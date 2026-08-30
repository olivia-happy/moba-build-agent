from app.match_state import Component, ItemRule, MatchState, plan_purchase


def test_plan_purchase_suggests_affordable_component_before_expensive_item():
    item = ItemRule(
        item_id=10,
        name="防御大件",
        price=2100,
        functions={"magic_resist"},
        evidence="提供法术防御",
        components=[Component(item_id=11, name="抗魔披风", price=220)],
    )

    plan = plan_purchase(MatchState(gold=400, owned_item_ids=set()), item)

    assert plan.status == "buy_component"
    assert plan.next_item_id == 11
    assert plan.reason == "full_item_not_affordable"


def test_plan_purchase_requires_boot_replacement_when_unique_group_is_occupied():
    cooldown_boots = ItemRule(1, "冷静之靴", 710, {"haste"}, "提供冷却", unique_group="boots")
    tenacity_boots = ItemRule(2, "抵抗之靴", 710, {"tenacity"}, "提供韧性", unique_group="boots")

    plan = plan_purchase(
        MatchState(gold=900, owned_item_ids={1}, owned_rules={1: cooldown_boots}),
        tenacity_boots,
    )

    assert plan.status == "replace_required"
    assert plan.replace_item_id == 1
    assert plan.next_item_id == 2


def test_plan_purchase_does_not_recommend_exhausted_limited_use_item():
    revive_item = ItemRule(
        20,
        "复活装备",
        2080,
        {"revive"},
        "提供复活效果",
        max_match_uses=2,
    )

    plan = plan_purchase(
        MatchState(gold=2500, owned_item_ids=set(), item_use_counts={20: 2}), revive_item
    )

    assert plan.status == "unavailable"
    assert plan.reason == "match_use_limit_reached"
