from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server


def setup_function() -> None:
    server._games.clear()


def test_new_game_and_move_with_coordinates() -> None:
    client = TestClient(server.app)
    response = client.post("/api/new")
    assert response.status_code == 200
    state = response.json()

    assert state["turn"] == "white"
    assert state["legal_moves"]

    _, moves = next(iter(state["legal_moves"].items()))
    move_data = moves[0]

    payload = {
        "game_id": state["game_id"],
        "source": move_data["source"],
        "target": move_data["to"],
    }
    if move_data.get("promotion"):
        payload["promotion"] = move_data["promotion"]

    response = client.post("/api/move", json=payload)
    assert response.status_code == 200
    updated = response.json()

    assert updated["history"][0]["white"]
    assert updated["turn"] in {"white", "black"}


def test_illegal_move_rejected() -> None:
    client = TestClient(server.app)
    state = client.post("/api/new").json()

    response = client.post(
        "/api/move",
        json={
            "game_id": state["game_id"],
            "source": "a2",
            "target": "a5",
        },
    )
    assert response.status_code == 400
    assert "Illegal move" in response.json()["detail"]
