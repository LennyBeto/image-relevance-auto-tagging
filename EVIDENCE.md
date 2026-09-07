# Evidence

**Beta version: A few tests ongoing before final version **

## AI processing

- [ ] **Vision output schema-validated** — paste a `pytest` pass for
  `app/schemas.py::ImageTags`, or a log line from `app/vision.py` showing a
  `VisionError` raised on a malformed response.
- [ ] **Low-confidence flagged, not accepted** — paste one `Image` row
  (via `GET /images`) with `"needs_review": true` and `confidence < 0.55`.
- [ ] **Batch job with retries** — paste `GET /jobs` output showing a job
  with `attempts > 1` that eventually succeeded, or the worker log for it.

## Matching system

- [ ] **Costs tracked per call** — paste `GET /jobs/costs/summary` output.
- [ ] **Suggestions ranked and stored** — paste one `Suggestion` row from
  `GET /review`.
- [ ] **Semantic matching across phrasing** — paste a query where a post
  about "Vulpes vulpes" still ranks the fox image first.

## Safety layer

- [x] **Guard rejects the wolf-on-fox-post scenario** — proven by
  `tests/test_guard.py::test_wolf_on_fox_post_is_rejected_by_category`:

  ```
  tests/test_guard.py::test_low_confidence_is_flagged_not_guessed PASSED
  tests/test_guard.py::test_low_similarity_is_rejected PASSED
  tests/test_guard.py::test_wolf_on_fox_post_is_rejected_by_category PASSED
  tests/test_guard.py::test_confident_matching_fox_is_approved PASSED
  4 passed in 0.30s
  ```

- [ ] **Rejections include a human-readable explanation** — paste a
  `guard_reason` field from a rejected `Suggestion`.
- [ ] **"No confident match" case** — paste a `Suggestion` with
  `image_id: null` and its `guard_reason`.

## Backend

- [ ] **DB models + indexes** — paste `\d images`, `\d suggestions` etc.
  from `psql`, or the relevant lines from `app/models.py`.
- [ ] **Review workflow works end to end** — paste an approve/reject curl
  transcript.

## Quality & documentation

- [ ] **Eval precision measured** — paste `python scripts/run_eval.py`
  output (the `TOP-1 PRECISION: XX%` line must match the README).
- [ ] **README + diagram + required files present** — this repo's file
  tree, or a `ls -la` paste.
