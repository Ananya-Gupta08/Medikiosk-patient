import re
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.domain import Consultation, Doctor, Medication, Patient
from app.repositories.base import MedikioskRepository


def parse_times_per_day(frequency: str) -> int:
    value = frequency.strip().lower()
    labels = {
        "once": 1, "one time": 1, "twice": 2, "two times": 2,
        "thrice": 3, "three times": 3, "four times": 4,
    }
    for label, count in labels.items():
        if label in value:
            return count
    match = re.search(r"\b(\d{1,2})\s*(?:x|times?)\b", value)
    return max(1, min(12, int(match.group(1)))) if match else 1


def parse_duration_days(value: Any) -> int | None:
    if isinstance(value, int):
        return value if 1 <= value <= 365 else None
    match = re.search(r"\b(\d{1,3})\s*days?\b", str(value or ""), re.IGNORECASE)
    return int(match.group(1)) if match and 1 <= int(match.group(1)) <= 365 else None


def diagnosis_from_summary(summary: str | None) -> str:
    for pattern in (
        r"(?im)^\s*(?:final\s+)?diagnosis\s*:\s*(.+)$",
        r"(?im)^\s*assessment\s*:\s*(.+)$",
        r"(?im)^\s*impression\s*:\s*(.+)$",
    ):
        match = re.search(pattern, summary or "")
        if match:
            return match.group(1).strip()
    return "Diagnosis not recorded"


class PostgresMedikioskRepository(MedikioskRepository):
    """Read-only adapter for the encounters-based Medikiosk schema."""

    def __init__(self, database_url: str):
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when DATA_SOURCE=postgres")
        self.database_url = database_url

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row, connect_timeout=10)

    def get_patient(self, patient_id: str) -> Patient | None:
        with self._connect() as connection, connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            row = connection.execute(
                "SELECT id, display_name FROM patients WHERE id = %s", (patient_id,)
            ).fetchone()
        return Patient(id=str(row["id"]), name=row["display_name"] or "Patient") if row else None

    def get_patient_by_abha(self, abha_number: str) -> Patient | None:
        normalized = "".join(character for character in abha_number if character.isdigit())
        if len(normalized) != 14:
            return None
        with self._connect() as connection, connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            row = connection.execute(
                """SELECT id, display_name FROM patients
                   WHERE regexp_replace(abha_id, '[^0-9]', '', 'g') = %s""",
                (normalized,),
            ).fetchone()
        return Patient(id=str(row["id"]), name=row["display_name"] or "Patient") if row else None

    def get_patient_consultations(self, patient_id: str) -> list[Consultation]:
        with self._connect() as connection, connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            encounters = connection.execute(
                """
                SELECT e.id, COALESCE(e.submitted_at, e.created_at) AS occurred_at,
                       s.draft_en, s.verified_by
                FROM encounters e
                LEFT JOIN LATERAL (
                    SELECT draft_en, verified_by
                    FROM encounter_summaries
                    WHERE encounter_id = e.id
                    ORDER BY updated_at DESC LIMIT 1
                ) s ON TRUE
                WHERE e.patient_id = %s
                ORDER BY COALESCE(e.submitted_at, e.created_at) DESC
                """,
                (patient_id,),
            ).fetchall()
            encounter_ids = [row["id"] for row in encounters]
            prescriptions = self._prescriptions(connection, encounter_ids)
            documents = self._prescription_documents(connection, encounter_ids)

        by_encounter: dict[Any, list[dict]] = defaultdict(list)
        for row in prescriptions:
            by_encounter[row["encounter_id"]].append(row)
        document_by_encounter = {
            row["encounter_id"]: row["original_file_reference"] for row in documents
        }
        result = []
        for encounter in encounters:
            occurred_at = encounter["occurred_at"] or datetime.now(timezone.utc)
            result.append(Consultation(
                id=str(encounter["id"]), occurred_at=occurred_at,
                doctor=Doctor(name=encounter["verified_by"] or "Treating clinician"),
                location=None, diagnosis=diagnosis_from_summary(encounter["draft_en"]),
                medications=self._medications(by_encounter[encounter["id"]], occurred_at.date()),
                prescription_document_url=document_by_encounter.get(encounter["id"]),
            ))
        return result

    @staticmethod
    def _prescriptions(connection, encounter_ids: list[Any]) -> list[dict]:
        if not encounter_ids:
            return []
        return connection.execute(
            """SELECT id, encounter_id, items, notes, created_at FROM prescriptions
               WHERE encounter_id = ANY(%s) ORDER BY created_at""",
            (encounter_ids,),
        ).fetchall()

    @staticmethod
    def _prescription_documents(connection, encounter_ids: list[Any]) -> list[dict]:
        if not encounter_ids:
            return []
        return connection.execute(
            """SELECT encounter_id, original_file_reference FROM medical_documents
               WHERE encounter_id = ANY(%s)
                 AND lower(document_type) LIKE '%%prescription%%'
                 AND original_file_reference IS NOT NULL
               ORDER BY created_at""",
            (encounter_ids,),
        ).fetchall()

    @staticmethod
    def _medications(rows: list[dict], start_date: date) -> list[Medication]:
        medications = []
        for prescription in rows:
            items = prescription["items"] if isinstance(prescription["items"], list) else []
            for index, item in enumerate(items):
                if not isinstance(item, dict) or not str(item.get("name", "")).strip():
                    continue
                frequency = str(item.get("frequency") or "As prescribed").strip()
                medications.append(Medication(
                    id=f'{prescription["id"]}:{index}', name=str(item["name"]).strip(),
                    dosage=str(item.get("dose") or "As prescribed").strip(),
                    quantity=str(item.get("quantity") or "As prescribed").strip(),
                    frequency=frequency, times_per_day=parse_times_per_day(frequency),
                    duration_days=parse_duration_days(item.get("duration")), start_date=start_date,
                    instructions=str(item["instructions"]).strip() if item.get("instructions") else None,
                    exact_times=None,
                ))
        return medications
