"""Transparent enemy-lineup threat aggregation for build recommendations."""

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class HeroThreatProfile:
    hero_id: int
    name: str
    tags: set[str]


@dataclass(frozen=True)
class EnemyLineupAnalysis:
    counts: dict[str, int]
    priority_needs: list[str]
    unknown_hero_ids: list[int]


def analyse_enemy_lineup(
    hero_ids: Sequence[int], profiles: Mapping[int, HeroThreatProfile]
) -> EnemyLineupAnalysis:
    counts: dict[str, int] = {}
    unknown_hero_ids: list[int] = []
    for hero_id in hero_ids:
        profile = profiles.get(hero_id)
        if profile is None:
            unknown_hero_ids.append(hero_id)
            continue
        for tag in profile.tags:
            counts[tag] = counts.get(tag, 0) + 1

    needs: list[str] = []
    if counts.get("healing", 0):
        needs.append("anti_heal")
    if counts.get("magic_burst", 0):
        needs.append("magic_resist")
    if counts.get("crowd_control", 0):
        needs.append("tenacity")
    if counts.get("physical_burst", 0) >= 2:
        needs.append("physical_defense")
    if counts.get("physical_sustain", 0) >= 2:
        needs.append("anti_sustain")
    return EnemyLineupAnalysis(
        counts=counts,
        priority_needs=needs,
        unknown_hero_ids=unknown_hero_ids,
    )
