"""Reproducible hero portrait fingerprint index for on-device recognition.

Why this exists
---------------
The Android overlay captures one screen frame and must identify which enemy
heroes are visible before asking the player to confirm. A tiny luminance grid
per hero is enough to rank candidates on-device; the player always confirms
before any build advice is used. The index carries provenance (source URL,
fetched_at, content_hash) so every candidate can be traced and rebuilt
offline with the exact same bytes.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import httpx

HERO_LIST_URL = "https://pvp.qq.com/web201605/js/herolist.json"
HERO_PORTRAIT_URL_TEMPLATE = (
    "https://game.gtimg.cn/images/yxzj/img201606/heroimg/{hero_id}/{hero_id}.jpg"
)

PORTRAIT_GRID_SIZE = 16
SCHEMA_VERSION = 1
DOWNLOAD_TIMEOUT_SECONDS = 15
MAX_DOWNLOAD_BYTES = 4 * 1024 * 1024


class PortraitIndexError(RuntimeError):
    """Raised when a portrait index cannot be built or loaded safely."""

@dataclass(frozen=True)
class PortraitEntry:
    hero_id: int
    hero_name: str
    source_url: str
    content_hash: str
    width: int
    height: int
    grid: tuple[int, ...]


@dataclass(frozen=True)
class PortraitIndex:
    schema_version: int
    grid_size: int
    fetched_at: datetime
    source_hero_list: str
    hero_count: int
    content_hash: str
    entries: tuple[PortraitEntry, ...]


def hero_portrait_url(hero_id: int) -> str:
    """Public portrait URL used both by the builder and the Android client."""
    return HERO_PORTRAIT_URL_TEMPLATE.format(hero_id=hero_id)


def rgb_to_luminance(rgb: int) -> int:
    red = (rgb >> 16) & 0xFF
    green = (rgb >> 8) & 0xFF
    blue = rgb & 0xFF
    return int(0.299 * red + 0.587 * green + 0.114 * blue)

def downsample_to_grid(
    luminance: Sequence[int], width: int, height: int, grid_size: int = PORTRAIT_GRID_SIZE
) -> list[int]:
    """Average each grid cell of a luminance image into a fixed-size descriptor."""
    if width <= 0 or height <= 0:
        raise PortraitIndexError(f"invalid dimensions {width}x{height}")
    if len(luminance) != width * height:
        raise PortraitIndexError(f"pixel count {len(luminance)} != {width}x{height}")
    cells: list[int] = []
    for cell_y in range(grid_size):
        y0 = cell_y * height // grid_size
        y1 = (cell_y + 1) * height // grid_size
        for cell_x in range(grid_size):
            x0 = cell_x * width // grid_size
            x1 = (cell_x + 1) * width // grid_size
            total = 0
            count = 0
            for y in range(y0, y1):
                start = y * width + x0
                total += sum(luminance[start : start + (x1 - x0)])
                count += x1 - x0
            cells.append(total // count if count else 0)
    return cells


def build_entry(
    *,
    hero_id: int,
    hero_name: str,
    source_url: str,
    luminance: Sequence[int],
    width: int,
    height: int,
    grid_size: int = PORTRAIT_GRID_SIZE,
) -> PortraitEntry:
    grid = downsample_to_grid(luminance, width, height, grid_size)
    payload = ",".join(str(value) for value in grid)
    return PortraitEntry(
        hero_id=hero_id,
        hero_name=hero_name,
        source_url=source_url,
        content_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        width=width,
        height=height,
        grid=tuple(grid),
    )



def canonical_payload(entries: Iterable[PortraitEntry]) -> str:
    """The exact byte string the artifact hash covers.

    This is the single source of truth shared with the Android parser: the
    index JSON contains `canonical_payload` verbatim, and the device only
    needs to hash it with SHA-256. Keeping this canonical string explicit
    avoids two independent serializers drifting apart.
    """
    ordered = sorted(entries, key=lambda entry: entry.hero_id)
    items = []
    for entry in ordered:
        items.append(
            "{"
            + ",".join(
                [
                    f'"content_hash":"{entry.content_hash}"',
                    f'"grid":[{",".join(str(v) for v in entry.grid)}]',
                    f'"hero_id":{entry.hero_id}',
                    f'"hero_name":"{entry.hero_name}"',
                ]
            )
            + "}"
        )
    return "[" + ",".join(items) + "]"
def _entries_payload(entries: Iterable[PortraitEntry]) -> str:
    ordered = sorted(entries, key=lambda entry: entry.hero_id)
    return json.dumps(
        [
            {
                "hero_id": entry.hero_id,
                "hero_name": entry.hero_name,
                "source_url": entry.source_url,
                "content_hash": entry.content_hash,
                "grid": list(entry.grid),
            }
            for entry in ordered
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def index_entries(
    *,
    entries: Iterable[PortraitEntry],
    fetched_at: datetime,
    source_hero_list: str = HERO_LIST_URL,
    grid_size: int = PORTRAIT_GRID_SIZE,
) -> PortraitIndex:
    ordered = tuple(sorted(entries, key=lambda entry: entry.hero_id))
    payload = canonical_payload(ordered)
    return PortraitIndex(
        schema_version=SCHEMA_VERSION,
        grid_size=grid_size,
        fetched_at=fetched_at,
        source_hero_list=source_hero_list,
        hero_count=len(ordered),
        content_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        entries=ordered,
    )

def index_to_json(index: PortraitIndex) -> str:
    """Deterministic, self-describing JSON artifact for Android to consume."""
    document = {
        "schema_version": index.schema_version,
        "grid_size": index.grid_size,
        "fetched_at": index.fetched_at.isoformat(),
        "source_hero_list": index.source_hero_list,
        "hero_count": index.hero_count,
        "canonical_payload": canonical_payload(index.entries),
        "content_hash": index.content_hash,
        "entries": [
            {
                "hero_id": entry.hero_id,
                "hero_name": entry.hero_name,
                "source_url": entry.source_url,
                "content_hash": entry.content_hash,
                "width": entry.width,
                "height": entry.height,
                "grid": list(entry.grid),
            }
            for entry in index.entries
        ],
    }
    return json.dumps(document, ensure_ascii=False, indent=2)


def load_index(path: Path) -> PortraitIndex:
    """Load and verify an index artifact; raises on tampering or schema drift."""
    if not path.is_file():
        raise PortraitIndexError(f"index not found: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != SCHEMA_VERSION:
        raise PortraitIndexError(
            f"unsupported schema_version: {document.get('schema_version')} (expected {SCHEMA_VERSION})"
        )
    entries = tuple(
        PortraitEntry(
            hero_id=int(entry["hero_id"]),
            hero_name=str(entry["hero_name"]),
            source_url=str(entry["source_url"]),
            content_hash=str(entry["content_hash"]),
            width=int(entry.get("width", 0)),
            height=int(entry.get("height", 0)),
            grid=tuple(int(value) for value in entry["grid"]),
        )
        for entry in document["entries"]
    )
    index = PortraitIndex(
        schema_version=int(document["schema_version"]),
        grid_size=int(document["grid_size"]),
        fetched_at=datetime.fromisoformat(document["fetched_at"]),
        source_hero_list=str(document["source_hero_list"]),
        hero_count=int(document["hero_count"]),
        content_hash=str(document["content_hash"]),
        entries=entries,
    )
    expected = hashlib.sha256(canonical_payload(entries).encode("utf-8")).hexdigest()
    if index.content_hash != expected:
        raise PortraitIndexError("index content_hash does not match entries")
    return index

def download_hero_portrait(
    hero_id: int, *, client: httpx.Client | None = None
) -> tuple[bytes, str]:
    """Fetch one official hero portrait. No API key; raises PortraitIndexError on failure."""
    url = hero_portrait_url(hero_id)
    own_client = client is None
    actual_client = client or httpx.Client(
        timeout=DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=True
    )
    try:
        response = actual_client.get(url)
        response.raise_for_status()
        if len(response.content) > MAX_DOWNLOAD_BYTES:
            raise PortraitIndexError(
                f"portrait too large: {len(response.content)} bytes for {url}"
            )
        return response.content, url
    except httpx.HTTPError as exc:
        raise PortraitIndexError(f"download failed for {url}: {exc}") from exc
    finally:
        if own_client:
            actual_client.close()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
# --- end of portrait_index.py ---
