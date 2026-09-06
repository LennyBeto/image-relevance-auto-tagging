"""
Background worker: processes vision-tagging and embedding jobs off the
request path, with retries and per-call cost logging (Section 4.4 / PROBE 1).

Run continuously:   python -m app.worker
Run one pass only:  python -m app.worker --once   (used by scripts/seed_corpus.py)
"""
import sys
import time

from app.database import SessionLocal
from app.models import Image, Post, JobStatus, JobType
from app import jobs
from app.vision import tag_image, VisionError
from app.embeddings import embed_text, EmbeddingError
from app.cost_tracking import log_cost
from app.config import settings


def process_vision_job(db, job) -> None:
    image_id = job.payload["image_id"]
    image = db.query(Image).get(image_id)
    if image is None:
        raise RuntimeError(f"image {image_id} not found")

    with open(image.path, "rb") as f:
        image_bytes = f.read()

    tags = tag_image(image_bytes)  # raises VisionError on untrustworthy output

    image.subject = tags.subject
    image.category = tags.category
    image.attributes = tags.attributes
    image.caption = tags.caption
    image.confidence = tags.confidence
    image.needs_review = tags.confidence < settings.min_confidence
    db.commit()

    log_cost(
        db, job_id=job.id, call_type="vision", provider=settings.ai_provider,
        model=settings.gemini_vision_model if settings.ai_provider == "gemini" else settings.ollama_vision_model,
        input_units=1, output_units=len(tags.caption.split()),
    )

    # chain an embedding job for the caption we just produced
    jobs.enqueue(db, JobType.embedding, {"target": "image", "id": image.id, "text": tags.caption})


def process_embedding_job(db, job) -> None:
    target = job.payload["target"]
    text = job.payload["text"]
    vector = embed_text(text)

    if target == "image":
        obj = db.query(Image).get(job.payload["id"])
    else:
        obj = db.query(Post).get(job.payload["id"])
    if obj is None:
        raise RuntimeError(f"{target} {job.payload['id']} not found")

    obj.embedding = vector
    db.commit()

    log_cost(
        db, job_id=job.id, call_type="embedding", provider=settings.ai_provider,
        model=settings.gemini_embedding_model if settings.ai_provider == "gemini" else settings.ollama_embedding_model,
        input_units=len(text.split()),
    )


def run_one(db) -> bool:
    """Process a single pending job. Returns False if the queue is empty."""
    job = jobs.next_pending(db)
    if job is None:
        return False

    jobs.mark_running(db, job)
    try:
        if job.job_type == JobType.vision_tagging:
            process_vision_job(db, job)
        else:
            process_embedding_job(db, job)
        jobs.mark_succeeded(db, job)
    except (VisionError, EmbeddingError, Exception) as exc:
        jobs.mark_failed(db, job, str(exc))
    return True


def main():
    once = "--once" in sys.argv
    db = SessionLocal()
    try:
        if once:
            while run_one(db):
                pass
        else:
            while True:
                if not run_one(db):
                    time.sleep(2)
    finally:
        db.close()


if __name__ == "__main__":
    main()
