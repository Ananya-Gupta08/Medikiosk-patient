import json
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class DocumentExtractionUnavailable(Exception):
    pass


class ExtractedDocument(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    document_date: str | None = Field(default=None, max_length=20)
    summary: str = Field(min_length=1, max_length=3000)
    important_points: list[str] = Field(default_factory=list, max_length=12)
    medicines_mentioned: list[str] = Field(default_factory=list, max_length=12)
    test_results: list[str] = Field(default_factory=list, max_length=12)
    follow_up_actions: list[str] = Field(default_factory=list, max_length=8)
    extraction_notice: Literal["AI extracted - patient should verify"] = "AI extracted - patient should verify"


INSTRUCTION = """Extract important information from this patient-uploaded medical record.
Copy facts from the document only. Do not diagnose, infer a condition, prescribe, or recommend changing medicine.
Use short, simple language. Omit information that is not visible or is uncertain rather than guessing.
Return JSON with: title, document_date (YYYY-MM-DD or null), summary, important_points,
medicines_mentioned, test_results, follow_up_actions. Each list must contain short strings."""


class DocumentExtractionService:
    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def extract(self, data: bytes, mime_type: str) -> dict:
        if not self.api_key:
            raise DocumentExtractionUnavailable("Gemini is not configured")
        client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=20_000, retry_options=types.HttpRetryOptions(attempts=1)))
        last_error: Exception | None = None
        for model in dict.fromkeys((self.model, "gemini-3.5-flash-lite")):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[INSTRUCTION, types.Part.from_bytes(data=data, mime_type=mime_type)],
                    config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
                )
                payload = json.loads(response.text or "")
                return ExtractedDocument.model_validate(payload).model_dump()
            except Exception as exc:
                last_error = exc
        raise DocumentExtractionUnavailable("Document extraction failed") from last_error
