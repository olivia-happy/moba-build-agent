"""Versioned public game catalog used as evidence by the recommendation Agent."""

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import html
import json
import re
from typing import Any, Sequence


@dataclass(frozen=True)
class CatalogItem:
    item_id: int
    name: str
    item_type: int | None
    price: int | None
    total_price: int | None
    description: str


@dataclass(frozen=True)
class CatalogHero:
    hero_id: int
    name: str
    hero_type: int | None
    roles: list[str]


@dataclass(frozen=True)
class CatalogSnapshot:
    source: str
    retrieved_at: datetime
    content_hash: str
    hero_count: int
    item_count: int
    heroes: list[CatalogHero]
    items: list[CatalogItem]


def _plain_text(value: str | None) -> str:
    without_tags = re.sub(r"<[^>]+>", "", value or "")
    return html.unescape(without_tags).strip()


def build_catalog_snapshot(
    *, heroes: Sequence[dict[str, Any]], items: Sequence[dict[str, Any]], retrieved_at: datetime
) -> CatalogSnapshot:
    normalized_heroes = [
        CatalogHero(
            hero_id=int(hero["ename"]),
            name=str(hero["cname"]),
            hero_type=int(hero["hero_type"]) if hero.get("hero_type") is not None else None,
            roles=[role for role in str(hero.get("roles") or "").split("|") if role],
        )
        for hero in heroes
        if hero.get("ename") is not None and hero.get("cname")
    ]
    normalized_items = [
        CatalogItem(
            item_id=int(item["item_id"]),
            name=str(item["item_name"]),
            item_type=int(item["item_type"]) if item.get("item_type") is not None else None,
            price=int(item["price"]) if item.get("price") is not None else None,
            total_price=int(item["total_price"]) if item.get("total_price") is not None else None,
            description=_plain_text(str(item.get("des1") or "")),
        )
        for item in items
        if item.get("item_id") is not None and item.get("item_name")
    ]
    payload = json.dumps(
        {"heroes": [asdict(hero) for hero in normalized_heroes], "items": [asdict(item) for item in normalized_items]},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return CatalogSnapshot(
        source="pvp.qq.com",
        retrieved_at=retrieved_at,
        content_hash=sha256(payload.encode("utf-8")).hexdigest(),
        hero_count=len(normalized_heroes),
        item_count=len(normalized_items),
        heroes=normalized_heroes,
        items=normalized_items,
    )
