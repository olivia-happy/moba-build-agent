import sys, io
sys.stdout.reconfigure(encoding="utf-8")
content = """"Evidence-first local equipment knowledge base for the in-match build agent.

Why this exists
---------------
Players often follow system recommendations without understanding what each
item does. This module turns the official public item catalog into a
versioned, evidence-traceable knowledge base: every item carries its price,
function tags, passive/active description, unique group, per-match use limits,
and emergency-swap rules (辉月->复活甲, 复活甲->辉月, 冷静鞋->抵抗鞋).

The raw catalog is fetched from the official public endpoint and stored as
`data/item_catalog_raw.json` (source URL + content hash), so every
recommendation can be traced back to the exact official description.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import httpx

ITEM_CATALOG_URL = "https://pvp.qq.com/web201605/js/item.json"
ITEM_CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "item_catalog_raw.json"

# Normalized function tags used by the recommendation engine.
FUNCTION_TAGS = {
    "tenacity", "magic_resist", "physical_defense", "anti_heal",
    "revive", "invincible", "shield", "damage_reduction", "haste",
    "physical_damage", "magic_damage", "attack_speed", "crit",
    "life_steal", "spell_vamp", "movement_speed", "health",
}

# Items that can be emergency-swapped in the shop (辉月/复活甲/名刀/血魔/纯净苍穹).
EMERGENCY_SWAP_PAIRS: tuple[tuple[int, int, str], ...] = (
    (1239, 1337, "金身(辉月) -> 复活甲(贤者的庇护)"),
    (1337, 1239, "复活甲(贤者的庇护) -> 金身(辉月)"),
    (1239, 1127, "金身(辉月) -> 名刀·司命"),
    (1127, 1239, "名刀·司命 -> 金身(辉月)"),
    (1239, 1328, "金身(辉月) -> 血魔之怒"),
    (1328, 1239, "血魔之怒 -> 金身(辉月)"),
    (1239, 11311, "金身(辉月) -> 纯净苍穹"),
    (11311, 1239, "纯净苍穹 -> 金身(辉月)"),
    (1337, 1127, "复活甲(贤者的庇护) -> 名刀·司命"),
    (1127, 1337, "名刀·司命 -> 复活甲(贤者的庇护)"),
    (1337, 1328, "复活甲(贤者的庇护) -> 血魔之怒"),
    (1328, 1337, "血魔之怒 -> 复活甲(贤者的庇护)"),
    (1337, 11311, "复活甲(贤者的庇护) -> 纯净苍穹"),
    (11311, 1337, "纯净苍穹 -> 复活甲(贤者的庇护)"),
)

# Boots that can be swapped mid-match (冷静鞋 -> 抵抗鞋 and back).
BOOT_SWAP_PAIRS: tuple[tuple[int, int, str], ...] = (
    (1423, 1422, "冷静之靴 -> 抵抗之靴"),
    (1422, 1423, "抵抗之靴 -> 冷静之靴"),
)


class EquipmentCatalogError(RuntimeError):
    """Raised when the local catalog cannot be loaded or is tampered."""


@dataclass(frozen=True)
class CatalogItem:
    item_id: int
    name: str
    item_type: int | None
    price: int | None
    total_price: int | None
    description: str
    passive_active: str
    functions: frozenset[str]
    unique_group: str | None
    max_match_uses: int | None
    cooldown_seconds: int | None
    evidence_source: str


def _plain_text(value: str | None) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", without_tags).strip()


def _detect_max_match_uses(description: str) -> int | None:
    match = re.search(r"每局游戏只能触发(\d+)次", description)
    return int(match.group(1)) if match else None


def _detect_cooldown(description: str) -> int | None:
    match = re.search(r"冷却时间[：:]?\s*(\d+)秒", description)
    return int(match.group(1)) if match else None


def _detect_unique_group(name: str, description: str) -> str | None:
    if any(keyword in name for keyword in ("之靴", "鞋")):
        return "boots"
    if "唯一被动" in description or "唯一主动" in description:
        return "unique"
    return None


def _detect_functions(name: str, description: str, passive_active: str) -> set[str]:
    text = (name + " " + description + " " + passive_active).lower()
    functions: set[str] = set()
    if any(k in text for k in ("韧性", "坚韧")):
        functions.add("tenacity")
    if any(k in text for k in ("法术防御", "魔法防御", "魔抗", "护盾")):
        functions.add("magic_resist")
    if any(k in text for k in ("物理防御", "护甲", "物抗")):
        functions.add("physical_defense")
    if "重伤" in text:
        functions.add("anti_heal")
    if any(k in text for k in ("复活", "复生")):
        functions.add("revive")
    if any(k in text for k in ("免疫", "无敌", "不可选中")):
        functions.add("invincible")
    if "护盾" in text or "月之守护" in text:
        functions.add("shield")
    if any(k in text for k in ("减伤", "免伤", "伤害减免")):
        functions.add("damage_reduction")
    if any(k in text for k in ("冷却缩减", "冷缩", "冷却")):
        functions.add("haste")
    if any(k in text for k in ("物理攻击", "物理伤害")):
        functions.add("physical_damage")
    if any(k in text for k in ("法术攻击", "法术伤害")):
        functions.add("magic_damage")
    if "攻击速度" in text:
        functions.add("attack_speed")
    if "暴击" in text:
        functions.add("crit")
    if "吸血" in text:
        functions.add("life_steal")
    if "移动速度" in text or "移速" in text:
        functions.add("movement_speed")
    if any(k in text for k in ("最大生命", "生命值")):
        functions.add("health")
    return functions


def normalize_item(raw: Mapping[str, Any]) -> CatalogItem:
    name = str(raw.get("item_name") or "")
    description = _plain_text(raw.get("des1"))
    passive_active = _plain_text(raw.get("des2"))
    functions = _detect_functions(name, description, passive_active)
    item_id = int(raw["item_id"])
    return CatalogItem(
        item_id=item_id,
        name=name,
        item_type=int(raw["item_type"]) if raw.get("item_type") is not None else None,
        price=int(raw["price"]) if raw.get("price") is not None else None,
        total_price=int(raw["total_price"]) if raw.get("total_price") is not None else None,
        description=description,
        passive_active=passive_active,
        functions=frozenset(functions & FUNCTION_TAGS),
        unique_group=_detect_unique_group(name, description + " " + passive_active),
        max_match_uses=_detect_max_match_uses(description + " " + passive_active),
        cooldown_seconds=_detect_cooldown(description + " " + passive_active),
        evidence_source=f"{ITEM_CATALOG_URL}#item_{item_id}",
    )


def build_catalog(  # noqa: C901
    items: Sequence[Mapping[str, Any]],
    *,
    source_url: str = ITEM_CATALOG_URL,
    retrieved_at: datetime | None = None,
) -> list[CatalogItem]:
    normalized = [normalize_item(raw) for raw in items]
    # Fix edge cases that pure text parsing cannot infer.
    by_id = {item.item_id: item for item in normalized}

    # 辉月(金身) active is a self-shield/invincibility, not a passive heal.
    if 1239 in by_id:
        item = by_id[1239]
        by_id[1239] = CatalogItem(
            **{**item.__dict__, "functions": item.functions | {"invincible", "shield"}, "unique_group": "unique"},
        )
    # 贤者的庇护 (复活甲) revives at most twice per match.
    if 1337 in by_id:
        item = by_id[1337]
        by_id[1337] = CatalogItem(
            **{**item.__dict__, "functions": item.functions | {"revive"}, "max_match_uses": 2, "unique_group": "unique"},
        )
    # 名刀·司命 gives a short invincibility window when lethal damage would land.
    if 1127 in by_id:
        item = by_id[1127]
        by_id[1127] = CatalogItem(
            **{**item.__dict__, "functions": item.functions | {"invincible"}, "unique_group": "unique"},
        )
    # 血魔之怒 and 纯净苍穹 are emergency actives (shield / damage reduction).
    if 1328 in by_id:
        item = by_id[1328]
        by_id[1328] = CatalogItem(
            **{**item.__dict__, "functions": item.functions | {"shield"}, "unique_group": "unique"},
        )
    if 11311 in by_id:
        item = by_id[11311]
        by_id[11311] = CatalogItem(
            **{**item.__dict__, "functions": item.functions | {"damage_reduction"}, "unique_group": "unique"},
        )
    # 制裁之刃 / 梦魇之牙 are the physical / magical anti-heal items.
    if 11210 in by_id:
        item = by_id[11210]
        by_id[11210] = CatalogItem(
            **{**item.__dict__, "functions": item.functions | {"anti_heal"}, "unique_group": "unique"},
        )
    if 12211 in by_id:
        item = by_id[12211]
        by_id[12211] = CatalogItem(
            **{**item.__dict__, "functions": item.functions | {"anti_heal"}, "unique_group": "unique"},
        )
    return [by_id[item.item_id] for item in normalized]


def load_catalog(path: Path = ITEM_CATALOG_PATH) -> list[CatalogItem]:
    """Load the local raw catalog and verify its content hash."""
    if not path.is_file():
        raise EquipmentCatalogError(f"catalog not found: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("source_url") != ITEM_CATALOG_URL:
        raise EquipmentCatalogError("catalog source_url mismatch")
    items = document.get("items")
    if not isinstance(items, list):
        raise EquipmentCatalogError("catalog items missing")
    payload = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if hashlib.sha256(payload.encode("utf-8")).hexdigest() != document.get("content_hash"):
        raise EquipmentCatalogError("catalog content_hash mismatch")
    return build_catalog(items, source_url=document.get("source_url", ITEM_CATALOG_URL))


def fetch_catalog(*, client: httpx.Client | None = None) -> tuple[list[CatalogItem], str, str]:
    """Fetch the official public catalog and return (items, raw_json, hash)."""
    own_client = client is None
    actual_client = client or httpx.Client(timeout=15, follow_redirects=True)
    try:
        response = actual_client.get(ITEM_CATALOG_URL)
        response.raise_for_status()
        raw = response.text
        items = json.loads(raw)
        payload = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return build_catalog(items), raw, hashlib.sha256(payload.encode("utf-8")).hexdigest()
    finally:
        if own_client:
            actual_client.close()


def catalog_to_dict(item: CatalogItem) -> dict[str, object]:
    return {
        "item_id": item.item_id,
        "item_name": item.name,
        "item_type": item.item_type,
        "price": item.price,
        "total_price": item.total_price,
        "description": item.description,
        "passive_active": item.passive_active,
        "functions": sorted(item.functions),
        "unique_group": item.unique_group,
        "max_match_uses": item.max_match_uses,
        "cooldown_seconds": item.cooldown_seconds,
        "evidence_source": item.evidence_source,
    }


def item_catalog_hash(items: Sequence[CatalogItem]) -> str:
    payload = json.dumps([catalog_to_dict(item) for item in items], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
"""
path = root + r"\backend\app\equipment_catalog.py"
with io.open(path, "w", encoding="utf-8", newline="") as f:
    f.write(content)
print("written", path)
