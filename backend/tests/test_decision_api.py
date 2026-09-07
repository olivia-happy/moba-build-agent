from fastapi.testclient import TestClient

from app.main import app


def test_player_confirmed_decision_returns_traceable_purchase_advice():
    response = TestClient(app).post(
        "/api/decisions",
        json={
            "gold": 400,
            "enemy_hero_ids": [101],
            "owned_item_ids": [],
            "input_source": "player_confirmed_screen",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "local_rules"
    assert body["recommendations"][0]["evidence"]
    assert body["recommendations"][0]["purchase_status"] == "buy_component"
    assert body["unknown_hero_ids"] == []


def test_decision_endpoint_rejects_unconfirmed_automatic_capture():
    response = TestClient(app).post(
        "/api/decisions",
        json={
            "gold": 400,
            "enemy_hero_ids": [101],
            "owned_item_ids": [],
            "input_source": "automatic_capture",
        },
    )

    assert response.status_code == 422
    assert "player-confirmed" in response.json()["detail"]


def test_decision_endpoint_returns_own_hero_context_and_adjustment():
    response = TestClient(app).post(
        "/api/decisions",
        json={
            "gold": 2_200,
            "enemy_hero_ids": [142],
            "own_hero_id": 169,
            "owned_item_ids": [],
            "input_source": "player_confirmed_screen",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["own_hero"] == {
        "hero_id": 169,
        "name": "后羿",
        "hero_type": 5,
        "role_label": "射手",
    }
    assert body["own_hero_adjustments"][0]["code"] == "fragile_survival"
    assert "survival" in body["priority_needs"]


def test_decision_endpoint_rejects_unknown_own_hero():
    response = TestClient(app).post(
        "/api/decisions",
        json={
            "gold": 400,
            "enemy_hero_ids": [101],
            "own_hero_id": 999999,
            "owned_item_ids": [],
            "input_source": "player_confirmed_screen",
        },
    )

    assert response.status_code == 422
    assert "own hero" in response.json()["detail"]
