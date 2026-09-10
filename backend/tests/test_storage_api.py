from fastapi.testclient import TestClient
from app.main import app
from app.routes import context
from app.identity import Identity
from app.repositories.mock_medikiosk_repository import MockMedikioskRepository
from app.storage import PwaStore


def make_context():
    repo, owned = MockMedikioskRepository(), PwaStore("sqlite:///:memory:")
    patient = repo.get_patient("TEST_PATIENT_001")
    return (Identity(patient.id), patient, repo, owned)


def test_dashboard_medications_taken_idempotent_and_calendar_updates():
    ctx = make_context()
    app.dependency_overrides[context] = lambda: ctx
    client = TestClient(app)
    dashboard = client.get("/api/me/dashboard?day=2026-09-10")
    assert dashboard.status_code == 200
    assert dashboard.json()["patient"]["name"] == "Ramesh Kumar"
    assert len(dashboard.json()["medications"]) == 4
    occurrence_id = dashboard.json()["medications"][0]["id"]
    first = client.post(f"/api/me/medication-schedules/{occurrence_id}/taken")
    second = client.post(f"/api/me/medication-schedules/{occurrence_id}/taken")
    assert first.status_code == second.status_code == 200
    assert first.json()["completed_at"] == second.json()["completed_at"]
    calendar = client.get("/api/me/calendar?start=2026-09-10&end=2026-09-10").json()
    assert next(x for x in calendar["medications"] if x["id"] == occurrence_id)["status"] == "taken"
    app.dependency_overrides.clear()


def test_unknown_occurrence_is_not_writable():
    app.dependency_overrides[context] = make_context
    assert TestClient(app).post("/api/me/medication-schedules/not-real/taken").status_code == 404
    app.dependency_overrides.clear()


def test_mock_identity_blocks_switching_patient_header():
    client = TestClient(app)
    assert client.get("/api/me/dashboard", headers={"X-Mock-Patient-ID":"OTHER"}).status_code == 403

