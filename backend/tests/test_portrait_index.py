from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.portrait_index import (
    PORTRAIT_GRID_SIZE,
    SCHEMA_VERSION,
    PortraitIndexError,
    build_entry,
    downsample_to_grid,
    hero_portrait_url,
    index_entries,
    index_to_json,
    load_index,
    rgb_to_luminance,
)

LUM = [
    0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150,
    255, 240, 230, 220, 210, 200, 190, 180, 170, 160, 150, 140, 130, 120, 110, 100,
]


def test_portrait_url_uses_public_cdn_template():
    assert hero_portrait_url(105) == (
        "https://game.gtimg.cn/images/yxzj/img201606/heroimg/105/105.jpg"
    )


def test_rgb_to_luminance_matches_android_extractor():
    assert rgb_to_luminance(0x000000) == 0
    assert rgb_to_luminance(0xFFFFFF) == 255
    assert 70 <= rgb_to_luminance(0xFF0000) <= 80
    assert 145 <= rgb_to_luminance(0x00FF00) <= 155
    assert 25 <= rgb_to_luminance(0x0000FF) <= 35


def test_downsample_preserves_fixed_grid_size_and_bounds():
    grid = downsample_to_grid(LUM, 8, 4, grid_size=4)
    assert len(grid) == 16
    assert all(0 <= value <= 255 for value in grid)


def test_entry_hash_stable_across_calls():
    first = build_entry(
        hero_id=105, hero_name="Hero105", source_url=hero_portrait_url(105),
        luminance=LUM, width=8, height=4,
    )
    second = build_entry(
        hero_id=105, hero_name="Hero105", source_url=hero_portrait_url(105),
        luminance=LUM, width=8, height=4,
    )
    assert first.content_hash == second.content_hash
    assert len(first.content_hash) == 64


def test_index_roundtrip_preserves_hash_and_order(tmp_path):
    entries = [
        build_entry(
            hero_id=107, hero_name="Hero107", source_url=hero_portrait_url(107),
            luminance=LUM, width=8, height=4,
        ),
        build_entry(
            hero_id=105, hero_name="Hero105", source_url=hero_portrait_url(105),
            luminance=LUM, width=8, height=4,
        ),
    ]
    index = index_entries(
        entries=entries, fetched_at=datetime(2026, 8, 19, tzinfo=timezone.utc),
    )
    assert index.hero_count == 2
    assert [entry.hero_id for entry in index.entries] == [105, 107]

    path = tmp_path / "portrait_index.json"
    path.write_text(index_to_json(index), encoding="utf-8")
    loaded = load_index(path)
    assert loaded.content_hash == index.content_hash
    assert loaded.schema_version == SCHEMA_VERSION
    assert loaded.grid_size == PORTRAIT_GRID_SIZE


def test_load_index_rejects_tampered_hash(tmp_path):
    index = index_entries(
        entries=[
            build_entry(
                hero_id=105, hero_name="Hero105", source_url=hero_portrait_url(105),
                luminance=LUM, width=8, height=4,
            ),
        ],
        fetched_at=datetime(2026, 8, 19, tzinfo=timezone.utc),
    )
    path = tmp_path / "portrait_index.json"
    path.write_text(index_to_json(index), encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        '"hero_name": "Hero105"', '"hero_name": "Tampered"', 1,
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(PortraitIndexError):
        load_index(path)
