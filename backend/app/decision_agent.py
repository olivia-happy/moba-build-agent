
"""Compose explicit lineup, item, and economy rules into local advice."""

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from app.build_recommendations import ItemFunctionProfile, recommend_items
from app.equipment_catalog import EquipmentRule
from app.emergency_swap import EmergencySwapAdvice, recommend_emergency_swap
from app.lineup_threats import HeroThreatProfile, analyse_enemy_lineup
from app.match_state import Component, ItemRule, MatchState, plan_purchase


ROLE_LABELS = {
    1: "战士",
    2: "法师",
    3: "坦克",
    4: "刺客",
    5: "射手",
    6: "辅助",
}


@dataclass(frozen=True)
class OwnHeroAdjustment:
    """An explainable adjustment caused by the player's own hero archetype."""

    code: str
    label: str
    added_needs: list[str]
    reason: str


def _own_hero_adjustments(
    *, own_hero_type: int | None, threat_counts: Mapping[str, int], current_needs: Sequence[str]
) -> list[OwnHeroAdjustment]:
    """Translate own-role fragility into explicit, testable purchase needs.

    Enemy threats remain the primary signal. Own-role rules only add the
    survivability or first-defense threshold that is appropriate for the hero
    the player is actually controlling; they never remove an enemy counter.
    """
    if own_hero_type is None:
        return []

    adjustments: list[OwnHeroAdjustment] = []
    burst_present = bool(threat_counts.get("magic_burst") or threat_counts.get("physical_burst"))
    fragile_roles = {2, 4, 5}  # mage / assassin / marksman
    durable_roles = {3, 6}  # tank / support

    if own_hero_type in fragile_roles and burst_present:
        adjustments.append(
            OwnHeroAdjustment(
                code="fragile_survival",
                label="脆皮优先保命",
                added_needs=["survival"],
                reason="当前英雄承伤容错较低，敌方已有爆发威胁，先补一件保命/减伤装备。",
            )
        )

    if own_hero_type in {2, 5} and threat_counts.get("physical_burst", 0) >= 1:
        if "physical_defense" not in current_needs:
            adjustments.append(
                OwnHeroAdjustment(
                    code="backline_physical_defense",
                    label="后排先补物防",
                    added_needs=["physical_defense"],
                    reason="法师/射手站位靠后但更怕刺客或物理爆发，单个明确威胁也触发第一件物防。",
                )
            )

    if own_hero_type in durable_roles and threat_counts.get("physical_burst", 0) >= 1:
        if "physical_defense" not in current_needs:
            adjustments.append(
                OwnHeroAdjustment(
                    code="frontline_physical_defense",
                    label="前排提前堆物防",
                    added_needs=["physical_defense"],
                    reason="前排需要持续承伤，面对单个物理爆发也提前补物防，降低开团风险。",
                )
            )

    return adjustments


@dataclass(frozen=True)
class BuildDecisionInput:
    enemy_hero_ids: Sequence[int]
    profiles: Mapping[int, HeroThreatProfile]
    match_state: MatchState
    item_rules: Sequence[ItemRule]
    own_hero_type: int | None = None
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
    own_hero_adjustments: list[OwnHeroAdjustment] = field(default_factory=list)
    emergency_swap: EmergencySwapAdvice | None = None


def decide_next_purchase(request: BuildDecisionInput) -> BuildDecision:
    threat_analysis = analyse_enemy_lineup(request.enemy_hero_ids, request.profiles)
    own_adjustments = _own_hero_adjustments(
        own_hero_type=request.own_hero_type,
        threat_counts=threat_analysis.counts,
        current_needs=threat_analysis.priority_needs,
    )
    priority_needs = list(threat_analysis.priority_needs)
    for adjustment in own_adjustments:
        for need in adjustment.added_needs:
            if need not in priority_needs:
                priority_needs.append(need)

    recommendation_items = recommend_items(
        priority_needs=priority_needs,
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
        priority_needs=priority_needs,
        threat_counts=threat_analysis.counts,
        unknown_hero_ids=threat_analysis.unknown_hero_ids,
        recommendations=decisions,
        own_hero_adjustments=own_adjustments,
        emergency_swap=emergency,
    )
