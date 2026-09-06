# Image Relevance & Auto-Tagging

**FlyRank Internship · Backend Track · Capstone** — AI Image Understanding & Content Matching Engine

Understands an image library, tags it automatically, and matches the right image to the right blog
post — a red-fox post gets the red-fox photo, never the wolf. Good suggestions when confident, safe
rejection when not.

> The most important production feature here is not finding a match — it's avoiding a wrong one.
> The **mismatch guard** is the decision core: a safety layer combining schema-validated tags,
> semantic similarity, and model confidence, which refuses with an explanation when it isn't sure.

## Architecture

```
Images —(batch job)→ Vision Model → {tags, caption, confidence} → image_metadata
  |  embed(caption) ————————→ image_vectors
Posts ————————————→ embed(post text) ————————————→ post_vectors

GET /posts/:id/images
  → Similarity Ranking (image_vectors × post_vector)
  → Mismatch Guard (tags + threshold + confidence)
  |    Suggested image (ranked, explained)
  |    "No good match" + explanation
  → Review API: approve / reject
```

**Layers** (data / logic / HTTP kept separate, per the shared requirements):

| Layer | Where |
|---|---|
| HTTP / routing | `app/routers/*.py` |
| Business logic | `app/vision.py`, `app/embeddings.py`, `app/guard.py`, `app/eval.py` |
| Background processing | `app/jobs.py`, `app/worker.py` |
| Persistence | `app/models.py`, `app/database.py` |
| Config / secrets | `app/config.py` (reads `.env`, never hardcoded) |

## Repo structure

```
image-relevance-auto-tagging/
├── app/
│   ├── main.py              # FastAPI app + route registration
│   ├── config.py            # Settings (from .env)
│   ├── database.py          # SQLAlchemy engine/session
│   ├── models.py            # Image, Post, Suggestion, Job, CostLog
│   ├── schemas.py           # Pydantic I/O + the ImageTags vision contract
│   ├── vision.py            # Gemini/Ollama vision client + schema validation
│   ├── embeddings.py        # Gemini/Ollama embeddings + cosine similarity
│   ├── guard.py             # The mismatch guard (3-signal safety layer)
│   ├── jobs.py               # DB-backed job queue helpers
│   ├── worker.py            # Background worker (retries, chains vision→embed)
│   ├── cost_tracking.py     # Per-call cost log
│   └── routers/
│       ├── images.py        # upload / ingest / list images
│       ├── posts.py         # create posts, GET /posts/:id/images (ranking + guard)
│       ├── review.py        # approve / reject / inspect suggestions
│       └── jobs.py          # job status + cost summary
├── scripts/
│   ├── seed_corpus.py       # Pulls ~50 licensed images from Pexels, builds posts + eval set
│   └── run_eval.py          # CLI: prints top-1 precision
├── tests/
│   └── test_guard.py        # Unit tests for the mismatch guard (incl. the fox/wolf probe)
├── data/
│   ├── images/              # downloaded corpus (gitignored — script reproduces it)
│   └── eval_set.json        # labeled {post_id, correct_image_id} pairs
├── docker-compose.yml        # db + api + worker
├── Dockerfile
├── requirements.txt
├── capstone.yaml             # evaluator manifest (run / seed / test / endpoints)
├── .env.example
├── BUILDLOG.md               # honest AI-usage log
├── EVIDENCE.md                # one proof per requirement checkbox
└── LICENSE                    # MIT
```

## Your $0 stack

| Need | Free tool used here |
|---|---|
| Framework | Python + FastAPI |
| Vision model | Gemini Flash (free tier) — swap `AI_PROVIDER=ollama` for a fully local `llava`/`moondream` path |
| Embeddings | Gemini `text-embedding-004` (free tier) — or Ollama `all-minilm` locally |
| Schema validation | Pydantic |
| Database | PostgreSQL via Docker Compose |
| Image corpus | Pexels API (free, licensed images) |
| Cost tracking | `app/cost_tracking.py` — every vision/embedding call logged |

No step here requires a credit card. If `AI_PROVIDER=ollama` is set, nothing ever leaves your machine.

## Setup

### 1. Get free credentials
- **Gemini**: [Google AI Studio](https://aistudio.google.com/apikey) → create an API key (Google account, no card).
- **Pexels** (only needed to seed the corpus): [pexels.com/api](https://www.pexels.com/api/) → free API key.
- Prefer fully local? Install [Ollama](https://ollama.com), then `ollama pull llava && ollama pull all-minilm`,
  and set `AI_PROVIDER=ollama` in `.env` — skip the Gemini key entirely.

### 2. Configure
```bash
cp .env.example .env
# edit .env: paste GEMINI_API_KEY and PEXELS_API_KEY
```

### 3. Run the stack
```bash
docker compose up --build
```
This starts Postgres, the FastAPI API on `:8000`, and the background worker in one command.

### 4. Seed the corpus (separate terminal, first run only)
```bash
pip install -r requirements.txt          # to run the seed script locally
export $(cat .env | xargs)               # load PEXELS_API_KEY etc. into this shell
python scripts/seed_corpus.py            # downloads ~55 images across 4 categories, creates posts + eval_set.json
python -m app.worker --once              # drains the queue: tags every image, embeds every caption/post
```

### 5. Try it
```bash
# List tagged images
curl localhost:8000/images

# Ask for the best image for the fox post (grab a post_id from `curl localhost:8000/posts`)
curl localhost:8000/posts/<post_id>/images

# Approve / reject
curl -X POST localhost:8000/review/<suggestion_id>/approve

# Cost visibility
curl localhost:8000/jobs/costs/summary
```

### 6. Run the eval
```bash
python scripts/run_eval.py
# or: curl localhost:8000/eval/run
```

**Top-1 precision: _fill in after running against your corpus_.**
(This number must match what's pasted in `EVIDENCE.md`.)

### 7. Run tests
```bash
pytest -q
```
The guard tests run with no DB/network and directly exercise the fox/wolf mismatch scenario from
the brief (Section 4.3 / PROBE 3).

## How the mismatch guard decides (`app/guard.py`)

A candidate image must clear **all three** independent bars, or it's rejected with a stated reason:

1. **Confidence** — the vision model's own certainty about the tag must be ≥ `MIN_CONFIDENCE` (default `0.55`).
   Below that, the image is flagged for review rather than guessed.
2. **Similarity** — cosine similarity between the post embedding and the image-caption embedding must
   clear `SIMILARITY_THRESHOLD` (default `0.62`, tune this against your own eval set — see Section 8,
   Phase 4 of the brief).
3. **Category/subject match** — when a post has an explicit `subject_hint` (e.g. "red fox"), a candidate
   whose detected subject doesn't contain that hint is rejected even if similarity is high — this is
   what catches the wolf-on-a-fox-post case, since foxes and wolves can land close together in
   embedding space.

Rejections are never a bare `false` — they carry a human-readable `guard_reason`, surfaced through
`GET /review/{suggestion_id}` and `GET /posts/{id}/images`.

## Background jobs (`app/worker.py`)

- Vision tagging and embedding run as two job types in a small Postgres-backed queue (`app/jobs.py`) —
  no extra infra needed at this scale.
- Each job retries up to `max_attempts` (default 3) with the failure reason recorded on the job row;
  after that it's marked `failed` for a human to inspect via `GET /jobs`.
- A successful vision-tagging job automatically enqueues the follow-up embedding job for that image's
  caption — the two AI calls never block the HTTP request path.

## Realistic scope taken here

- **~55 images across 4 categories** (animal / landscape / technology / food) — comfortably over the
  40-image, 4-category floor from Section 7.
- **One vision model, one embedding model** (Gemini Flash + `text-embedding-004`, or the Ollama
  equivalents) — comparing models was treated as a stretch goal, not core.
- **Review interface is API-only** — `GET /review`, `/approve`, `/reject` — no frontend build, per
  the brief's explicit allowance.
- **Eval set**: 5 hand-labeled post↔image pairs generated by `seed_corpus.py`, growable by hand-editing
  `data/eval_set.json`.

## Limitations (honest, per the brief)

- Embeddings are stored as JSON float arrays and ranked with a full Python scan — fine at ~50 images,
  would need `pgvector` + an ANN index past a few thousand.
- The category/subject check in the guard is a substring match on the vision model's own subject
  string, not a fixed taxonomy — good enough at this scale, would want a controlled vocabulary at
  production scope.
- The worker is a simple polling loop, not a durable queue like Celery/RQ — acceptable for the $0,
  single-box scope of this capstone; documented here rather than hidden.

## Stretch goals (not started)

- Automatic alt-text generation from the vision output.
- Near-duplicate detection via perceptual hashing.
- A human-in-the-loop review UI beyond the current API+table.

## License

MIT — see `LICENSE`.
