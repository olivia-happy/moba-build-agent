from app.build_recommendations import ItemFunctionProfile, recommend_items


def test_recommend_items_covers_priority_needs_without_recommending_owned_item():
    items = [
        ItemFunctionProfile(1, "制裁之刃", {"anti_heal"}, "造成伤害后降低回复效果"),
        ItemFunctionProfile(2, "魔女斗篷", {"magic_resist"}, "提供法术防御与护盾"),
        ItemFunctionProfile(3, "抵抗之靴", {"tenacity", "magic_resist"}, "提供韧性与法术防御"),
    ]

    recommendations = recommend_items(
        priority_needs=["anti_heal", "magic_resist", "tenacity"],
        items=items,
        owned_item_ids={2},
    )

    assert [item.item_id for item in recommendations] == [1, 3]
    assert recommendations[0].covered_needs == ["anti_heal"]
    assert recommendations[1].covered_needs == ["magic_resist", "tenacity"]
    assert recommendations[1].evidence == "提供韧性与法术防御"


def test_recommend_items_reports_uncovered_need_when_catalog_lacks_a_match():
    recommendations = recommend_items(
        priority_needs=["anti_heal"],
        items=[],
        owned_item_ids=set(),
    )

    assert recommendations == []
