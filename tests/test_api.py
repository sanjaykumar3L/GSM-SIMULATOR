"""Independent API smoke tests for the custom dashboard and synthetic experiments."""
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_root_and_health():
    home = client.get("/")
    assert home.status_code == 200
    assert "SIGNALCORE" in home.text
    assert "Authorization" not in home.text
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_overview_is_synthetic():
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["tower_count"] == 4
    assert data["controller_count"] == 2
    assert data["mode"] == "SYNTHETIC LAB"


def test_authenticated_and_rejected_cases():
    good = client.post("/api/authenticate", json={"scenario": "valid"})
    bad = client.post("/api/authenticate", json={"scenario": "invalid"})
    assert good.status_code == 200
    assert bad.status_code == 200
    assert good.json()["accepted"] is True
    assert len(good.json()["rand"]) == 32
    assert bad.json()["accepted"] is False
    assert bad.json()["kc"] is None


def test_cipher_round_trip():
    response = client.post("/api/encryption", json={"message": "Secret capstone demo"})
    assert response.status_code == 200
    data = response.json()
    assert data["recovered"] == "Secret capstone demo"
    assert data["ciphertext"] != "Secret capstone demo"
    assert "not GSM A5" in data["algorithm"]


def test_noise_free_localization_and_error_checks():
    response = client.post("/api/localization", json={
        "x": 500, "y": 800, "noise_db": 0, "seed": 42
    })
    assert response.status_code == 200
    data = response.json()
    assert data["trilateration"]["error_m"] < 0.01
    assert len(data["measurements"]) == 4
    wrong = client.post("/api/localization", json={"noise_db": -7})
    assert wrong.status_code == 422


def test_handover_success_and_deadzone_failure():
    success = client.post("/api/handover", json={"noise_db": 0})
    assert success.status_code == 200
    events = [r["event"] for r in success.json()["events"]]
    assert "INTRA-BSC" in events
    assert "INTER-BSC" in events
    dropped = client.post("/api/handover", json={"noise_db": 0, "coverage_hole": True})
    assert dropped.status_code == 200
    assert dropped.json()["metrics"]["call_dropped"] is True


def test_seeded_experiments():
    config = {"trials": 5, "noise_db": 2.0, "seed": 123}
    first = client.post("/api/experiments", json=config)
    second = client.post("/api/experiments", json=config)
    assert first.status_code == 200
    assert first.json() == second.json()
    assert len(first.json()["localization"]) == 5
    assert len(first.json()["handover"]) == 5
