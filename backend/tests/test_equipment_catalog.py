
from app.equipment_catalog import build_equipment_rules, load_catalog
from app.emergency_swap import recommend_emergency_swap
from app.hero_profiles import build_threat_profiles, load_hero_catalog


def test_item_catalog_loads_real_official_items_with_metadata():
    catalog = load_catalog()
    assert len(catalog) >= 100
    revive = catalog[1337]
    assert revive.name == "贤者的庇护"
    assert revive.total_price == 2280
    assert "复活" in (revive.passive_or_active or "")
    gold_zhang = catalog[1239]
    assert gold_zhang.name == "辉月"
    assert gold_zhang.total_price == 2080


def test_equipment_rules_carry_constraints_and_functions():
    rules = {rule.item_id: rule for rule in build_equipment_rules(load_catalog())}
    revive = rules[1337]
    assert revive.max_match_uses == 2
    assert revive.functions >= {"revive", "survival"}
    boots = rules[1422]
    assert boots.unique_group == "boots"
    assert boots.functions >= {"tenacity", "magic_resist"}
    assert boots.total_price == 700


def test_emergency_swap_respects_revive_limit_and_gold():
    rules = build_equipment_rules(load_catalog())
    advice = recommend_emergency_swap(
        gold=500,
        owned_item_ids=[1423],
        rules=rules,
        revive_uses_used=2,
        needs_tenacity=True,
    )
    assert advice.revive_uses_remaining == 0
    assert any("复活甲" in warning for warning in advice.warnings)
    assert not any(s.target_item_id == 1337 for s in advice.suggestions)
    swap = next((s for s in advice.suggestions if s.action == "swap_now" and s.target_item_id == 1422), None)
    assert swap is None or swap.cost > 500


def test_emergency_swap_recommends_tenacity_boots_swap_when_affordable():
    rules = build_equipment_rules(load_catalog())
    advice = recommend_emergency_swap(
        gold=1200,
        owned_item_ids=[1423],
        rules=rules,
        revive_uses_used=0,
        needs_tenacity=True,
    )
    swap = next((s for s in advice.suggestions if s.target_item_id == 1422), None)
    assert swap is not None
    assert swap.action == "swap_now"
    assert swap.replace_item_id == 1423


def test_hero_profiles_load_official_catalog_and_keep_examples():
    heroes = load_hero_catalog()
    assert len(heroes) >= 100
    profiles = build_threat_profiles(heroes)
    assert profiles[109].name == "妲己"
    assert 101 in profiles  # documented example kept for tests/demo
    assert profiles[101].name == "示例控制法师"
    assert profiles[102].tags >= {"healing"}


def test_unknown_hero_ids_still_disclosed_when_profile_missing():
    heroes = load_hero_catalog()
    profiles = build_threat_profiles(heroes)
    assert 999999 not in profiles
