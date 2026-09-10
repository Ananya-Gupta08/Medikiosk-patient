from datetime import date, timedelta
from app.domain import Consultation


# Deterministic policy owned by the application. Gemini never selects due dates.
DEFAULT_FOLLOWUP_DAY_OFFSETS = (1, 3, 7)


def followup_dates(consultation: Consultation, offsets: tuple[int, ...] = DEFAULT_FOLLOWUP_DAY_OFFSETS) -> list[date]:
    start = consultation.occurred_at.date()
    return [start + timedelta(days=offset) for offset in offsets]


def is_followup_due(consultation: Consultation | None, selected: date) -> bool:
    return bool(consultation and selected in followup_dates(consultation))

