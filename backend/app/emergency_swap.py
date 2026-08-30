
"""Emergency swap advice for last-second survivability purchases.

Covers the classic quick-swap patterns players ask about:
  - 辉月(金身) / 贤者的庇护(复活甲) / 名刀 / 血魔之怒 / 纯净苍穹 as "save me" actives
  - 冷静之靴 -> 抵抗之靴 when enemy control matters

Every suggestion is constrained by gold, inventory slots, unique groups and the
per-match revive limit, and returns explicit evidence + why_now text so the
player can audit the reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from app.equipment_catalog import EquipmentRule


@dataclass(frozen=True)
class EmergencySwapOption:
    action: str
    target_item_id: int
    target_item_name: str
    cost: int
    reason: str
    why_now: str
    evidence: str
    constraints: list[str] = field(default_factory=list)
    replace_item_id: int | None = None


@dataclass(frozen=True)
class EmergencySwapAdvice:
    suggestions: list[EmergencySwapOption]
    remaining_gold: int
    inventory_slots_free: int
    revive_uses_remaining: int | None
    warnings: list[str] = field(default_factory=list)


_SURVIVAL_PRIORITY = [1239, 1337, 1127, 1328, 11311]


def _rule_by_id(rules: Iterable[EquipmentRule]) -> dict[int, EquipmentRule]:
    return {rule.item_id: rule for rule in rules}


def _boots_swap_advice(
    state_gold: int,
    owned_item_ids: set[int],
    rules: Mapping[int, EquipmentRule],
    needs_tenacity: bool,
) -> list[EmergencySwapOption]:
    suggestions: list[EmergencySwapOption] = []
    tenacity_boots = rules.get(1422)
    cooldown_boots = rules.get(1423)
    if not needs_tenacity or tenacity_boots is None or cooldown_boots is None:
        return suggestions
    if 1422 in owned_item_ids:
        return suggestions
    if 1423 not in owned_item_ids:
        suggestions.append(
            EmergencySwapOption(
                action="consider_buying",
                target_item_id=1422,
                target_item_name=tenacity_boots.name,
                cost=tenacity_boots.total_price,
                reason="敌方法术控制偏多",
                why_now="控住一次可能就是一波团灭；抵抗之靴的韧性直接缩短被控时间。",
                evidence=tenacity_boots.evidence,
                constraints=["鞋子移速不叠加，买了抵抗之靴后原来的冷静之靴效果不叠加"],
            )
        )
        return suggestions
    if state_gold >= tenacity_boots.total_price:
        suggestions.append(
            EmergencySwapOption(
                action="swap_now",
                target_item_id=1422,
                target_item_name=tenacity_boots.name,
                cost=tenacity_boots.total_price,
                reason="你已持有冷静之靴，敌方控制偏多",
                why_now="把冷静之靴换成抵抗之靴，韧性收益远高于继续攒冷却。",
                evidence=tenacity_boots.evidence,
                constraints=["鞋子移速不叠加", "需要预留足够金币完成置换"],
                replace_item_id=1423,
            )
        )
    return suggestions


def _survival_swap_advice(
    state_gold: int,
    owned_item_ids: set[int],
    rules: Mapping[int, EquipmentRule],
    revive_uses: int,
    slot_capacity: int,
) -> list[EmergencySwapOption]:
    suggestions: list[EmergencySwapOption] = []
    owned_survival = [item_id for item_id in _SURVIVAL_PRIORITY if item_id in owned_item_ids]
    free_slots = slot_capacity - len(owned_item_ids)
    warnings: list[str] = []

    for item_id in _SURVIVAL_PRIORITY:
        rule = rules.get(item_id)
        if rule is None:
            continue
        if item_id in owned_item_ids:
            continue
        if item_id == 1337 and revive_uses >= (rule.max_match_uses or 0):
            warnings.append("复活甲本局已用完，不能继续购买。")
            continue
        cost = rule.total_price
        constraints: list[str] = []
        if rule.max_match_uses is not None:
            constraints.append(f"复活甲每局最多 {rule.max_match_uses} 次")
        if rule.cooldown_seconds is not None:
            constraints.append(f"主动冷却约 {rule.cooldown_seconds} 秒")
        if item_id == 1239:
            why_now = "残血/被集火瞬间开金身免疫 1.5 秒，拖到队友支援。"
        elif item_id == 1337:
            why_now = "吃到致命伤害后原地复活，适合有复活次数时拼一波。"
        elif item_id == 1127:
            why_now = "名刀是廉价的免死备选，且可以和其他保命装并存。"
        elif item_id == 1328:
            why_now = "血魔主动给盾，适合在被秒前开出来。"
        else:
            why_now = "纯净苍穹主动减伤 30%，适合开团时提前开启。"
        action = "buy_now" if state_gold >= cost else "save_for"
        suggestions.append(
            EmergencySwapOption(
                action=action,
                target_item_id=item_id,
                target_item_name=rule.name,
                cost=cost,
                reason="保命备选",
                why_now=why_now,
                evidence=rule.evidence,
                constraints=constraints,
            )
        )

    if owned_survival and free_slots <= 0:
        warnings.append("装备栏已满，秒换需要在商店里先卖出旧装备再购买新装备。")
    return suggestions


def recommend_emergency_swap(
    *,
    gold: int,
    owned_item_ids: Sequence[int],
    rules: Iterable[EquipmentRule],
    revive_uses_used: int = 0,
    needs_tenacity: bool = False,
    slot_capacity: int = 6,
) -> EmergencySwapAdvice:
    rule_by_id = _rule_by_id(rules)
    owned = set(owned_item_ids)
    revive_rule = rule_by_id.get(1337)
    revive_uses_remaining = (
        revive_rule.max_match_uses - revive_uses_used if revive_rule and revive_rule.max_match_uses is not None else None
    )
    suggestions = _survival_swap_advice(
        state_gold=gold,
        owned_item_ids=owned,
        rules=rule_by_id,
        revive_uses=revive_uses_used,
        slot_capacity=slot_capacity,
    )
    suggestions.extend(
        _boots_swap_advice(
            state_gold=gold,
            owned_item_ids=owned,
            rules=rule_by_id,
            needs_tenacity=needs_tenacity,
        )
    )
    warnings: list[str] = []
    if revive_uses_remaining is not None and revive_uses_remaining <= 0:
        warnings.append("复活甲次数已用完。")
    if len(owned) >= slot_capacity:
        warnings.append("装备栏已满，秒换需要在商店里先卖出旧装备再购买新装备。")
    return EmergencySwapAdvice(
        suggestions=suggestions,
        remaining_gold=gold,
        inventory_slots_free=max(0, slot_capacity - len(owned)),
        revive_uses_remaining=revive_uses_remaining,
        warnings=warnings,
    )
