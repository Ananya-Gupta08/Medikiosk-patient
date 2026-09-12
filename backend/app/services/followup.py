from app.repositories.base import MedikioskRepository
from app.services.gemini_service import AssistantUnavailable
from app.storage import PwaStore

RECOVERY_QUESTION = "Have you recovered from the health problem discussed at your last appointment? Please answer yes or no."
RECOVERY_CLARIFICATION = "Please tell me whether you have recovered from your last appointment by answering yes or no."


def recovery_answer(answer: str) -> bool | None:
    value = answer.strip().lower()
    negative = ("no", "not yet", "not recovered", "still unwell", "still sick", "haven't", "have not")
    positive = ("yes", "recovered", "i have", "feeling well", "feel well")
    if any(term in value for term in negative):
        return False
    if any(term in value for term in positive):
        return True
    return None


class FollowupService:
    def __init__(self, repository: MedikioskRepository, store: PwaStore, assistant):
        self.repository, self.store, self.assistant = repository, store, assistant

    def start(self, patient_id: str) -> tuple[dict, dict]:
        consultation = self.repository.get_latest_consultation(patient_id)
        if not consultation:
            raise ValueError("No consultation is available")
        session = self.store.create_session(patient_id, consultation.diagnosis, consultation.id)
        reply = self.assistant.next_question(consultation.diagnosis, "Post-consultation recovery check-in", [])
        urgent = reply.status == "complete" and any(term in reply.message.lower() for term in ("urgent", "emergency", "seek medical help", "contact your healthcare professional promptly"))
        first_message = reply.message if urgent or reply.status != "complete" else RECOVERY_QUESTION
        message = self.store.add_message(session["id"], "assistant", first_message)
        if urgent:
            self.store.complete_session(session["id"])
        return self.store.session(patient_id, session["id"]), message

    def respond(self, patient_id: str, session_id: str, answer: str) -> tuple[dict, dict]:
        session = self.store.session(patient_id, session_id)
        if not session:
            raise LookupError("Session not found")
        if session["status"] == "complete":
            raise ValueError("This check-in is complete")
        existing_messages = self.store.messages(session_id)
        awaiting_recovery = bool(existing_messages and existing_messages[-1]["role"] == "assistant" and existing_messages[-1]["message"] in {RECOVERY_QUESTION, RECOVERY_CLARIFICATION})
        self.store.add_message(session_id, "patient", answer)
        if awaiting_recovery:
            recovered = recovery_answer(answer)
            if recovered is None:
                message = self.store.add_message(session_id, "assistant", RECOVERY_CLARIFICATION)
                return self.store.session(patient_id, session_id), message
            if recovered:
                text = "Thank you. Your recovery check-in is complete."
            else:
                self.store.create_appointment_request(patient_id, session["consultation_reference"], "Patient reported they have not recovered")
                text = "An appointment request has been created. The hospital still needs to confirm the date and time."
            message = self.store.add_message(session_id, "assistant", text)
            self.store.complete_session(session_id)
            return self.store.session(patient_id, session_id), message
        messages = self.store.messages(session_id)
        reply = self.assistant.next_question(session["diagnosis_value"], "Post-consultation recovery check-in", messages)
        urgent = reply.status == "complete" and any(term in reply.message.lower() for term in ("urgent", "emergency", "seek medical help", "contact your healthcare professional promptly"))
        next_message = reply.message if urgent or reply.status != "complete" else RECOVERY_QUESTION
        message = self.store.add_message(session_id, "assistant", next_message)
        if urgent:
            self.store.complete_session(session_id)
        return self.store.session(patient_id, session_id), message
