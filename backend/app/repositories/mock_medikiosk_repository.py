from datetime import date, datetime
from app.domain import Consultation, Doctor, Medication, Patient
from app.repositories.base import MedikioskRepository


class MockMedikioskRepository(MedikioskRepository):
    """Synthetic data only. Mirrors the future Postgres adapter contract."""

    patient = Patient(id="TEST_PATIENT_001", name="Ramesh Kumar")
    synthetic_abha = "99999999999999"
    consultation = Consultation(
        id="CONSULTATION_001",
        occurred_at=datetime(2026, 9, 10, 10, 30),
        doctor=Doctor(id="DOCTOR_001", name="Dr Sharma"),
        location="Medikiosk",
        diagnosis="Post-operative prostate surgery",
        medications=[
            Medication(id="MED_001", name="Paracetamol", dosage="500 mg", quantity="1 tablet", frequency="3 times daily", times_per_day=3, duration_days=5, start_date=date(2026, 9, 10), instructions="After food"),
            Medication(id="MED_002", name="Medicine B", dosage="As prescribed", quantity="1 tablet", frequency="Once daily", times_per_day=1, duration_days=7, start_date=date(2026, 9, 10)),
        ],
    )

    def get_patient(self, patient_id: str) -> Patient | None:
        return self.patient if patient_id == self.patient.id else None

    def get_patient_by_abha(self, abha_number: str) -> Patient | None:
        normalized = "".join(character for character in abha_number if character.isdigit())
        return self.patient if normalized == self.synthetic_abha else None

    def get_patient_consultations(self, patient_id: str) -> list[Consultation]:
        return [self.consultation] if patient_id == self.patient.id else []
