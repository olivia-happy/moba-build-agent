from fastapi.testclient import TestClient

from app.main import app
from app.portrait_index import PORTRAIT_GRID_SIZE


def _grid_matching_hero(hero_id: int) -> list[int]:
    # A flat grid that exactly matches the first reference entry's grid, so
    # the endpoint returns it as the top candidate with confidence 1.0.
    from app.main import _load_index

    index = _load_index()
    if index is None:
        raise AssertionError("portrait index missing; run build script first")
    for entry in index.entries:
        if entry.hero_id == hero_id:
            return list(entry.grid)
    raise AssertionError(f"hero {hero_id} not in index")


def test_frame_analyze_requires_player_tapped_input_source():
    response = TestClient(app).post(
        "/api/frames/analyze",
        json={
            "input_source": "automatic_capture",
            "layout_version": "draft-layout-1080x2400-v1",
            "slots": [{"slot_index": 0, "grid": [0] * (PORTRAIT_GRID_SIZE * PORTRAIT_GRID_SIZE)}],
        },
    )

    assert response.status_code == 422


def test_frame_analyze_rejects_unsupported_layout():
    response = TestClient(app).post(
        "/api/frames/analyze",
        json={
            "input_source": "player_tapped_capture",
            "layout_version": "old-layout",
            "slots": [{"slot_index": 0, "grid": [0] * (PORTRAIT_GRID_SIZE * PORTRAIT_GRID_SIZE)}],
        },
    )

    assert response.status_code == 422


def test_frame_analyze_returns_top_candidate_with_index_hash():
    grid = _grid_matching_hero(105)
    response = TestClient(app).post(
        "/api/frames/analyze",
        json={
            "input_source": "player_tapped_capture",
            "layout_version": "draft-layout-1080x2400-v1",
            "slots": [{"slot_index": 0, "grid": grid}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["index_hash"]
    assert body["slots"][0]["slot_index"] == 0
    assert body["slots"][0]["candidates"][0]["hero_id"] == 105
    assert body["slots"][0]["candidates"][0]["confidence"] == 1.0
    assert len(body["slots"][0]["candidates"]) == 3
