from datetime import date, time
from app.domain import Medication
from app.repositories.mock_medikiosk_repository import MockMedikioskRepository
from app.repositories.medikiosk_repository import (
    diagnosis_from_summary,
    parse_duration_days,
    parse_times_per_day,
)
from app.services.scheduling import generate_schedule
from app.services.followup_scheduling import followup_dates, is_followup_due


def test_mock_repository_returns_synthetic_patient_and_medications():
    repo = MockMedikioskRepository()
    patient = repo.get_patient("TEST_PATIENT_001")
    assert patient and patient.name == "Ramesh Kumar"
    assert repo.get_latest_consultation(patient.id).doctor.name == "Dr Sharma"
    assert repo.get_patient_medications(patient.id)[0].name == "Paracetamol"


def test_schedule_respects_frequency_duration_and_defaults_are_preferences():
    medication = MockMedikioskRepository().get_patient_medications("TEST_PATIENT_001")[0]
    schedule = generate_schedule(medication)
    assert len(schedule) == 3 * 5
    assert len({item.scheduled_at.date() for item in schedule}) == 5
    assert all(item.time_source == "reminder_preference_default" for item in schedule)


def test_exact_times_are_preserved_and_labelled():
    medication = Medication(id="x", name="Test", dosage="1 mg", frequency="twice", times_per_day=2, duration_days=2, start_date=date(2026, 1, 1), exact_times=[time(7, 30), time(19, 45)])
    schedule = generate_schedule(medication)
    assert [x.scheduled_at.time() for x in schedule[:2]] == medication.exact_times
    assert all(x.time_source == "prescribed_exact_time" for x in schedule)


def test_missing_prescribed_duration_never_creates_occurrences():
    medication = Medication(id="x", name="Test", dosage="1 mg", frequency="twice", times_per_day=2, duration_days=None, start_date=date(2026, 1, 1))
    assert generate_schedule(medication) == []


def test_postgres_mapping_parsers_do_not_invent_clinical_values():
    assert parse_times_per_day("3 times daily") == 3
    assert parse_times_per_day("twice daily") == 2
    assert parse_duration_days("Take for 7 days") == 7
    assert parse_duration_days(None) is None
    assert diagnosis_from_summary("Assessment: Viral fever") == "Viral fever"
    assert diagnosis_from_summary("General narrative only") == "Diagnosis not recorded"


def test_followup_schedule_is_deterministic_not_ai_controlled():
    consultation = MockMedikioskRepository().consultation
    dates = followup_dates(consultation)
    assert dates == [date(2026, 9, 11), date(2026, 9, 13), date(2026, 9, 17)]
    assert is_followup_due(consultation, date(2026, 9, 11))
