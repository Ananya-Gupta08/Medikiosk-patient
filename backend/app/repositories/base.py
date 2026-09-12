from abc import ABC, abstractmethod
from app.domain import Consultation, Medication, Patient


class MedikioskRepository(ABC):
    """Read-only adapter for Medikiosk-owned clinical data."""

    @abstractmethod
    def get_patient(self, patient_id: str) -> Patient | None: ...

    @abstractmethod
    def get_patient_by_abha(self, abha_number: str) -> Patient | None: ...

    @abstractmethod
    def get_patient_consultations(self, patient_id: str) -> list[Consultation]: ...

    def get_latest_consultation(self, patient_id: str) -> Consultation | None:
        rows = self.get_patient_consultations(patient_id)
        return max(rows, key=lambda item: item.occurred_at) if rows else None

    def get_patient_diagnoses(self, patient_id: str) -> list[str]:
        return [item.diagnosis for item in self.get_patient_consultations(patient_id)]

    def get_patient_medications(self, patient_id: str) -> list[Medication]:
        return [med for visit in self.get_patient_consultations(patient_id) for med in visit.medications]

    def get_patient_prescription(self, patient_id: str, consultation_id: str) -> Consultation | None:
        return next((c for c in self.get_patient_consultations(patient_id) if c.id == consultation_id), None)
