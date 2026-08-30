from app.frame_analysis import (
    DRAFT_LAYOUT_VERSION,
    MatchCandidate,
    analyze_frame,
    decode_rgba,
    layout_crops,
    rank_candidates,
)
from app.portrait_index import PortraitEntry, build_entry


def _entry(hero_id: int, name: str, grid_values: list[int]) -> PortraitEntry:
    # Reuse the same luminance-grid hashing as the index builder.
    payload = ",".join(str(v) for v in grid_values)
    return PortraitEntry(
        hero_id=hero_id,
        hero_name=name,
        source_url="https://example.invalid/portrait",
        content_hash="placeholder",
        width=1,
        height=len(grid_values),
        grid=tuple(grid_values),
    )


def _solid_rgba(red: int, green: int, blue: int, width: int, height: int) -> bytes:
    return bytes([red, green, blue, 255]) * (width * height)


def test_decode_rgba_converts_rgb_to_luminance_with_rec709_weights():
    pixels = _solid_rgba(255, 0, 0, 1, 1) + _solid_rgba(0, 255, 0, 1, 1)
    luminance = decode_rgba(pixels, 2, 1)

    assert len(luminance) == 2
    assert luminance[0] == int(0.299 * 255)
    assert luminance[1] == int(0.587 * 255)


def test_layout_crops_are_normalized_and_versioned():
    crops = layout_crops(1080, 2400)

    assert len(crops) == 5
    assert DRAFT_LAYOUT_VERSION.startswith("draft-layout")
    assert crops[0].left == 784
    assert crops[0].top == 312
    assert crops[0].width == 112
    assert crops[0].height == 112


def test_rank_candidates_orders_references_by_luminance_distance():
    references = [
        _entry(105, "Hero105", list(range(16 * 16))),
        _entry(106, "Hero106", [0] * (16 * 16)),
    ]
    sample = [0] * (16 * 16)

    ranked = rank_candidates(sample, references, limit=2)

    assert ranked[0].hero_id == 106
    assert ranked[0].confidence == 1.0
    assert ranked[1].hero_id == 105
    assert ranked[0].confidence > ranked[1].confidence


def test_analyze_frame_returns_top3_candidates_for_each_slot():
    references = [
        _entry(105, "Hero105", [10] * (16 * 16)),
        _entry(106, "Hero106", [30] * (16 * 16)),
        _entry(107, "Hero107", [20] * (16 * 16)),
    ]
    # Small synthetic frame (500x1000) still exercises decode+crop+downsample.
    rgba = _solid_rgba(10, 10, 10, 500, 1000)

    slots = analyze_frame(rgba, 500, 1000, references)

    assert len(slots) == 5
    first = slots[0]
    assert first.candidates[0].hero_id == 105
    assert first.candidates[0].confidence >= 0.9
    assert len(first.candidates) == 3
    assert all(isinstance(c, MatchCandidate) for c in first.candidates)
