"""Analyze one user-authorized screen frame into ranked hero candidates.

This module is the backend twin of Android's FrameAnalyzer. It is used for
offline verification and unit tests with synthetic frames; the Android app
performs the same pipeline on-device and never uploads a screenshot. The two
implementations share the exact luminance weights, grid size, crop profile,
and ranking formula so results stay comparable.

Pipeline per enemy portrait slot:
  1. Decode raw RGBA bytes into a luminance array.
  2. Crop the portrait using the versioned layout profile (normalized coords).
  3. Downsample the crop to a fixed 16x16 luminance grid.
  4. Rank against the bundled portrait index and return Top-3 candidates
     with confidence. The player always confirms or corrects before advice.

Nothing here claims a single "correct" hero.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.portrait_index import PortraitEntry, PORTRAIT_GRID_SIZE, downsample_to_grid

# Versioned crop profile, aligned with Android HeroSelectLayout.
# Normalized coordinates on a 1080x2400 reference; 5 enemy portraits.
DRAFT_LAYOUT_VERSION = "draft-layout-1080x2400-v1"
ENEMY_PORTRAIT_CROPS: tuple[tuple[float, float, float, float], ...] = (
    (784 / 1080, 312 / 2400, 112 / 1080, 112 / 2400),
    (784 / 1080, 462 / 2400, 112 / 1080, 112 / 2400),
    (784 / 1080, 612 / 2400, 112 / 1080, 112 / 2400),
    (784 / 1080, 762 / 2400, 112 / 1080, 112 / 2400),
    (784 / 1080, 912 / 2400, 112 / 1080, 112 / 2400),
)


class FrameAnalysisError(RuntimeError):
    """Raised when a frame cannot be decoded or analyzed safely."""


@dataclass(frozen=True)
class CropSpec:
    slot_index: int
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class MatchCandidate:
    hero_id: int
    hero_name: str
    confidence: float


@dataclass(frozen=True)
class SlotAnalysis:
    slot_index: int
    crop: CropSpec
    candidates: tuple[MatchCandidate, ...]


def decode_rgba(rgba: bytes, width: int, height: int, stride: int | None = None) -> list[int]:
    """Decode raw RGBA bytes into a row-major luminance array."""
    if width <= 0 or height <= 0:
        raise FrameAnalysisError(f"invalid frame dimensions {width}x{height}")
    row_stride = stride or width * 4
    expected = row_stride * (height - 1) + width * 4
    if len(rgba) < expected:
        raise FrameAnalysisError(
            f"frame too small: {len(rgba)} bytes, need at least {expected} for {width}x{height}"
        )
    luminance: list[int] = []
    for y in range(height):
        row_start = y * row_stride
        for x in range(width):
            offset = row_start + x * 4
            red = rgba[offset]
            green = rgba[offset + 1]
            blue = rgba[offset + 2]
            luminance.append(int(0.299 * red + 0.587 * green + 0.114 * blue))
    return luminance


def crop_luminance(luminance: list[int], width: int, height: int, crop: CropSpec) -> tuple[list[int], int, int]:
    """Extract one crop as row-major luminance; clamps out-of-bounds like Android."""
    left = max(0, min(crop.left, width - 1))
    top = max(0, min(crop.top, height - 1))
    crop_width = max(1, min(crop.width, width - left))
    crop_height = max(1, min(crop.height, height - top))
    rows: list[int] = []
    for y in range(crop_height):
        start = (top + y) * width + left
        rows.extend(luminance[start : start + crop_width])
    return rows, crop_width, crop_height


def layout_crops(width: int, height: int) -> list[CropSpec]:
    return [
        CropSpec(
            slot_index=index,
            left=int(left * width),
            top=int(top * height),
            width=max(1, int(crop_w * width)),
            height=max(1, int(crop_h * height)),
        )
        for index, (left, top, crop_w, crop_h) in enumerate(ENEMY_PORTRAIT_CROPS)
    ]


def rank_candidates(
    sample: Iterable[int],
    references: Iterable[PortraitEntry],
    grid_size: int = PORTRAIT_GRID_SIZE,
    limit: int = 3,
) -> list[MatchCandidate]:
    """Rank reference grids by mean absolute luminance distance; 1.0 = identical."""
    sample_list = list(sample)
    if len(sample_list) != grid_size * grid_size:
        raise FrameAnalysisError(
            f"sample must be {grid_size * grid_size} cells, got {len(sample_list)}"
        )
    scored: list[tuple[float, PortraitEntry]] = []
    for entry in references:
        if len(entry.grid) != len(sample_list):
            continue
        total = 0.0
        for index, value in enumerate(sample_list):
            total += abs(value - entry.grid[index])
        max_distance = len(sample_list) * 255.0
        confidence = 1.0 - total / max_distance
        scored.append((confidence, entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        MatchCandidate(hero_id=entry.hero_id, hero_name=entry.hero_name, confidence=round(conf, 4))
        for conf, entry in scored[:limit]
    ]


def analyze_frame(
    rgba: bytes,
    width: int,
    height: int,
    references: Iterable[PortraitEntry],
    stride: int | None = None,
) -> list[SlotAnalysis]:
    """Full pipeline: decode -> crop -> downsample -> rank (Top-3 per slot)."""
    luminance = decode_rgba(rgba, width, height, stride)
    results: list[SlotAnalysis] = []
    for crop in layout_crops(width, height):
        cropped, crop_width, crop_height = crop_luminance(luminance, width, height, crop)
        grid = downsample_to_grid(cropped, crop_width, crop_height)
        results.append(
            SlotAnalysis(
                slot_index=crop.slot_index,
                crop=crop,
                candidates=tuple(rank_candidates(grid, references)),
            )
        )
    return results
