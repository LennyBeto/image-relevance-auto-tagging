"""
Database models.

Embeddings are stored as JSON arrays of floats. At ~50 images this is fine
per the brief's "in-DB arrays fine at this scale" note; swap the embedding
columns for pgvector's Vector type if the corpus grows.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, ForeignKey, DateTime, Enum, JSON, Text, Index
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class JobType(str, enum.Enum):
    vision_tagging = "vision_tagging"
    embedding = "embedding"


class SuggestionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Image(Base):
    __tablename__ = "images"

    id = Column(String, primary_key=True, default=gen_uuid)
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    license = Column(String, nullable=True)

    # Vision output (schema-validated before it ever lands here)
    subject = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True, index=True)
    attributes = Column(JSON, nullable=True)  # list[str]
    caption = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    needs_review = Column(Boolean, default=False)  # low-confidence flag

    embedding = Column(JSON, nullable=True)  # list[float]
    tagged_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_images_category_subject", "category", "subject"),
    )


class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    subject_hint = Column(String, nullable=True)  # optional manual override/hint

    embedding = Column(JSON, nullable=True)  # list[float]
    created_at = Column(DateTime, default=datetime.utcnow)


class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(String, primary_key=True, default=gen_uuid)
    post_id = Column(String, ForeignKey("posts.id"), nullable=False, index=True)
    image_id = Column(String, ForeignKey("images.id"), nullable=True)  # null if "no match"

    similarity = Column(Float, nullable=True)
    guard_passed = Column(Boolean, default=False)
    guard_reason = Column(Text, nullable=True)

    status = Column(Enum(SuggestionStatus), default=SuggestionStatus.pending, index=True)
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post")
    image = relationship("Image")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.pending, index=True)

    payload = Column(JSON, nullable=True)     # e.g. {"image_id": ...}
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class CostLog(Base):
    __tablename__ = "cost_log"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    call_type = Column(String, nullable=False)   # "vision" | "embedding"
    provider = Column(String, nullable=False)    # "gemini" | "ollama"
    model = Column(String, nullable=False)
    input_units = Column(Integer, default=0)     # tokens / images, provider-dependent
    output_units = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
