"""Small DB-backed job queue. No extra infra (no Redis/Celery) is needed at
this scale — the requirement is retries + progress tracking off the request
path, which a polling worker (app/worker.py) satisfies honestly."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Job, JobStatus, JobType


def enqueue(db: Session, job_type: JobType, payload: dict) -> Job:
    job = Job(job_type=job_type, payload=payload, status=JobStatus.pending)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def next_pending(db: Session) -> Job | None:
    return (
        db.query(Job)
        .filter(Job.status == JobStatus.pending)
        .order_by(Job.created_at.asc())
        .first()
    )


def mark_running(db: Session, job: Job) -> None:
    job.status = JobStatus.running
    job.started_at = datetime.utcnow()
    job.attempts += 1
    db.commit()


def mark_succeeded(db: Session, job: Job) -> None:
    job.status = JobStatus.succeeded
    job.finished_at = datetime.utcnow()
    db.commit()


def mark_failed(db: Session, job: Job, error: str) -> None:
    job.last_error = error[:2000]
    if job.attempts >= job.max_attempts:
        job.status = JobStatus.failed
        job.finished_at = datetime.utcnow()
    else:
        job.status = JobStatus.pending  # will be retried by the worker loop
    db.commit()
