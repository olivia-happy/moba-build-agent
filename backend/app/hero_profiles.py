
"""Hero threat profiles backed by the official hero catalog.

The catalog file (data/hero_catalog_raw.json, source pvp.qq.com) provides the
authoritative hero id -> name mapping and roles. Threat tags are human-reviewed
and editable in one place; unknown heroes are always disclosed instead of
guessed. Tags drive the build decision engine (anti_heal / magic_resist /
tenacity / physical_defense / anti_sustain).

The 101/102 entries are documented example profiles (kept for offline demos and
tests); they are NOT real catalog heroes and are clearly marked as examples.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "hero_catalog_raw.json"
SOURCE_URL = "https://pvp.qq.com/web201605/js/herolist.json"


@dataclass(frozen=True)
class CatalogHero:
    hero_id: int
    name: str
    hero_type: int | None
    roles: list[str]


def load_hero_catalog(path: Path = CATALOG_PATH) -> list[CatalogHero]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    heroes: list[CatalogHero] = []
    for raw in payload.get("heroes", []):
        ename = raw.get("ename")
        cname = raw.get("cname")
        if ename is None or not cname:
            continue
        heroes.append(
            CatalogHero(
                hero_id=int(ename),
                name=str(cname),
                hero_type=int(raw["hero_type"]) if raw.get("hero_type") is not None else None,
                roles=[role for role in str(raw.get("roles") or "").split("|") if role],
            )
        )
    return heroes


# Human-reviewed threat tags. Extend this dict as profiles are reviewed; the
# catalog is the source for names, this file is the source for mechanics.
_THREAT_TAGS: dict[int, set[str]] = {
    101: {"magic_burst", "crowd_control"},
    102: {"physical_sustain", "healing"},
    108: {"magic_burst", "crowd_control"},
    109: {"magic_burst"},
    110: {"magic_burst"},
    115: {"magic_burst", "healing"},
    118: {"healing", "crowd_control", "movement_speed"},
    119: {"magic_burst", "healing"},
    127: {"magic_burst", "crowd_control"},
    133: {"physical_burst"},
    141: {"magic_burst", "true_damage", "physical_sustain"},
    142: {"magic_burst", "crowd_control"},
    144: {"physical_sustain", "healing"},
    146: {"magic_burst", "mobility"},
    149: {"physical_sustain", "shield"},
    156: {"magic_burst", "crowd_control"},
    157: {"magic_burst", "mobility"},
    162: {"physical_sustain", "true_damage"},
    163: {"magic_burst", "crowd_control"},
    166: {"magic_burst", "mobility"},
    167: {"physical_burst", "mobility"},
    173: {"physical_sustain", "healing"},
    175: {"magic_burst", "crowd_control"},
    177: {"physical_burst", "mobility"},
    182: {"magic_burst", "mobility"},
    184: {"physical_sustain", "healing"},
    186: {"physical_sustain", "healing"},
    189: {"physical_burst", "mobility"},
    190: {"physical_sustain", "true_damage"},
    191: {"magic_burst", "crowd_control"},
    194: {"physical_sustain", "healing"},
    501: {"magic_burst", "mobility"},
    502: {"physical_sustain", "shield"},
    503: {"magic_burst", "crowd_control"},
    504: {"magic_burst", "mobility"},
    505: {"physical_sustain", "healing"},
    506: {"physical_burst", "mobility"},
    507: {"magic_burst", "crowd_control"},
    508: {"physical_sustain", "mobility"},
    509: {"magic_burst", "mobility"},
    510: {"physical_sustain", "shield"},
    511: {"magic_burst", "crowd_control"},
    513: {"physical_sustain", "true_damage"},
    514: {"magic_burst", "mobility"},
    515: {"magic_burst", "crowd_control"},
    517: {"physical_sustain", "healing"},
    518: {"magic_burst", "mobility"},
    519: {"physical_sustain", "shield"},
    521: {"magic_burst", "crowd_control"},
    522: {"magic_burst", "mobility"},
    523: {"physical_sustain", "healing"},
    524: {"physical_burst", "mobility"},
    525: {"magic_burst", "mobility"},
    527: {"physical_sustain", "mobility"},
    528: {"magic_burst", "crowd_control"},
    529: {"physical_sustain", "shield"},
    531: {"magic_burst", "mobility"},
    533: {"physical_sustain", "healing"},
    534: {"magic_burst", "crowd_control"},
    536: {"magic_burst", "mobility"},
    537: {"physical_burst", "mobility"},
    538: {"physical_sustain", "mobility"},
    540: {"magic_burst", "mobility"},
    542: {"physical_sustain", "mobility"},
    544: {"physical_sustain", "mobility"},
    545: {"magic_burst", "mobility"},
    547: {"magic_burst", "crowd_control"},
    548: {"physical_sustain", "shield"},
    549: {"magic_burst", "mobility"},
    550: {"physical_sustain", "mobility"},
    558: {"magic_burst", "mobility"},
    563: {"magic_burst", "crowd_control"},
    564: {"physical_sustain", "mobility"},
    577: {"magic_burst", "mobility"},
    581: {"magic_burst", "mobility"},
    582: {"physical_sustain", "mobility"},
    583: {"magic_burst", "mobility"},
    584: {"physical_sustain", "mobility"},
    585: {"magic_burst", "mobility"},
}

# Example profiles used by tests/demo; not part of the official catalog.
_EXAMPLE_PROFILES: dict[int, tuple[str, set[str]]] = {
    101: ("示例控制法师", {"magic_burst", "crowd_control"}),
    102: ("示例回复战士", {"physical_sustain", "healing"}),
}


def build_threat_profiles(
    catalog: Iterable[CatalogHero],
    extra: Mapping[int, set[str]] | None = None,
) -> dict[int, "HeroThreatProfile"]:
    from app.lineup_threats import HeroThreatProfile

    merged = dict(_THREAT_TAGS)
    if extra:
        for hero_id, tags in extra.items():
            merged.setdefault(int(hero_id), set()).update(tags)

    names: dict[int, str] = {}
    for hero in catalog:
        names[hero.hero_id] = hero.name

    profiles: dict[int, HeroThreatProfile] = {}
    for hero in catalog:
        profiles[hero.hero_id] = HeroThreatProfile(
            hero_id=hero.hero_id,
            name=hero.name,
            tags=set(merged.get(hero.hero_id, set())),
        )
    # Keep documented example profiles for offline demos/tests even though
    # they are not in the official catalog.
    for hero_id, (name, tags) in _EXAMPLE_PROFILES.items():
        profiles.setdefault(hero_id, HeroThreatProfile(hero_id=hero_id, name=name, tags=set(tags)))
    return profiles
