from dataclasses import dataclass
from fastapi import Header, HTTPException
from app.config import get_settings


@dataclass(frozen=True)
class Identity:
    patient_id: str


def current_identity(x_mock_patient_id: str | None = Header(default=None)) -> Identity:
    settings = get_settings()
    if settings.data_source != "mock":
        # Replace with verified Supabase JWT claims; never accept patient IDs from URLs.
        raise HTTPException(status_code=501, detail="Authentication provider is not configured")
    requested = x_mock_patient_id or settings.mock_patient_id
    if requested != settings.mock_patient_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return Identity(patient_id=requested)

