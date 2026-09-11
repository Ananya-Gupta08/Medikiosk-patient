from functools import lru_cache
from app.config import get_settings
from app.repositories import make_medikiosk_repository
from app.services.gemini_service import GeminiService
from app.storage import make_pwa_store
from app.services.mock_assistant_service import MockAssistantService
from app.repositories.ocr_history_repository import OcrHistoryRepository


@lru_cache
def repository(): return make_medikiosk_repository(get_settings())


@lru_cache
def store(): return make_pwa_store(get_settings().patient_pwa_database_url)


@lru_cache
def gemini():
    settings = get_settings()
    if settings.assistant_mode == "mock":
        return MockAssistantService()
    return GeminiService(settings.gemini_api_key, settings.gemini_model)


@lru_cache
def history_repository():
    settings=get_settings()
    url=settings.database_url or settings.patient_pwa_database_url
    return OcrHistoryRepository(url)
