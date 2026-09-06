"""Generate offline demo snapshots for h5-demo.

Runs the real FastAPI endpoints (via TestClient) for every preset scenario and
writes the exact JSON the h5 demo would receive into
h5-demo/src/offline-snapshots.json so the static build keeps working without
a running backend. Snapshots are engine output, not fabricated data.

Usage (repo root):
    .venv/Scripts/python.exe backend/scripts/generate_h5_offline_snapshots.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

# Same canonical request params as h5-demo/src/scenarios.js
SCENARIOS = {
    "magic-burst": {
        "enemy": [142, 152, 156, 141, 109],
        "own_team": [169, 133, 107, 118, 105],
        "gold": 2140, "owned": [1411, 1313],
        "revive": 0, "slots": 6, "tenacity": True,
    },
    "assassin-dive": {
        "enemy": [153, 167, 107, 144, 133],
        "own_team": [112, 106, 167, 105, 118],
        "gold": 2860, "owned": [1411, 1333, 1113],
        "revive": 1, "slots": 6, "tenacity": False,
    },
    "sustain-control": {
        "enemy": [144, 118, 184, 156, 108],
        "own_team": [105, 107, 142, 112, 184],
        "gold": 1650, "owned": [1411, 1325],
        "revive": 0, "slots": 6, "tenacity": True,
    },
}

INDEX_PATH = ROOT / "h5-demo" / "public" / "portrait_index.json"
index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
by_hero = {e["hero_id"]: e for e in index["entries"]}


def analyze_payload(enemy_ids):
    slots = [
        {"slot_index": i, "grid": by_hero[hid]["grid"]}
        for i, hid in enumerate(enemy_ids)
    ]
    return {
        "input_source": "player_tapped_capture",
        "layout_version": "draft-layout-1080x2400-v1",
        "slots": slots,
    }


def decision_payload(s, own_hero_id, enemy_ids):
    return {
        "input_source": "player_confirmed_screen",
        "enemy_hero_ids": enemy_ids,
        "own_hero_id": own_hero_id,
        "gold": s["gold"],
        "owned_item_ids": s["owned"],
        "revive_uses_used": s["revive"],
        "slot_capacity": s["slots"],
        "needs_tenacity": s["tenacity"],
    }


client = TestClient(app)
out = {"schema_version": 1, "scenarios": {}}

for sid, s in SCENARIOS.items():
    # 1) analyze for the captured enemy frame (identical grids -> true heroes on top)
    an = client.post("/api/frames/analyze", json=analyze_payload(s["enemy"]))
    an.raise_for_status()
    analyze = an.json()
    top1 = [slot["candidates"][0]["hero_id"] for slot in analyze["slots"]]
    assert top1 == s["enemy"], f"{sid}: analyze top-1 != scenario enemies {top1}"

    # 2) decisions per selectable own-team hero
    decisions = {}
    for own in s["own_team"]:
        resp = client.post("/api/decisions", json=decision_payload(s, own, s["enemy"]))
        resp.raise_for_status()
        decisions[str(own)] = resp.json()

    out["scenarios"][sid] = {"analyze": analyze, "decisions": decisions}
    print(f"{sid}: analyze ok, decisions for {sorted(decisions)}")

dest = ROOT / "h5-demo" / "src" / "offline-snapshots.json"
dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"wrote {dest} ({dest.stat().st_size / 1024:.0f} KB)")
