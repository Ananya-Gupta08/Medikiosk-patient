from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    data_source: str = "mock"
    database_url: str = ""
    patient_pwa_database_url: str = "sqlite:///./patient_pwa.db"
    mock_patient_id: str = "TEST_PATIENT_001"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    assistant_mode: str = "mock"
    frontend_origin: str = "http://localhost:5173"
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@example.com"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
