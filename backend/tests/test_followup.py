import pytest
from app.repositories.mock_medikiosk_repository import MockMedikioskRepository
from app.services.followup import FollowupService
from app.services.gemini_service import AssistantReply, AssistantUnavailable, GeminiService
from app.storage import PwaStore


class FakeAssistant:
    def __init__(self): self.calls=[]
    def next_question(self, diagnosis, context, messages):
        self.calls.append((diagnosis, messages))
        return AssistantReply("How are you feeling today?" if not messages else "Thank you. Your check-in is complete for today.", "continue" if not messages else "complete")


def test_followup_gets_diagnosis_persists_messages_and_completes():
    store, assistant = PwaStore("sqlite:///:memory:"), FakeAssistant()
    service = FollowupService(MockMedikioskRepository(), store, assistant)
    session, first = service.start("TEST_PATIENT_001")
    assert assistant.calls[0][0] == "Post-operative prostate surgery"
    session, last = service.respond("TEST_PATIENT_001", session["id"], "I feel better")
    assert session["status"] == "complete"
    assert [x["role"] for x in store.messages(session["id"])] == ["assistant", "patient", "assistant"]


def test_cross_patient_session_access_is_blocked():
    store = PwaStore("sqlite:///:memory:")
    session = store.create_session("PATIENT_A", "diagnosis", "visit")
    assert store.session("PATIENT_B", session["id"]) is None


def test_missing_key_is_graceful():
    with pytest.raises(AssistantUnavailable): GeminiService("", "model").next_question("diagnosis", "context", [])


def test_malformed_and_timeout_responses_are_graceful(monkeypatch):
    class Models:
        def generate_content(self, **kwargs): return type("Response",(),{"text":"not json"})()
    class Client:
        def __init__(self, **kwargs): self.models=Models()
    monkeypatch.setattr("app.services.gemini_service.genai.Client", Client)
    with pytest.raises(AssistantUnavailable): GeminiService("key", "model").next_question("diagnosis", "context", [])
    class TimeoutModels:
        def generate_content(self, **kwargs): raise TimeoutError()
    class TimeoutClient:
        def __init__(self, **kwargs): self.models=TimeoutModels()
    monkeypatch.setattr("app.services.gemini_service.genai.Client", TimeoutClient)
    with pytest.raises(AssistantUnavailable): GeminiService("key", "model").next_question("diagnosis", "context", [])

