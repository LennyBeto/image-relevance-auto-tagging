"""
Embedding client — same swap-by-config pattern as vision.py.
Produces the shared semantic space that captions and post text are
compared in (cosine similarity, see guard.py).
"""
import httpx
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class EmbeddingError(Exception):
    pass


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _embed_gemini(text: str) -> list[float]:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_embedding_model}:embedContent?key={settings.gemini_api_key}"
    )
    body = {
        "model": f"models/{settings.gemini_embedding_model}",
        "content": {"parts": [{"text": text}]},
        "taskType": "SEMANTIC_SIMILARITY",
    }
    resp = httpx.post(url, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _embed_ollama(text: str) -> list[float]:
    resp = httpx.post(
        f"{settings.ollama_base_url}/api/embeddings",
        json={"model": settings.ollama_embedding_model, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def embed_text(text: str) -> list[float]:
    try:
        if settings.ai_provider == "gemini":
            return _embed_gemini(text)
        return _embed_ollama(text)
    except Exception as exc:
        raise EmbeddingError(f"embedding call failed: {exc}") from exc


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
