"""Job status / progress + cost visibility."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, CostLog
from app.schemas import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.created_at.desc()).limit(200).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).get(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job


@router.get("/costs/summary")
def cost_summary(db: Session = Depends(get_db)):
    rows = db.query(CostLog).all()
    total = sum(r.estimated_cost_usd for r in rows)
    return {
        "calls": len(rows),
        "estimated_total_usd": round(total, 6),
        "by_call_type": {
            call_type: sum(r.estimated_cost_usd for r in rows if r.call_type == call_type)
            for call_type in {r.call_type for r in rows}
        },
    }
