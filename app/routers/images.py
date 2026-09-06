"""Image ingestion + listing."""
import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Image, JobType
from app.schemas import ImageOut
from app import jobs

router = APIRouter(prefix="/images", tags=["images"])

CORPUS_DIR = "data/images"


@router.post("/upload", response_model=ImageOut)
def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Add one image to the corpus and enqueue its tagging job."""
    os.makedirs(CORPUS_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    stored_name = f"{uuid.uuid4()}{ext}"
    path = os.path.join(CORPUS_DIR, stored_name)
    with open(path, "wb") as f:
        f.write(file.file.read())

    image = Image(filename=file.filename, path=path)
    db.add(image)
    db.commit()
    db.refresh(image)

    jobs.enqueue(db, JobType.vision_tagging, {"image_id": image.id})
    return image


@router.post("/ingest")
def ingest_corpus(db: Session = Depends(get_db)):
    """Enqueue a vision-tagging job for every untagged image already on disk
    (used after scripts/seed_corpus.py drops files into data/images/)."""
    untagged = db.query(Image).filter(Image.tagged_at.is_(None), Image.subject.is_(None)).all()
    created = 0
    for image in untagged:
        jobs.enqueue(db, JobType.vision_tagging, {"image_id": image.id})
        created += 1
    return {"queued": created}


@router.get("", response_model=list[ImageOut])
def list_images(db: Session = Depends(get_db)):
    return db.query(Image).all()


@router.get("/{image_id}", response_model=ImageOut)
def get_image(image_id: str, db: Session = Depends(get_db)):
    return db.query(Image).get(image_id)
