from app.identity import create_session_token, read_session_token
from app.repositories.mock_medikiosk_repository import MockMedikioskRepository


def test_abha_maps_to_canonical_patient_without_creating_identity():
    repository = MockMedikioskRepository()
    patient = repository.get_patient_by_abha("99-9999-9999-9999")
    assert patient and patient.id == "TEST_PATIENT_001"
    assert repository.get_patient_by_abha("11-1111-1111-1111") is None


def test_signed_patient_session_rejects_tampering():
    token = create_session_token("TEST_PATIENT_001")
    assert read_session_token(token).patient_id == "TEST_PATIENT_001"
    assert read_session_token(token + "changed") is None
