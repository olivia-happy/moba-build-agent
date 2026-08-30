from pathlib import Path

from app.portrait_index import (
    PortraitEntry,
    build_entry,
    index_entries,
    load_index,
    now_utc,
)
from app.game_catalog import build_catalog_snapshot

LUM = list(range(0, 256, 16)) + list(range(255, -1, -16))


def test_build_script_uses_catalog_and_produces_verifiable_artifact(tmp_path):
    snapshot = build_catalog_snapshot(
        heroes=[
            {"ename": 105, "cname": "Hero105", "hero_type": 3, "roles": "1|5"},
            {"ename": 106, "cname": "Hero106", "hero_type": 3, "roles": "1"},
        ],
        items=[],
        retrieved_at=now_utc(),
    )
    entries = [
        build_entry(
            hero_id=hero.hero_id,
            hero_name=hero.name,
            source_url=f"https://cdn/{hero.hero_id}.jpg",
            luminance=LUM[:8] * 8,
            width=8,
            height=8,
        )
        for hero in snapshot.heroes
    ]
    index = index_entries(entries=entries, fetched_at=now_utc())
    out = tmp_path / "portrait_index.json"
    out.write_text(_json(index), encoding="utf-8")
    loaded = load_index(out)
    assert loaded.hero_count == 2
    assert loaded.entries[0].hero_id == 105


def _json(index):
    from app.portrait_index import index_to_json
    return index_to_json(index)
