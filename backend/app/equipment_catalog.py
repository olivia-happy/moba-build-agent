
"""Load the official in-game item catalog into explicit, evidence-bearing rules.

Source: https://pvp.qq.com/web201605/js/item.json (fetched once, hashed and
bundled under data/item_catalog_raw.json). Every rule the recommendation engine
uses points back to this catalog entry so players can audit price, effect,
components and per-match limits.
"""

from __future__ import annotations

import json
import re
import html
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "item_catalog_raw.json"
SOURCE_URL = "https://pvp.qq.com/web201605/js/item.json"


@dataclass(frozen=True)
class CatalogItem:
    item_id: int
    name: str
    item_type: int | None
    price: int | None
    total_price: int | None
    description: str
    passive_or_active: str | None


@dataclass(frozen=True)
class EquipmentRule:
    item_id: int
    name: str
    price: int
    total_price: int
    functions: set[str]
    evidence: str
    description: str
    source_url: str
    unique_group: str | None = None
    max_match_uses: int | None = None
    cooldown_seconds: int | None = None
    item_type: int | None = None


def _strip_tags(value: str | None) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def load_catalog(path: Path = CATALOG_PATH) -> dict[int, CatalogItem]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected_hash = payload.get("content_hash")
    computed = sha256(
        json.dumps(payload.get("items", []), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if expected_hash and computed != expected_hash:
        raise ValueError(f"item catalog content hash mismatch: expected {expected_hash}, got {computed}")
    items: dict[int, CatalogItem] = {}
    for raw in payload.get("items", []):
        item_id = raw.get("item_id")
        if item_id is None or not raw.get("item_name"):
            continue
        items[int(item_id)] = CatalogItem(
            item_id=int(item_id),
            name=str(raw["item_name"]),
            item_type=int(raw["item_type"]) if raw.get("item_type") is not None else None,
            price=int(raw["price"]) if raw.get("price") is not None else None,
            total_price=int(raw["total_price"]) if raw.get("total_price") is not None else None,
            description=_strip_tags(raw.get("des1")),
            passive_or_active=_strip_tags(raw.get("des2")),
        )
    return items


# Human-reviewed tags. These intentionally mirror official item text and can be
# edited in one place; the source of truth for numbers is the catalog file.
_FUNCTION_TAGS: dict[int, set[str]] = {
    1422: {"tenacity", "magic_resist", "boots"},
    1423: {"haste", "boots"},
    1335: {"magic_shield", "magic_resist"},
    1347: {"magic_resist", "sustain"},
    1336: {"physical_defense", "haste", "anti_attack_speed"},
    1327: {"physical_defense", "reflect"},
    1333: {"physical_defense", "anti_attack_speed", "slow"},
    1338: {"physical_defense", "damage", "speed"},
    1341: {"physical_defense", "slow", "engage"},
    11210: {"anti_heal", "physical_attack", "sustain"},
    12211: {"anti_heal", "magic_power"},
    1239: {"invulnerability", "survival"},
    1337: {"revive", "survival"},
    1127: {"death_avoid", "survival"},
    1328: {"shield", "survival"},
    11311: {"damage_reduction", "survival"},
    1111: {"physical_attack"},
    1112: {"attack_speed"},
    1113: {"crit"},
    1116: {"physical_attack", "crit"},
    1121: {"physical_attack"},
    1312: {"physical_defense"},
    1313: {"magic_resist"},
    1311: {"health"},
    1321: {"health"},
    1323: {"magic_resist", "health"},
    1325: {"physical_defense", "health"},
    1324: {"haste", "physical_defense", "mana"},
}

_BOOT_IDS = {1422, 1423}
_REVIVE_LIMIT = 2


def _cooldown(item_id: int, text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d+)\s*秒", text)
    return int(match.group(1)) if match else None


def build_equipment_rules(
    catalog: Mapping[int, CatalogItem], overrides: Sequence[dict[str, Any]] | None = None
) -> list[EquipmentRule]:
    """Turn catalog entries into recommendation rules with explicit constraints."""
    rules: list[EquipmentRule] = []
    for item_id, item in catalog.items():
        functions = set(_FUNCTION_TAGS.get(item_id, set()))
        text = (item.description or "") + " " + (item.passive_or_active or "")
        if "重伤" in text or "降低其35%生命回复" in text:
            functions.add("anti_heal")
        if "韧性" in text:
            functions.add("tenacity")
        if "法术护盾" in text or "魔抗" in text or "法术防御" in text:
            functions.add("magic_resist")
        if "护甲" in text or "物理防御" in text:
            functions.add("physical_defense")
        unique_group = "boots" if item_id in _BOOT_IDS else None
        max_uses = _REVIVE_LIMIT if item_id == 1337 else None
        cooldown = _cooldown(item_id, item.passive_or_active) if item_id in {1239, 1328, 11311} else None
        rules.append(
            EquipmentRule(
                item_id=item_id,
                name=item.name,
                price=item.price or 0,
                total_price=item.total_price or item.price or 0,
                functions=functions,
                evidence=f"{item.name}：{text}",
                description=text,
                source_url=SOURCE_URL,
                unique_group=unique_group,
                max_match_uses=max_uses,
                cooldown_seconds=cooldown,
                item_type=item.item_type,
            )
        )
    if overrides:
        by_id = {rule.item_id: rule for rule in rules}
        for override in overrides:
            item_id = int(override["item_id"])
            current = by_id.get(item_id)
            if current is None:
                continue
            merged = {
                "item_id": current.item_id,
                "name": override.get("name", current.name),
                "price": override.get("price", current.price),
                "total_price": override.get("total_price", current.total_price),
                "functions": set(override.get("functions", current.functions)),
                "evidence": override.get("evidence", current.evidence),
                "description": override.get("description", current.description),
                "source_url": override.get("source_url", current.source_url),
                "unique_group": override.get("unique_group", current.unique_group),
                "max_match_uses": override.get("max_match_uses", current.max_match_uses),
                "cooldown_seconds": override.get("cooldown_seconds", current.cooldown_seconds),
                "item_type": override.get("item_type", current.item_type),
            }
            idx = next((i for i, rule in enumerate(rules) if rule.item_id == item_id), None)
            if idx is not None:
                rules[idx] = EquipmentRule(**merged)
    return sorted(rules, key=lambda rule: rule.total_price)
