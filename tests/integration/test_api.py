import os

os.environ["BATTERYMIND_PROCESSED_DATA_DIR"] = "data/processed"
os.environ["BATTERYMIND_DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_battery_analysis_is_real_and_cutoff_aware():
    response = client.get("/api/v1/batteries/B0005/analysis?cutoff=10")
    assert response.status_code == 200
    body = response.json()
    assert body["battery_id"] == "B0005"
    assert body["cutoff_cycle"] == 10
    assert len(body["measurements"]) == 10
    assert body["provenance"]["measurement_kind"] == "laboratory_experiment"


def test_unknown_battery_is_404():
    assert client.get("/api/v1/batteries/B9999/analysis").status_code == 404


def test_memory_requires_authentication():
    response = client.post("/api/v1/sessions", json={"battery_id": "B0005", "objective": "Review degradation"})
    assert response.status_code == 401
