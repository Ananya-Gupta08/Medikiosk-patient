from app.config import Settings
from app.repositories.base import MedikioskRepository
from app.repositories.medikiosk_repository import PostgresMedikioskRepository
from app.repositories.mock_medikiosk_repository import MockMedikioskRepository


def make_medikiosk_repository(settings: Settings) -> MedikioskRepository:
    if settings.data_source == "mock":
        return MockMedikioskRepository()
    if settings.data_source == "postgres":
        return PostgresMedikioskRepository(settings.database_url)
    raise RuntimeError("DATA_SOURCE must be 'mock' or 'postgres'")

