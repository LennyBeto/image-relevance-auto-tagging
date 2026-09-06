"""Posts + the ranked-image-suggestion endpoint (Section 5's GET /posts/:id/images)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Post, Image, Suggestion, SuggestionStatus, JobType
from app.schemas import PostCreate, PostOut, SuggestionOut
from app.guard import evaluate_candidate
from app import jobs

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostOut)
def create_post(payload: PostCreate, db: Session = Depends(get_db)):
    post = Post(title=payload.title, body=payload.body, subject_hint=payload.subject_hint)
    db.add(post)
    db.commit()
    db.refresh(post)

    jobs.enqueue(db, JobType.embedding, {"target": "post", "id": post.id, "text": f"{post.title}. {post.body}"})
    return post


@router.get("", response_model=list[PostOut])
def list_posts(db: Session = Depends(get_db)):
    return db.query(Post).all()


@router.get("/{post_id}/images", response_model=SuggestionOut)
def suggest_images(post_id: str, db: Session = Depends(get_db)):
    """Rank every tagged, embedded image against this post, run the mismatch
    guard on the best candidate, and persist + return the suggestion."""
    post = db.query(Post).get(post_id)
    if post is None:
        raise HTTPException(404, "post not found")
    if post.embedding is None:
        raise HTTPException(409, "post embedding not ready yet — try again shortly")

    candidates = (
        db.query(Image)
        .filter(Image.embedding.isnot(None), Image.subject.isnot(None))
        .all()
    )

    best_image = None
    best_similarity = -1.0
    for image in candidates:
        from app.embeddings import cosine_similarity
        sim = cosine_similarity(post.embedding, image.embedding)
        if sim > best_similarity:
            best_similarity = sim
            best_image = image

    if best_image is None:
        suggestion = Suggestion(
            post_id=post.id, image_id=None, similarity=None,
            guard_passed=False, guard_reason="No tagged images available in the corpus.",
        )
    else:
        result = evaluate_candidate(
            post_embedding=post.embedding,
            image_embedding=best_image.embedding,
            image_subject=best_image.subject,
            image_confidence=best_image.confidence,
            expected_subject=post.subject_hint,
        )
        suggestion = Suggestion(
            post_id=post.id,
            image_id=best_image.id if result.passed else None,
            similarity=result.similarity,
            guard_passed=result.passed,
            guard_reason=result.reason,
        )

    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion
