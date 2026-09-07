# Build Log — AI usage, honestly

This capstone was scaffolded with AI assistance (Claude). This log is kept
current as the project develops, per the brief's "AI-assisted building is
encouraged — and owned" rule.

## Where AI helped
- Initial project structure and module boundaries (routers / models / vision
  / embeddings / guard / worker split).
- First draft of the mismatch guard's three-signal logic (confidence →
  similarity → category), and its unit tests.
- Boilerplate: Pydantic schemas, SQLAlchemy models, Dockerfile, docker-compose.

## Where it was wrong / needed correction
- Gemini Flash occasionally ignored the "respond with ONLY a JSON object" instruction and
  wrapped the JSON in a sentence or a ```json code fence. Rather than fighting the prompt
  further, added the `_extract_json()` regex fallback in `vision.py` that strips fences and
  pulls out the `{...}` block before validating — treating "the model adds prose" as an
  expected failure mode, not an edge case.
- The Ollama (`llava`) path returns `confidence` as a string (`"0.9"`) rather than a float in
  some responses. Pydantic's `ImageTags` schema coerces this automatically, so it passes
  validation — noted here rather than "fixed," since silently coercing a wrong type is itself
  a small risk worth being honest about.
- First guess at `SIMILARITY_THRESHOLD` was 0.75, copied from a tutorial. Against the real
  corpus, genuinely matching post/image pairs (e.g. the red-fox post + red-fox photo) scored
  0.55–0.68 with `text-embedding-004` — 0.75 rejected almost everything, including correct
  matches. Re-tuned to 0.62 by checking precision/recall on the labeled eval set, not by
  guessing a rounder number.
- Pexels search results for narrow terms like "gray wolf" occasionally returned off-topic
  images (illustrations, unrelated stock photos) rather than clean photographs. Didn't hand-
  curate the corpus to hide this — it's a realistic case for the confidence/`needs_review`
  path to catch, so it was left in intentionally.

## What I changed / would explain to an evaluator
- I can explain any 2–3 lines picked from `app/guard.py` or `app/vision.py`: the guard's three
  checks are independent and ANDed together on purpose — a single weak signal (e.g. borderline
  similarity) should never be enough to approve a pairing on its own.
- The category check in `guard.py` is a substring match on the vision model's own subject
  string (`"fox" in "red fox"`), not a fixed taxonomy. I'd tell an evaluator this is a
  deliberate scope cut for a ~50-image corpus — a real production system would map subjects to
  a controlled vocabulary so "gray wolf" and "wolf" are guaranteed to collide correctly instead
  of relying on string containment.
- `SIMILARITY_THRESHOLD` and `MIN_CONFIDENCE` live in `.env`, not hardcoded, specifically so
  they could be retuned against the eval set without a code change — that's the mechanism
  Section 8 Phase 4 asks for ("pick thresholds using your own labeled eval set").