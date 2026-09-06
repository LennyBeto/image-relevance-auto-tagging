"""
Unit tests for the mismatch guard — no DB or network needed, since guard.py
takes plain embeddings/floats. Covers the three rejection paths plus the
happy path, mirroring PROBEs 2-4 in the brief.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.guard import evaluate_candidate

FOX_VEC = [1.0, 0.0, 0.0]
WOLF_VEC = [0.95, 0.05, 0.0]   # deliberately close in vector space
UNRELATED_VEC = [0.0, 0.0, 1.0]


def test_low_confidence_is_flagged_not_guessed():
    result = evaluate_candidate(
        post_embedding=FOX_VEC, image_embedding=FOX_VEC,
        image_subject="red fox", image_confidence=0.3,
    )
    assert result.passed is False
    assert "low-confidence" in result.reason.lower()


def test_low_similarity_is_rejected():
    result = evaluate_candidate(
        post_embedding=FOX_VEC, image_embedding=UNRELATED_VEC,
        image_subject="laptop", image_confidence=0.95,
    )
    assert result.passed is False
    assert "below threshold" in result.reason.lower()


def test_wolf_on_fox_post_is_rejected_by_category():
    # High similarity (foxes/wolves look alike in embedding space) but the
    # subject check must still catch the mismatch — this is the exact
    # scenario from Section 4.3 of the brief.
    result = evaluate_candidate(
        post_embedding=FOX_VEC, image_embedding=WOLF_VEC,
        image_subject="gray wolf", image_confidence=0.9,
        expected_subject="red fox",
    )
    assert result.passed is False
    assert "category mismatch" in result.reason.lower()


def test_confident_matching_fox_is_approved():
    result = evaluate_candidate(
        post_embedding=FOX_VEC, image_embedding=FOX_VEC,
        image_subject="red fox", image_confidence=0.94,
        expected_subject="red fox",
    )
    assert result.passed is True
