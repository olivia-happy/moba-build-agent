from app.decision_agent import BuildDecisionInput, decide_next_purchase
from app.lineup_threats import HeroThreatProfile
from app.match_state import Component, ItemRule, MatchState


def test_decision_agent_links_enemy_threat_to_affordable_purchase_evidence():
    enemy_profiles = {
        10: HeroThreatProfile(hero_id=10, name="控制法师", tags={"magic_burst", "crowd_control"}),
    }
    items = [
        ItemRule(
            item_id=2,
            name="抵抗之靴",
            price=710,
            functions={"tenacity", "magic_resist"},
            evidence="提供韧性与法术防御",
            components=[Component(item_id=3, name="神速之靴", price=250)],
            unique_group="boots",
        )
    ]

    decision = decide_next_purchase(
        BuildDecisionInput(
            enemy_hero_ids=[10],
            profiles=enemy_profiles,
            match_state=MatchState(gold=400, owned_item_ids=set()),
            item_rules=items,
        )
    )

    assert decision.priority_needs == ["magic_resist", "tenacity"]
    assert decision.recommendations[0].item_name == "抵抗之靴"
    assert decision.recommendations[0].purchase_status == "buy_component"
    assert decision.recommendations[0].next_item_name == "神速之靴"
    assert decision.recommendations[0].evidence == "提供韧性与法术防御"
