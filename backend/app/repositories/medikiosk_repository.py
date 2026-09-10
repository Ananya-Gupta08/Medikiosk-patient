from app.domain import Consultation, Patient
from app.repositories.base import MedikioskRepository


class PostgresMedikioskRepository(MedikioskRepository):
    """Integration seam for the shared Supabase database.

    Clinical SQL belongs only here. Mapping is intentionally blocked until the
    Medikiosk schema and authorization policy are supplied.
    """

    def __init__(self, database_url: str):
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when DATA_SOURCE=postgres")
        self.database_url = database_url

    def get_patient(self, patient_id: str) -> Patient | None:
        raise NotImplementedError("Map the Medikiosk patient schema in this adapter")

    def get_patient_consultations(self, patient_id: str) -> list[Consultation]:
        raise NotImplementedError("Map the Medikiosk clinical schema in this adapter")

