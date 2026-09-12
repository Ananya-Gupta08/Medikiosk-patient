from datetime import date, datetime, time
from pydantic import BaseModel, Field


class Patient(BaseModel):
    id: str
    name: str


class Doctor(BaseModel):
    id: str | None = None
    name: str


class Medication(BaseModel):
    id: str
    name: str
    dosage: str
    quantity: str = "As prescribed"
    frequency: str
    times_per_day: int = Field(ge=1, le=12)
    duration_days: int | None = Field(default=None, ge=1, le=365)
    start_date: date
    instructions: str | None = None
    exact_times: list[time] | None = None


class Consultation(BaseModel):
    id: str
    occurred_at: datetime
    doctor: Doctor
    location: str | None = None
    diagnosis: str
    medications: list[Medication] = []
    prescription_document_url: str | None = None


class ScheduleOccurrence(BaseModel):
    id: str
    medication_id: str
    medication_name: str
    dosage: str
    quantity: str
    instructions: str | None = None
    scheduled_at: datetime
    time_source: str
    status: str = "pending"
    completed_at: datetime | None = None
