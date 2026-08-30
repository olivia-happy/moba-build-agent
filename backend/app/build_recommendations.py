"""Map explicit lineup needs to evidence-bearing item suggestions."""

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ItemFunctionProfile:
    item_id: int
    name: str
    functions: set[str]
    evidence: str


@dataclass(frozen=True)
class ItemRecommendation:
    item_id: int
    name: str
    covered_needs: list[str]
    evidence: str


def recommend_items(
    *,
    priority_needs: Sequence[str],
    items: Iterable[ItemFunctionProfile],
    owned_item_ids: set[int],
) -> list[ItemRecommendation]:
    """Greedily cover needs in declared priority order, never hiding evidence."""
    available = [item for item in items if item.item_id not in owned_item_ids]
    remaining = list(dict.fromkeys(priority_needs))
    recommendations: list[ItemRecommendation] = []

    while remaining:
        first_need = remaining[0]
        candidates = [item for item in available if first_need in item.functions]
        if not candidates:
            remaining.pop(0)
            continue
        selected = max(
            candidates,
            key=lambda item: sum(need in item.functions for need in remaining),
        )
        covered = [need for need in remaining if need in selected.functions]
        recommendations.append(
            ItemRecommendation(
                item_id=selected.item_id,
                name=selected.name,
                covered_needs=covered,
                evidence=selected.evidence,
            )
        )
        available.remove(selected)
        remaining = [need for need in remaining if need not in selected.functions]
    return recommendations
