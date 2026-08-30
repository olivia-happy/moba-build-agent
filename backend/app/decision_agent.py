
"""Compose explicit lineup, item, and economy rules into local advice."""

from dataclasses import dataclass
from typing import Mapping, Sequence

from app.build_recommendations import ItemFunctionProfile, recommend_items
from app.equipment_catalog import EquipmentRule
from app.emergency_swap import EmergencySwapAdvice, recommend_emergency_swap
from app.lineup_threats import HeroThreatProfile, analyse_enemy_lineup
from app.match_state import Component, ItemRule, MatchState, plan_purchase


@dataclass(frozen=True)
class BuildDecisionInput:
    enemy_hero_ids: Sequence[int]
    profiles: Mapping[int, HeroThreatProfile]
    match_state: MatchState
    item_rules: Sequence[ItemRule]
    revive_uses_used: int = 0
    slot_capacity: int = 6
    needs_tenacity: bool = False
    equipment_rules: Sequence[EquipmentRule] = ()


@dataclass(frozen=True)
class PurchaseRecommendation:
    item_id: int
    item_name: str
    covered_needs: list[str]
    purchase_status: str
    next_item_id: int | None
    next_item_name: str | None
    replace_item_id: int | None
    evidence: str


@dataclass(frozen=True)
class BuildDecision:
    priority_needs: list[str]
    threat_counts: dict[str, int]
    unknown_hero_ids: list[int]
    recommendations: list[PurchaseRecommendation]
    emergency_swap: EmergencySwapAdvice | None = None


def decide_next_purchase(request: BuildDecisionInput) -> BuildDecision:
    threat_analysis = analyse_enemy_lineup(request.enemy_hero_ids, request.profiles)
    recommendation_items = recommend_items(
        priority_needs=threat_analysis.priority_needs,
        items=[
            ItemFunctionProfile(rule.item_id, rule.name, rule.functions, rule.evidence)
            for rule in request.item_rules
        ],
        owned_item_ids=request.match_state.owned_item_ids,
    )
    rule_by_id = {rule.item_id: rule for rule in request.item_rules}
    component_names = {
        component.item_id: component.name
        for rule in request.item_rules
        for component in rule.components
    }
    decisions = []
    for item in recommendation_items:
        purchase = plan_purchase(request.match_state, rule_by_id[item.item_id])
        decisions.append(
            PurchaseRecommendation(
                item_id=item.item_id,
                item_name=item.name,
                covered_needs=item.covered_needs,
                purchase_status=purchase.status,
                next_item_id=purchase.next_item_id,
                next_item_name=component_names.get(purchase.next_item_id, item.name),
                replace_item_id=purchase.replace_item_id,
                evidence=item.evidence,
            )
        )

    emergency: EmergencySwapAdvice | None = None
    if request.equipment_rules:
        emergency = recommend_emergency_swap(
            gold=request.match_state.gold,
            owned_item_ids=sorted(request.match_state.owned_item_ids),
            rules=request.equipment_rules,
            revive_uses_used=request.revive_uses_used,
            needs_tenacity=request.needs_tenacity or "tenacity" in threat_analysis.priority_needs,
            slot_capacity=request.slot_capacity,
        )
    return BuildDecision(
        priority_needs=threat_analysis.priority_needs,
        threat_counts=threat_analysis.counts,
        unknown_hero_ids=threat_analysis.unknown_hero_ids,
        recommendations=decisions,
        emergency_swap=emergency,
    )
