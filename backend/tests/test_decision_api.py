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
