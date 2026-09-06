"""
Vision client: turns an image into schema-validated tags.

Two providers, one interface — swap via AI_PROVIDER in .env, no code changes
needed elsewhere. Both paths retry on transient failure and raise (never
guess) on a response that fails schema validation.
"""
import base64
import json
import re

import httpx
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.schemas import ImageTags

PROMPT = """You are an image-tagging system for a blog's media library.
Look at the image and respond with ONLY a JSON object (no markdown fences,
no prose) with exactly these fields:

{
  "subject": "short noun phrase, e.g. 'red fox'",
  "category": "one broad category, e.g. 'animal'",
  "attributes": ["3-6 short descriptive tags"],
  "caption": "one sentence describing the image",
  "confidence": 0.0-1.0 (how sure you are about the subject)
}

If you are unsure of the exact subject, use the closest general term and
give it a lower confidence score. Never guess a specific value with high
confidence."""


class VisionError(Exception):
    """Raised when a vision response cannot be trusted, even after retries."""


def _extract_json(text: str) -> dict:
    """Vision models sometimes wrap JSON in prose or code fences — strip that."""
    text = text.strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise VisionError(f"No JSON object found in vision response: {text[:200]!r}")
    return json.loads(match.group(0))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _call_gemini(image_bytes: bytes, mime_type: str) -> dict:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_vision_model}:generateContent?key={settings.gemini_api_key}"
    )
    b64 = base64.b64encode(image_bytes).decode()
    body = {
        "contents": [{
            "parts": [
                {"text": PROMPT},
                {"inline_data": {"mime_type": mime_type, "data": b64}},
            ]
        }],
        "generationConfig": {"temperature": 0.1},
    }
    resp = httpx.post(url, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return _extract_json(text)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _call_ollama(image_bytes: bytes) -> dict:
    b64 = base64.b64encode(image_bytes).decode()
    body = {
        "model": settings.ollama_vision_model,
        "prompt": PROMPT,
        "images": [b64],
        "stream": False,
        "options": {"temperature": 0.1},
    }
    resp = httpx.post(f"{settings.ollama_base_url}/api/generate", json=body, timeout=120)
    resp.raise_for_status()
    text = resp.json()["response"]
    return _extract_json(text)


def tag_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> ImageTags:
    """Run one image through the configured vision provider and return
    schema-validated tags. Raises VisionError if the model output can't be
    trusted after retries — callers must treat that as a job failure, not a
    silent pass-through."""
    try:
        if settings.ai_provider == "gemini":
            raw = _call_gemini(image_bytes, mime_type)
        else:
            raw = _call_ollama(image_bytes)
    except Exception as exc:  # network / provider failure after retries
        raise VisionError(f"vision call failed: {exc}") from exc

    try:
        return ImageTags.model_validate(raw)
    except ValidationError as exc:
        raise VisionError(f"vision output failed schema validation: {exc}") from exc
