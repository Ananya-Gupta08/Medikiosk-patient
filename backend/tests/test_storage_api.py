from fastapi.testclient import TestClient
from app.main import app
from app.routes import context
from app.identity import Identity
from app.repositories.mock_medikiosk_repository import MockMedikioskRepository
from app.storage import PwaStore
from app.services.document_extraction_service import DocumentExtractionUnavailable


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


def test_patient_upload_extract_edit_and_download(monkeypatch):
    class Extractor:
        def extract(self, data, mime_type):
            assert data == b"Synthetic medical note"
            assert mime_type == "text/plain"
            return {"title":"Synthetic note","document_date":"2026-09-13","summary":"Patient is improving.","important_points":["Review completed"],"medicines_mentioned":[],"test_results":[],"follow_up_actions":[],"extraction_notice":"AI extracted - patient should verify"}
    ctx = make_context()
    app.dependency_overrides[context] = lambda: ctx
    monkeypatch.setattr("app.routes.document_extractor", lambda: Extractor())
    client = TestClient(app)
    uploaded = client.post("/api/me/uploaded-records", files={"file":("note.txt",b"Synthetic medical note","text/plain")})
    assert uploaded.status_code == 201
    record = uploaded.json()
    assert record["extraction_status"] == "complete"
    edited = client.put(f'/api/me/uploaded-records/{record["id"]}', json={"history":"My corrected summary"})
    assert edited.status_code == 200
    assert edited.json()["patient_summary"] == "My corrected summary"
    downloaded = client.get(f'/api/me/uploaded-records/{record["id"]}/file')
    assert downloaded.content == b"Synthetic medical note"
    assert downloaded.headers["content-disposition"].startswith("attachment;")
    assert client.post("/api/me/uploaded-records", files={"file":("bad.exe",b"x","application/octet-stream")}).status_code == 415
    assert client.post("/api/me/uploaded-records", files={"file":("fake.pdf",b"not a pdf","application/pdf")}).status_code == 400
    app.dependency_overrides.clear()


def test_uploaded_record_is_scoped_to_current_patient(monkeypatch):
    class Extractor:
        def extract(self, data, mime_type):
            return {"title":"Note","summary":"Summary","important_points":[],"medicines_mentioned":[],"test_results":[],"follow_up_actions":[]}
    ctx = make_context()
    app.dependency_overrides[context] = lambda: ctx
    monkeypatch.setattr("app.routes.document_extractor", lambda: Extractor())
    client = TestClient(app)
    record_id = client.post("/api/me/uploaded-records", files={"file":("note.txt",b"Synthetic","text/plain")}).json()["id"]
    other_context = (Identity("OTHER_PATIENT"), ctx[1], ctx[2], ctx[3])
    app.dependency_overrides[context] = lambda: other_context
    assert client.get(f"/api/me/uploaded-records/{record_id}/file").status_code == 404
    assert client.put(f"/api/me/uploaded-records/{record_id}", json={"history":"Changed"}).status_code == 404
    app.dependency_overrides.clear()


def test_upload_survives_extraction_failure(monkeypatch):
    class FailingExtractor:
        def extract(self, data, mime_type): raise DocumentExtractionUnavailable()
    ctx = make_context()
    app.dependency_overrides[context] = lambda: ctx
    monkeypatch.setattr("app.routes.document_extractor", lambda: FailingExtractor())
    response = TestClient(app).post("/api/me/uploaded-records", files={"file":("note.txt",b"Synthetic note","text/plain")})
    assert response.status_code == 201
    assert response.json()["extraction_status"] == "failed"
    app.dependency_overrides.clear()
