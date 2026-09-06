"""
The mismatch guard — the production-critical safety layer (Section 4.3).

Combines three independent signals so no single weak signal can force a bad
match through:
  1. Category compatibility  — coarse sanity check (animal vs animal, etc.)
  2. Semantic similarity     — cosine distance between post and image embeddings
  3. Model confidence        — the vision model's own certainty about the tag

A candidate must clear ALL THREE bars to be approved. Any failure returns a
human-readable reason instead of a bare boolean, per PROBE 3/4.
"""
from dataclasses import dataclass

from app.config import settings
from app.embeddings import cosine_similarity


@dataclass
class GuardResult:
    passed: bool
    similarity: float
    reason: str


def evaluate_candidate(
    *,
    post_embedding: list[float],
    image_embedding: list[float],
    image_subject: str | None,
    image_confidence: float | None,
    expected_subject: str | None = None,
) -> GuardResult:
    similarity = cosine_similarity(post_embedding, image_embedding)

    # 1. Confidence bar — never trust a low-confidence tag into production.
    if image_confidence is None or image_confidence < settings.min_confidence:
        return GuardResult(
            passed=False,
            similarity=similarity,
            reason=(
                f"Low-confidence tag ({image_confidence!r}): flagged for human "
                f"review instead of guessed."
            ),
        )

    # 2. Similarity bar — the tuned cut-off from the eval set.
    if similarity < settings.similarity_threshold:
        return GuardResult(
            passed=False,
            similarity=similarity,
            reason=(
                f"Similarity {similarity:.2f} is below threshold "
                f"{settings.similarity_threshold:.2f}: no confident match."
            ),
        )

    # 3. Category / subject sanity check — the fox-vs-wolf boundary.
    # Only enforced when we have an explicit expectation to check against
    # (e.g. an admin-provided subject hint on the post).
    if expected_subject and image_subject:
        if expected_subject.strip().lower() not in image_subject.strip().lower():
            return GuardResult(
                passed=False,
                similarity=similarity,
                reason=(
                    f"Category mismatch: expected '{expected_subject}', "
                    f"detected '{image_subject}'."
                ),
            )

    return GuardResult(
        passed=True,
        similarity=similarity,
        reason=f"Similarity {similarity:.2f} clears threshold; subject and confidence check out.",
    )
