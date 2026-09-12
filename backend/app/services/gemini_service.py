import json
from dataclasses import dataclass
from google import genai
from google.genai import types


SYSTEM_INSTRUCTION = """You are a patient follow-up assistant used after a medical consultation.
You receive only a known diagnosis, limited relevant consultation context, and this check-in conversation.
You are not a doctor. Ask exactly ONE short question at a time in simple language suitable for an elderly patient.
Adapt to prior answers, do not repeat answered questions, and focus on recovery, relevant symptoms, and whether they are improving or worsening.
Never diagnose, prescribe, recommend changing dose/frequency, tell the patient to start or stop medicine, contradict the treating doctor, fabricate facts, claim the patient is safe, or claim answers were sent to a doctor.
If an answer suggests a serious or urgent problem, clearly direct the patient to appropriate urgent medical help; do not manage it yourself.
Finish after 4-6 useful questions. Return JSON only: {"message": string, "status": "continue"|"complete"}."""


class AssistantUnavailable(Exception):
    pass


@dataclass
class AssistantReply:
    message: str
    status: str


class GeminiService:
    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def next_question(self, diagnosis: str, context: str, messages: list[dict]) -> AssistantReply:
        if not self.api_key:
            raise AssistantUnavailable("Gemini is not configured")
        transcript = "\n".join(f'{m["role"]}: {m["message"]}' for m in messages[-12:])
        prompt = f"Known diagnosis: {diagnosis}\nRelevant context: {context}\nConversation:\n{transcript or '(new check-in)'}"
        client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(
                timeout=12_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        last_error: Exception | None = None
        # Flash Lite is a deterministic service fallback, not a source of any
        # medication or scheduling decision.
        for model in dict.fromkeys((self.model, "gemini-3.5-flash-lite")):
            try:
                response = client.models.generate_content(
                    model=model, contents=prompt,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, response_mime_type="application/json", temperature=0.2),
                )
                data = json.loads(response.text or "")
                if not isinstance(data.get("message"), str) or data.get("status") not in {"continue", "complete"}:
                    raise ValueError("invalid structured response")
                message = data["message"].strip()
                if not message:
                    raise ValueError("empty assistant message")
                return AssistantReply(message=message, status=data["status"])
            except Exception as exc:
                last_error = exc
        raise AssistantUnavailable("Assistant request failed") from last_error
