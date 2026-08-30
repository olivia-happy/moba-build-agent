"""Build the local hero portrait fingerprint index.

Usage (repo root):
    .\\.venv\\Scripts\\python.exe -m backend.scripts.build_portrait_index

Reproducible: same hero list + same portrait bytes + same grid size produce
the same JSON and the same content_hash. No API key. Network is only needed
when a portrait is not already cached under data/portraits/.
"""
from __future__ import annotations

import argparse
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.portrait_index import (  # noqa: E402
    HERO_LIST_URL,
    PortraitEntry,
    PortraitIndexError,
    build_entry,
    download_hero_portrait,
    hero_portrait_url,
    index_entries,
    index_to_json,
    load_index,
    rgb_to_luminance,
)

DEFAULT_OUTPUT = ROOT / "data" / "portrait_index.json"
DEFAULT_CACHE = ROOT / "data" / "portraits"
MAX_IMAGE_DIMENSION = 128


def fetch_hero_list(client: httpx.Client) -> list[dict]:
    response = client.get(HERO_LIST_URL)
    response.raise_for_status()
    heroes = response.json()
    if not isinstance(heroes, list):
        raise PortraitIndexError("hero list is not a JSON array")
    return [
        hero
        for hero in heroes
        if isinstance(hero, dict) and hero.get("ename") is not None and hero.get("cname")
    ]

def portrait_to_luminance(data: bytes, max_dimension: int = MAX_IMAGE_DIMENSION) -> tuple[list[int], int, int]:
    with Image.open(io.BytesIO(data)) as image:
        image = image.convert("RGB")
        image.thumbnail((max_dimension, max_dimension))
        width, height = image.size
        pixels = [rgb[0] << 16 | rgb[1] << 8 | rgb[2] for rgb in image.getdata()]
        return [rgb_to_luminance(rgb) for rgb in pixels], width, height


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--max-heroes", type=int, default=None, help="dev/test limit")
    args = parser.parse_args(argv)

    output = args.output
    cache = args.cache_dir
    output.parent.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)

    fetched_at = datetime.now(timezone.utc)
    entries: list[PortraitEntry] = []
    failures: list[str] = []

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        heroes = fetch_hero_list(client)
        if args.max_heroes is not None:
            heroes = heroes[: args.max_heroes]

        for hero in heroes:
            hero_id = int(hero["ename"])
            hero_name = str(hero["cname"])
            url = hero_portrait_url(hero_id)
            cache_file = cache / f"{hero_id}.jpg"
            try:
                if cache_file.is_file():
                    data = cache_file.read_bytes()
                else:
                    data, url = download_hero_portrait(hero_id, client=client)
                    cache_file.write_bytes(data)
                luminance, width, height = portrait_to_luminance(data)
                entries.append(
                    build_entry(
                        hero_id=hero_id,
                        hero_name=hero_name,
                        source_url=url,
                        luminance=luminance,
                        width=width,
                        height=height,
                    )
                )
            except (PortraitIndexError, OSError, ValueError) as exc:
                failures.append(f"{hero_id} {hero_name}: {exc}")
                print(f"  skipped {hero_id} {hero_name}: {exc}", file=sys.stderr)

    index = index_entries(entries=entries, fetched_at=fetched_at)
    output.write_text(index_to_json(index), encoding="utf-8")
    print(
        f"wrote {output} heroes={index.hero_count} skipped={len(failures)} "
        f"grid={index.grid_size}x{index.grid_size} hash={index.content_hash[:12]} "
        f"fetched_at={index.fetched_at.isoformat()}"
    )

    loaded = load_index(output)
    if loaded.content_hash != index.content_hash:
        print("round-trip hash mismatch", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
