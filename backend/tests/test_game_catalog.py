from datetime import datetime, timezone

from app.game_catalog import build_catalog_snapshot


def test_catalog_snapshot_preserves_source_version_and_normalized_items():
    snapshot = build_catalog_snapshot(
        heroes=[{"ename": 105, "cname": "廉颇", "hero_type": 3, "roles": "1|5"}],
        items=[
            {
                "item_id": 250,
                "item_name": "铁剑",
                "item_type": 1,
                "price": 250,
                "total_price": 250,
                "des1": "<p>+20物理攻击</p>",
            }
        ],
        retrieved_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
    )

    assert snapshot.source == "pvp.qq.com"
    assert snapshot.hero_count == 1
    assert snapshot.item_count == 1
    assert snapshot.items[0].description == "+20物理攻击"
    assert len(snapshot.content_hash) == 64
