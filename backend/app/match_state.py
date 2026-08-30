
"""Versioned constraints for player-initiated in-match purchase decisions."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Component:
    item_id: int
    name: str
    price: int


@dataclass(frozen=True)
class ItemRule:
    item_id: int
    name: str
    price: int
    functions: set[str]
    evidence: str
    components: list[Component] = field(default_factory=list)
    unique_group: str | None = None
    max_match_uses: int | None = None
    cooldown_seconds: int | None = None


@dataclass(frozen=True)
class MatchState:
    gold: int
    owned_item_ids: set[int]
    owned_rules: dict[int, ItemRule] = field(default_factory=dict)
    item_use_counts: dict[int, int] = field(default_factory=dict)
    slot_capacity: int = 6


@dataclass(frozen=True)
class PurchasePlan:
    status: str
    next_item_id: int | None
    reason: str
    replace_item_id: int | None = None


def plan_purchase(state: MatchState, target: ItemRule) -> PurchasePlan:
    """Return the next safe purchase action without automating any game operation."""
    if target.max_match_uses is not None and state.item_use_counts.get(target.item_id, 0) >= target.max_match_uses:
        return PurchasePlan("unavailable", None, "match_use_limit_reached")
    if target.item_id in state.owned_item_ids:
        return PurchasePlan("owned", target.item_id, "already_owned")

    if target.unique_group:
        for item_id, owned_rule in state.owned_rules.items():
            if owned_rule.unique_group == target.unique_group:
                return PurchasePlan("replace_required", target.item_id, "unique_group_occupied", item_id)

    if len(state.owned_item_ids) >= state.slot_capacity:
        return PurchasePlan("replace_required", target.item_id, "inventory_full")

    if state.gold >= target.price:
        return PurchasePlan("buy_now", target.item_id, "full_item_affordable")

    affordable_components = [component for component in target.components if component.price <= state.gold]
    if affordable_components:
        component = max(affordable_components, key=lambda item: item.price)
        return PurchasePlan("buy_component", component.item_id, "full_item_not_affordable")
    return PurchasePlan("save_for", target.item_id, "no_affordable_component")
