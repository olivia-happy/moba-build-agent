
"""Local-first in-match build assistant API.

Every endpoint is offline and deterministic: no API key, no paid model, no
cloud cost. The "AI" here is an explicit, evidence-bearing rule engine that
composes hero mechanics -> threat needs -> item functions -> economy
constraints into traceable advice. The player always confirms a frame-derived
state before the service returns any build recommendation.

Privacy contract: the Android overlay crops the five enemy portraits and
downsamples each to a 16x16 luminance grid on-device. Only those tiny grids
(256 integers each) are sent to the user's own local FastAPI process; the full
frame never leaves the phone.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.decision_agent import BuildDecisionInput, decide_next_purchase
from app.equipment_catalog import EquipmentRule, build_equipment_rules, load_catalog
from app.emergency_swap import EmergencySwapAdvice, recommend_emergency_swap
from app.frame_analysis import MatchCandidate, rank_candidates
from app.hero_profiles import build_threat_profiles, load_hero_catalog
from app.lineup_threats import HeroThreatProfile
from app.match_state import Component, ItemRule, MatchState
from app.portrait_index import PortraitIndex, PORTRAIT_GRID_SIZE, load_index

INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "portrait_index.json"


def _load_index() -> PortraitIndex | None:
    try:
        return load_index(INDEX_PATH)
    except Exception:
        return None


def _threat_profiles() -> dict[int, HeroThreatProfile]:
    """Explicit, maintainable hero-mechanic tags (source: official hero catalog).

    Names and ids come from the bundled catalog; threat tags are reviewed in
    hero_profiles.py. Unknown heroes are disclosed instead of guessed.
    """
    return build_threat_profiles(load_hero_catalog())


def _item_rules() -> list[ItemRule]:
    """Versioned item rules with components, uniqueness, and per-match limits.

    Prices/functions come from the official item catalog; overrides keep any
    known component paths. Kept as ItemRule so the decision agent and existing
    tests remain source-compatible.
    """
    catalog = load_catalog()
    rules: list[ItemRule] = []
    for rule in build_equipment_rules(catalog):
        rules.append(
            ItemRule(
                item_id=rule.item_id,
                name=rule.name,
                price=rule.total_price,
                functions=rule.functions,
                evidence=rule.evidence,
                components=[
                    Component(item_id=component.item_id, name=component.name, price=component.price)
                    for component in _components_for(rule.item_id)
                ],
                unique_group=rule.unique_group,
                max_match_uses=rule.max_match_uses,
                cooldown_seconds=rule.cooldown_seconds,
            )
        )
    return rules


_COMPONENT_PATHS: dict[int, list[Component]] = {
    1422: [Component(1405, "神速之靴", 250)],
    1423: [Component(1405, "神速之靴", 250)],
    1335: [Component(1323, "神隐斗篷", 800)],
    1347: [Component(1323, "神隐斗篷", 800)],
    1336: [Component(1324, "雪山圆盾", 750), Component(1321, "力量腰带", 850)],
    1327: [Component(1312, "布甲", 275), Component(1321, "力量腰带", 850)],
    1333: [Component(1325, "守护者之铠", 800)],
    1338: [Component(1325, "守护者之铠", 800), Component(1121, "风暴巨剑", 850)],
    1341: [Component(1325, "守护者之铠", 800), Component(1321, "力量腰带", 850)],
    11210: [Component(1121, "风暴巨剑", 850), Component(1114, "吸血之镰", 300)],
    12211: [Component(1116, "雷鸣刃", 820), Component(1313, "抗魔披风", 275)],
    1239: [Component(1116, "雷鸣刃", 820), Component(1113, "搏击拳套", 300)],
    1337: [Component(1321, "力量腰带", 850), Component(1313, "抗魔披风", 275), Component(1311, "红玛瑙", 300)],
    1127: [Component(1121, "风暴巨剑", 850), Component(1311, "红玛瑙", 300)],
    1328: [Component(1321, "力量腰带", 850), Component(1313, "抗魔披风", 275), Component(1114, "吸血之镰", 300)],
    11311: [Component(1121, "风暴巨剑", 850), Component(1313, "抗魔披风", 275), Component(1311, "红玛瑙", 300)],
}


def _components_for(item_id: int) -> list[Component]:
    return _COMPONENT_PATHS.get(item_id, [])


def _item_function_names(functions: set[str]) -> dict[str, str]:
    mapping = {
        "anti_heal": "减疗（降低敌方回血/吸血）",
        "magic_resist": "法术防御",
        "tenacity": "韧性（缩短被控时间）",
        "physical_defense": "物理防御",
        "anti_sustain": "对抗续航",
        "physical_burst": "物理爆发",
        "magic_burst": "法术爆发",
        "survival": "生存保命",
        "invulnerability": "金身无敌",
        "revive": "复活",
        "death_avoid": "免死",
        "shield": "护盾",
        "damage_reduction": "减伤",
        "boots": "鞋子",
        "haste": "冷却缩减",
        "magic_shield": "法术护盾",
        "sustain": "续航",
        "reflect": "反伤",
        "anti_attack_speed": "降低攻速",
        "slow": "减速",
        "engage": "开团",
        "damage": "增伤",
        "speed": "移速",
        "physical_attack": "物理攻击",
        "attack_speed": "攻速",
        "crit": "暴击",
        "health": "生命值",
        "mana": "法力",
        "mobility": "机动",
        "crowd_control": "控制",
        "healing": "回复",
        "physical_sustain": "物理续航",
        "true_damage": "真实伤害",
        "movement_speed": "移速增益",
    }
    return {name: mapping.get(name, name) for name in sorted(functions)}


def _equipment_rule_to_dict(rule: EquipmentRule) -> dict[str, object]:
    return {
        "item_id": rule.item_id,
        "name": rule.name,
        "price": rule.price,
        "total_price": rule.total_price,
        "item_type": rule.item_type,
        "functions": sorted(rule.functions),
        "function_labels": _item_function_names(rule.functions),
        "description": rule.description,
        "evidence": rule.evidence,
        "source_url": rule.source_url,
        "unique_group": rule.unique_group,
        "max_match_uses": rule.max_match_uses,
        "cooldown_seconds": rule.cooldown_seconds,
    }


def _emergency_swap_to_dict(advice: EmergencySwapAdvice) -> dict[str, object]:
    return {
        "suggestions": [
            {
                "action": s.action,
                "target_item_id": s.target_item_id,
                "target_item_name": s.target_item_name,
                "cost": s.cost,
                "reason": s.reason,
                "why_now": s.why_now,
                "evidence": s.evidence,
                "constraints": s.constraints,
                "replace_item_id": s.replace_item_id,
            }
            for s in advice.suggestions
        ],
        "remaining_gold": advice.remaining_gold,
        "inventory_slots_free": advice.inventory_slots_free,
        "revive_uses_remaining": advice.revive_uses_remaining,
        "warnings": advice.warnings,
    }


app = FastAPI(
    title="局内出装助手 API",
    description="本地优先、零 API 成本的王者荣耀局内出装决策服务。",
    version="0.3.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "ai_mode": "offline"}


@app.get("/api/catalog/items")
def list_catalog_items() -> dict[str, object]:
    """List the official item catalog with explicit rules and provenance."""
    catalog = load_catalog()
    rules = build_equipment_rules(catalog)
    return {
        "source_url": "https://pvp.qq.com/web201605/js/item.json",
        "item_count": len(rules),
        "items": [_equipment_rule_to_dict(rule) for rule in rules],
    }


@app.get("/api/catalog/items/{item_id}")
def get_catalog_item(item_id: int) -> dict[str, object]:
    """Return one catalog item with rules; 404 when unknown."""
    catalog = load_catalog()
    rules = {rule.item_id: rule for rule in build_equipment_rules(catalog)}
    rule = rules.get(item_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"item {item_id} not found")
    return _equipment_rule_to_dict(rule)


@app.get("/api/catalog/portrait-index")
def portrait_index_meta() -> dict[str, object]:
    """Expose the bundled portrait index provenance without dumping grids."""
    index = _load_index()
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="portrait index is not available; run backend/scripts/build_portrait_index.py",
        )
    return {
        "schema_version": index.schema_version,
        "grid_size": index.grid_size,
        "hero_count": index.hero_count,
        "content_hash": index.content_hash,
        "fetched_at": index.fetched_at.isoformat(),
        "source_hero_list": index.source_hero_list,
    }


@app.post("/api/frames/analyze")
def analyze_captured_frame(payload: dict[str, object]) -> dict[str, object]:
    """Rank on-device portrait grids against the versioned index.

    Request body (player-initiated only):
      input_source: "player_tapped_capture"
      layout_version: "draft-layout-1080x2400-v1"
      slots: [{ "slot_index": 0, "grid": [256 luminance values] }, ...]

    The client sends only downsampled 16x16 luminance grids; the full frame
    stays on the device. The response returns Top-3 candidates per slot with
    confidence and the index hash so the advice chain is reproducible.
    """
    if payload.get("input_source") != "player_tapped_capture":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Frame analysis requires a player-initiated capture trigger.",
        )
    if payload.get("layout_version") != "draft-layout-1080x2400-v1":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported layout_version.",
        )
    raw_slots = payload.get("slots")
    if not isinstance(raw_slots, list) or not raw_slots:
        raise HTTPException(status_code=422, detail="slots is required.")

    index = _load_index()
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="portrait index is not available; run backend/scripts/build_portrait_index.py",
        )

    slots_out = []
    for raw_slot in raw_slots:
        if not isinstance(raw_slot, dict):
            raise HTTPException(status_code=422, detail="each slot must be an object")
        slot_index = raw_slot.get("slot_index")
        grid = raw_slot.get("grid")
        if not isinstance(slot_index, int) or not isinstance(grid, list):
            raise HTTPException(status_code=422, detail="slot_index:int and grid:list are required")
        if len(grid) != PORTRAIT_GRID_SIZE * PORTRAIT_GRID_SIZE:
            raise HTTPException(
                status_code=422,
                detail=f"grid must have {PORTRAIT_GRID_SIZE * PORTRAIT_GRID_SIZE} values, got {len(grid)}",
            )
        try:
            candidates: list[MatchCandidate] = rank_candidates(grid, index.entries)
        except Exception as exc:  # noqa: BLE001 - convert to client error
            raise HTTPException(status_code=422, detail=f"invalid grid: {exc}") from exc
        slots_out.append(
            {
                "slot_index": slot_index,
                "candidates": [
                    {
                        "hero_id": candidate.hero_id,
                        "hero_name": candidate.hero_name,
                        "confidence": candidate.confidence,
                    }
                    for candidate in candidates
                ],
            }
        )

    return {
        "input_source": "player_tapped_capture",
        "layout_version": "draft-layout-1080x2400-v1",
        "index_hash": index.content_hash,
        "slots": slots_out,
    }


@app.post("/api/decisions", status_code=status.HTTP_200_OK)
def create_player_confirmed_decision(payload: dict[str, object]) -> dict[str, object]:
    """Return build advice only for player-confirmed, evidence-traceable input.

    New in 0.3.0:
      - owned_item_ids may include real catalog ids (e.g. 1239 辉月, 1337 复活甲)
      - revive_uses_used / slot_capacity / needs_tenacity feed the emergency
        swap engine (金身/复活甲/名刀/血魔/苍穹, 冷静鞋->抵抗鞋)
      - every recommendation now carries function_explanation, item_price,
        component_path and why_now alongside the existing evidence.
    """
    if payload.get("input_source") != "player_confirmed_screen":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Screen-derived state must be player-confirmed before recommendation.",
        )

    gold = int(payload.get("gold", 0))
    enemy_hero_ids = [int(hero_id) for hero_id in payload.get("enemy_hero_ids", [])]
    owned_item_ids = {int(item_id) for item_id in payload.get("owned_item_ids", [])}
    revive_uses_used = int(payload.get("revive_uses_used", 0))
    slot_capacity = int(payload.get("slot_capacity", 6))
    needs_tenacity = bool(payload.get("needs_tenacity", False))

    profiles = _threat_profiles()
    item_rules = _item_rules()
    decision = decide_next_purchase(
        BuildDecisionInput(
            enemy_hero_ids=enemy_hero_ids,
            profiles=profiles,
            match_state=MatchState(gold=gold, owned_item_ids=owned_item_ids),
            item_rules=item_rules,
        )
    )
    rule_by_id = {rule.item_id: rule for rule in item_rules}
    component_paths: dict[int, list[dict[str, object]]] = {}
    for rule in item_rules:
        component_paths[rule.item_id] = [
            {"item_id": component.item_id, "name": component.name, "price": component.price}
            for component in rule.components
        ]
    catalog = load_catalog()

    emergency_advice = recommend_emergency_swap(
        gold=gold,
        owned_item_ids=sorted(owned_item_ids),
        rules=build_equipment_rules(catalog),
        revive_uses_used=revive_uses_used,
        needs_tenacity=needs_tenacity or "tenacity" in decision.priority_needs,
        slot_capacity=slot_capacity,
    )

    recommendations = []
    for rec in decision.recommendations:
        rule = rule_by_id.get(rec.item_id)
        recommendations.append(
            {
                "item_id": rec.item_id,
                "item_name": rec.item_name,
                "covered_needs": rec.covered_needs,
                "purchase_status": rec.purchase_status,
                "next_item_id": rec.next_item_id,
                "next_item_name": rec.next_item_name,
                "replace_item_id": rec.replace_item_id,
                "evidence": rec.evidence,
                "function_explanation": _item_function_names(rule.functions) if rule else {},
                "item_price": rule.price if rule else None,
                "component_path": component_paths.get(rec.item_id, []),
                "why_now": rule.evidence if rule else rec.evidence,
            }
        )

    return {
        "input_source": "player_confirmed_screen",
        "mode": "local_rules",
        "priority_needs": decision.priority_needs,
        "threat_counts": decision.threat_counts,
        "unknown_hero_ids": decision.unknown_hero_ids,
        "recommendations": recommendations,
        "emergency_swap": _emergency_swap_to_dict(emergency_advice),
        "catalog_provenance": {
            "item_source_url": "https://pvp.qq.com/web201605/js/item.json",
            "hero_source_url": "https://pvp.qq.com/web201605/js/herolist.json",
        },
    }
