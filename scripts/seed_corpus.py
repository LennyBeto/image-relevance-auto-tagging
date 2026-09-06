"""
Builds the ~50-image, 4+ category corpus and a matching set of blog posts,
then writes data/eval_set.json (Section 7's "small labeled eval set").

Uses the Pexels API (free, no credit card: https://www.pexels.com/api/) to
fetch real, licensed-free photos per category, so retrieval behavior is real
rather than synthetic.

Usage:
    export PEXELS_API_KEY=...          # or set it in .env
    python scripts/seed_corpus.py
    python -m app.worker --once        # tag + embed everything just downloaded
"""
import json
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.models import Image, Post
from app.config import settings

CATEGORIES = {
    "animal": ["red fox", "gray wolf", "brown bear", "deer", "domestic dog"],
    "landscape": ["mountain landscape", "forest path", "desert dunes"],
    "technology": ["laptop coding", "server room", "smartphone"],
    "food": ["coffee cup", "fresh bread"],
}
IMAGES_PER_TERM = 4  # 14 terms * ~4 = ~56 images, comfortably over the 40 floor
IMAGE_DIR = "data/images"
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")


def fetch_pexels(query: str, per_page: int) -> list[dict]:
    resp = httpx.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": per_page},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("photos", [])


def download(url: str, path: str) -> None:
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)


def main():
    if not PEXELS_API_KEY:
        raise SystemExit("Set PEXELS_API_KEY (env var or .env) before seeding — see Section 10 of the brief.")

    os.makedirs(IMAGE_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    downloaded = []
    for category, terms in CATEGORIES.items():
        for term in terms:
            photos = fetch_pexels(term, IMAGES_PER_TERM)
            for i, photo in enumerate(photos):
                url = photo["src"]["large"]
                filename = f"{term.replace(' ', '_')}_{i}.jpg"
                path = os.path.join(IMAGE_DIR, filename)
                download(url, path)

                image = Image(filename=filename, path=path, source_url=photo["url"], license="Pexels License")
                db.add(image)
                downloaded.append((category, term, image))
                print(f"downloaded {filename}")
    db.commit()

    # A handful of posts, one per animal term, so the fox/wolf probe (Section 13
    # PROBE 2/3) has real posts to query against.
    posts_to_make = [
        ("The behavior of red foxes", "Red foxes are adaptable, mostly nocturnal hunters found across the northern hemisphere.", "red fox"),
        ("Understanding gray wolf packs", "Gray wolves live and hunt in tightly organized family packs.", "gray wolf"),
        ("Why bears hibernate", "Brown bears spend the winter in a state of deep, extended sleep.", "brown bear"),
        ("Tracking deer through the forest", "Deer are common across forested regions and are usually shy of humans.", "deer"),
        ("A day in the life of a dog", "Dogs have been companions to humans for thousands of years.", "domestic dog"),
    ]
    post_records = []
    for title, body, subject_hint in posts_to_make:
        post = Post(title=title, body=body, subject_hint=subject_hint)
        db.add(post)
        post_records.append((post, subject_hint))
    db.commit()

    # Build the eval set: for each post, the "correct" image is any downloaded
    # image whose search term matches the post's subject hint.
    eval_set = []
    for post, subject_hint in post_records:
        match = next((img for cat, term, img in downloaded if term == subject_hint), None)
        if match:
            eval_set.append({"post_id": post.id, "correct_image_id": match.id})

    with open("data/eval_set.json", "w") as f:
        json.dump(eval_set, f, indent=2)

    print(f"\nDone: {len(downloaded)} images, {len(post_records)} posts, "
          f"{len(eval_set)} labeled eval rows written to data/eval_set.json")
    print("Next: python -m app.worker --once   (tags + embeds everything)")


if __name__ == "__main__":
    main()
