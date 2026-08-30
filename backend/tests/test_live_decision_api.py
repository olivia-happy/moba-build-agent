from fastapi.testclient import TestClient

from app.main import app


def test_live_decision_accepts_player_confirmed_screen_state():
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
    assert body["input_source"] == "player_confirmed_screen"
    assert body["recommendations"][0]["purchase_status"] == "buy_component"


def test_live_decision_rejects_unconfirmed_automatic_capture():
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
