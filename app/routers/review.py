"""Review API — approve / reject / inspect a suggested pairing (Section 4.5)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Suggestion, SuggestionStatus
from app.schemas import SuggestionOut

router = APIRouter(prefix="/review", tags=["review"])


@router.get("", response_model=list[SuggestionOut])
def list_suggestions(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Suggestion)
    if status:
        q = q.filter(Suggestion.status == status)
    return q.order_by(Suggestion.created_at.desc()).all()


@router.get("/{suggestion_id}", response_model=SuggestionOut)
def get_suggestion(suggestion_id: str, db: Session = Depends(get_db)):
    """Inspect why an image was selected or refused."""
    s = db.query(Suggestion).get(suggestion_id)
    if s is None:
        raise HTTPException(404, "suggestion not found")
    return s


@router.post("/{suggestion_id}/approve", response_model=SuggestionOut)
def approve(suggestion_id: str, db: Session = Depends(get_db)):
    s = db.query(Suggestion).get(suggestion_id)
    if s is None:
        raise HTTPException(404, "suggestion not found")
    s.status = SuggestionStatus.approved
    s.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return s


@router.post("/{suggestion_id}/reject", response_model=SuggestionOut)
def reject(suggestion_id: str, db: Session = Depends(get_db)):
    s = db.query(Suggestion).get(suggestion_id)
    if s is None:
        raise HTTPException(404, "suggestion not found")
    s.status = SuggestionStatus.rejected
    s.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return s
