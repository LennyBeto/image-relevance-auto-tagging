"""
Top-1 precision evaluation (Section 7 / PROBE 5).

Loads data/eval_set.json — a hand-labeled list of {post_id, correct_image_id}
pairs — re-runs the ranking for each post, and reports the share whose top
suggestion matched the label.
"""
import json

from sqlalchemy.orm import Session

from app.models import Post, Image
from app.embeddings import cosine_similarity


def run_eval(db: Session, eval_path: str = "data/eval_set.json") -> dict:
    with open(eval_path) as f:
        eval_set = json.load(f)

    details = []
    correct = 0

    for row in eval_set:
        post = db.query(Post).get(row["post_id"])
        if post is None or post.embedding is None:
            details.append({**row, "predicted_image_id": None, "correct": False, "note": "post not embedded"})
            continue

        candidates = db.query(Image).filter(Image.embedding.isnot(None)).all()
        best, best_sim = None, -1.0
        for image in candidates:
            sim = cosine_similarity(post.embedding, image.embedding)
            if sim > best_sim:
                best, best_sim = image, sim

        predicted_id = best.id if best else None
        is_correct = predicted_id == row["correct_image_id"]
        correct += int(is_correct)
        details.append({
            "post_id": row["post_id"],
            "correct_image_id": row["correct_image_id"],
            "predicted_image_id": predicted_id,
            "similarity": round(best_sim, 4) if best else None,
            "correct": is_correct,
        })

    total = len(eval_set)
    precision = round(correct / total, 4) if total else 0.0
    return {"total": total, "correct": correct, "top1_precision": precision, "details": details}
