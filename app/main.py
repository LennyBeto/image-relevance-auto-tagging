"""FastAPI application entrypoint."""
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.routers import images, posts, review, jobs as jobs_router
from app.eval import run_eval

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Image Relevance & Auto-Tagging",
    description="Vision tagging + semantic matching + a mismatch guard for blog post ↔ image pairing.",
    version="0.1.0",
)

app.include_router(images.router)
app.include_router(posts.router)
app.include_router(review.router)
app.include_router(jobs_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/eval/run")
def eval_run(db: Session = Depends(get_db)):
    return run_eval(db)
