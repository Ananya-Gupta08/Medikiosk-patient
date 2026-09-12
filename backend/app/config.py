from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    data_source: str = "mock"
    identity_source: str = "mock"
    session_secret: str = "development-only-change-me"
    session_max_age_seconds: int = 28_800
    database_url: str = ""
    patient_pwa_database_url: str = "sqlite:///./patient_pwa.db"
    mock_patient_id: str = "TEST_PATIENT_001"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    assistant_mode: str = "mock"
    frontend_origin: str = "http://localhost:5173"
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@example.com"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("*", mode="before")
    @classmethod
    def strip_environment_strings(cls, value: object) -> object:
        """Ignore accidental whitespace introduced by env-management tools."""
        return value.strip() if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
