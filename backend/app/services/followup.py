from app.repositories.base import MedikioskRepository
from app.services.gemini_service import AssistantUnavailable
from app.storage import PwaStore


class FollowupService:
    def __init__(self, repository: MedikioskRepository, store: PwaStore, assistant):
        self.repository, self.store, self.assistant = repository, store, assistant

    def start(self, patient_id: str) -> tuple[dict, dict]:
        consultation = self.repository.get_latest_consultation(patient_id)
        if not consultation:
            raise ValueError("No consultation is available")
        session = self.store.create_session(patient_id, consultation.diagnosis, consultation.id)
        reply = self.assistant.next_question(consultation.diagnosis, "Post-consultation recovery check-in", [])
        message = self.store.add_message(session["id"], "assistant", reply.message)
        if reply.status == "complete": self.store.complete_session(session["id"])
        return self.store.session(patient_id, session["id"]), message

    def respond(self, patient_id: str, session_id: str, answer: str) -> tuple[dict, dict]:
        session = self.store.session(patient_id, session_id)
        if not session:
            raise LookupError("Session not found")
        if session["status"] == "complete":
            raise ValueError("This check-in is complete")
        self.store.add_message(session_id, "patient", answer)
        messages = self.store.messages(session_id)
        reply = self.assistant.next_question(session["diagnosis_value"], "Post-consultation recovery check-in", messages)
        message = self.store.add_message(session_id, "assistant", reply.message)
        if reply.status == "complete": self.store.complete_session(session_id)
        return self.store.session(patient_id, session_id), message
