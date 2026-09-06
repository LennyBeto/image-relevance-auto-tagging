"""Pydantic schemas — request/response bodies and the vision-output contract."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ---- Vision model contract (Section 4.1 of the brief) ----------------------

class ImageTags(BaseModel):
    """Schema every vision-model response is validated against.
    Anything that fails this validation is retried or flagged — never
    silently accepted, per the brief's core rule."""

    subject: str = Field(..., min_length=1, max_length=120)
    category: str = Field(..., min_length=1, max_length=60)
    attributes: list[str] = Field(default_factory=list)
    caption: str = Field(..., min_length=1, max_length=400)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("attributes")
    @classmethod
    def cap_attributes(cls, v: list[str]) -> list[str]:
        return v[:10]


# ---- API request/response models -------------------------------------------

class PostCreate(BaseModel):
    title: str
    body: str
    subject_hint: Optional[str] = None


class PostOut(BaseModel):
    id: str
    title: str
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


class ImageOut(BaseModel):
    id: str
    filename: str
    subject: Optional[str]
    category: Optional[str]
    attributes: Optional[list[str]]
    caption: Optional[str]
    confidence: Optional[float]
    needs_review: bool

    class Config:
        from_attributes = True


class SuggestionOut(BaseModel):
    id: str
    post_id: str
    image_id: Optional[str]
    similarity: Optional[float]
    guard_passed: bool
    guard_reason: Optional[str]
    status: str
    image: Optional[ImageOut] = None

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: str
    job_type: str
    status: str
    attempts: int
    last_error: Optional[str]

    class Config:
        from_attributes = True


class EvalResult(BaseModel):
    total: int
    correct: int
    top1_precision: float
    details: list[dict]
