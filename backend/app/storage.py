import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


SCHEMA = """
CREATE TABLE IF NOT EXISTS patient_pwa_medication_logs (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, schedule_id TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status='taken'), completed_at TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(patient_id, schedule_id));
CREATE TABLE IF NOT EXISTS patient_pwa_reminder_preferences (
 patient_id TEXT NOT NULL, times_per_day INTEGER NOT NULL, reminder_times TEXT NOT NULL,
 PRIMARY KEY(patient_id, times_per_day));
CREATE TABLE IF NOT EXISTS patient_pwa_push_subscriptions (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, endpoint TEXT NOT NULL UNIQUE,
 subscription_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS patient_pwa_followup_sessions (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, diagnosis_value TEXT NOT NULL,
 consultation_reference TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL,
 completed_at TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS patient_pwa_followup_messages (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL,
 message TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(session_id) REFERENCES patient_pwa_followup_sessions(id));
CREATE TABLE IF NOT EXISTS patient_pwa_appointment_requests (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, consultation_reference TEXT NOT NULL,
 reason TEXT NOT NULL, status TEXT NOT NULL CHECK(status='requested'),
 requested_at TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(patient_id, consultation_reference, status));
CREATE TABLE IF NOT EXISTS patient_pwa_uploaded_records (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, file_name TEXT NOT NULL,
 mime_type TEXT NOT NULL, file_size INTEGER NOT NULL, file_data BLOB NOT NULL,
 extraction_status TEXT NOT NULL, extracted_data TEXT, patient_summary TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
"""


class PwaStore:
    def __init__(self, url: str):
        if not url.startswith("sqlite:///"):
            raise RuntimeError("MVP owned-data store currently supports sqlite:/// URLs; Supabase migration SQL is provided")
        raw = url.removeprefix("sqlite:///")
        self.path = raw if raw == ":memory:" else str(Path(raw).resolve())
        self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False) if raw == ":memory:" else None
        self.initialize()

    @contextmanager
    def connection(self):
        connection = self._memory_connection or sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            if self._memory_connection is None:
                connection.close()

    def initialize(self):
        with self.connection() as db:
            db.executescript(SCHEMA)

    def logs(self, patient_id: str) -> dict[str, dict]:
        with self.connection() as db:
            rows = db.execute("SELECT schedule_id,status,completed_at FROM patient_pwa_medication_logs WHERE patient_id=?", (patient_id,)).fetchall()
        return {row["schedule_id"]: dict(row) for row in rows}

    def mark_taken(self, patient_id: str, schedule_id: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection() as db:
            db.execute("INSERT OR IGNORE INTO patient_pwa_medication_logs VALUES (?,?,?,?,?,?)", (str(uuid4()), patient_id, schedule_id, "taken", now, now))
            row = db.execute("SELECT schedule_id,status,completed_at FROM patient_pwa_medication_logs WHERE patient_id=? AND schedule_id=?", (patient_id, schedule_id)).fetchone()
        return dict(row)

    def add_subscription(self, patient_id: str, subscription: dict) -> dict:
        now, sub_id = datetime.now(timezone.utc).isoformat(), str(uuid4())
        endpoint = subscription["endpoint"]
        with self.connection() as db:
            db.execute("INSERT INTO patient_pwa_push_subscriptions VALUES (?,?,?,?,?) ON CONFLICT(endpoint) DO UPDATE SET patient_id=excluded.patient_id, subscription_json=excluded.subscription_json", (sub_id, patient_id, endpoint, json.dumps(subscription), now))
            row = db.execute("SELECT id,endpoint,created_at FROM patient_pwa_push_subscriptions WHERE endpoint=?", (endpoint,)).fetchone()
        return dict(row)

    def remove_subscription(self, patient_id: str, sub_id: str) -> bool:
        with self.connection() as db:
            result = db.execute("DELETE FROM patient_pwa_push_subscriptions WHERE id=? AND patient_id=?", (sub_id, patient_id))
        return result.rowcount > 0

    def create_session(self, patient_id: str, diagnosis: str, consultation_id: str) -> dict:
        now, session_id = datetime.now(timezone.utc).isoformat(), str(uuid4())
        with self.connection() as db:
            db.execute("INSERT INTO patient_pwa_followup_sessions VALUES (?,?,?,?,?,?,?,?)", (session_id, patient_id, diagnosis, consultation_id, "active", now, None, now))
        return self.session(patient_id, session_id)

    def session(self, patient_id: str, session_id: str) -> dict | None:
        with self.connection() as db:
            row = db.execute("SELECT * FROM patient_pwa_followup_sessions WHERE id=? AND patient_id=?", (session_id, patient_id)).fetchone()
        return dict(row) if row else None

    def sessions(self, patient_id: str) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT * FROM patient_pwa_followup_sessions WHERE patient_id=? ORDER BY started_at DESC", (patient_id,)).fetchall()
        return [dict(row) for row in rows]

    def add_message(self, session_id: str, role: str, message: str) -> dict:
        now, message_id = datetime.now(timezone.utc).isoformat(), str(uuid4())
        with self.connection() as db:
            db.execute("INSERT INTO patient_pwa_followup_messages VALUES (?,?,?,?,?)", (message_id, session_id, role, message, now))
        return {"id": message_id, "role": role, "message": message, "created_at": now}

    def messages(self, session_id: str) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT id,role,message,created_at FROM patient_pwa_followup_messages WHERE session_id=? ORDER BY created_at", (session_id,)).fetchall()
        return [dict(row) for row in rows]

    def complete_session(self, session_id: str):
        with self.connection() as db:
            db.execute("UPDATE patient_pwa_followup_sessions SET status='complete', completed_at=? WHERE id=?", (datetime.now(timezone.utc).isoformat(), session_id))

    def create_appointment_request(self, patient_id: str, consultation_id: str, reason: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection() as db:
            db.execute("INSERT OR IGNORE INTO patient_pwa_appointment_requests VALUES (?,?,?,?,?,?,?)", (str(uuid4()), patient_id, consultation_id, reason, "requested", now, now))
            row = db.execute("SELECT id,consultation_reference,reason,status,requested_at FROM patient_pwa_appointment_requests WHERE patient_id=? AND consultation_reference=? AND status='requested'", (patient_id, consultation_id)).fetchone()
        return dict(row)

    def appointment_requests(self, patient_id: str) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT id,consultation_reference,reason,status,requested_at FROM patient_pwa_appointment_requests WHERE patient_id=? ORDER BY requested_at DESC", (patient_id,)).fetchall()
        return [dict(row) for row in rows]

    def create_uploaded_record(self, patient_id: str, file_name: str, mime_type: str, data: bytes) -> dict:
        now, record_id = datetime.now(timezone.utc).isoformat(), str(uuid4())
        with self.connection() as db:
            db.execute("INSERT INTO patient_pwa_uploaded_records VALUES (?,?,?,?,?,?,?,?,?,?,?)", (record_id,patient_id,file_name,mime_type,len(data),data,"pending",None,None,now,now))
        return self.uploaded_record(patient_id, record_id)

    def uploaded_record(self, patient_id: str, record_id: str, include_file: bool = False) -> dict | None:
        fields = "*" if include_file else "id,patient_id,file_name,mime_type,file_size,extraction_status,extracted_data,patient_summary,created_at,updated_at"
        with self.connection() as db:
            row = db.execute(f"SELECT {fields} FROM patient_pwa_uploaded_records WHERE id=? AND patient_id=?", (record_id,patient_id)).fetchone()
        return self._uploaded_dict(row) if row else None

    def uploaded_records(self, patient_id: str) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT id,patient_id,file_name,mime_type,file_size,extraction_status,extracted_data,patient_summary,created_at,updated_at FROM patient_pwa_uploaded_records WHERE patient_id=? ORDER BY created_at DESC", (patient_id,)).fetchall()
        return [self._uploaded_dict(row) for row in rows]

    def save_extraction(self, patient_id: str, record_id: str, extracted: dict | None) -> dict | None:
        with self.connection() as db:
            db.execute("UPDATE patient_pwa_uploaded_records SET extraction_status=?,extracted_data=?,updated_at=? WHERE id=? AND patient_id=?", ("complete" if extracted else "failed",json.dumps(extracted) if extracted else None,datetime.now(timezone.utc).isoformat(),record_id,patient_id))
        return self.uploaded_record(patient_id, record_id)

    def update_uploaded_summary(self, patient_id: str, record_id: str, summary: str) -> dict | None:
        with self.connection() as db:
            result = db.execute("UPDATE patient_pwa_uploaded_records SET patient_summary=?,updated_at=? WHERE id=? AND patient_id=?", (summary,datetime.now(timezone.utc).isoformat(),record_id,patient_id))
            changed = result.rowcount
        return self.uploaded_record(patient_id, record_id) if changed else None

    @staticmethod
    def _uploaded_dict(row) -> dict:
        result = dict(row)
        if isinstance(result.get("extracted_data"), str): result["extracted_data"] = json.loads(result["extracted_data"])
        return result


class PostgresPwaStore:
    """Supabase/PostgreSQL store for Patient-PWA-owned data only."""
    def __init__(self, url: str):
        import psycopg
        self.url, self.psycopg = url, psycopg

    @contextmanager
    def connection(self):
        with self.psycopg.connect(self.url, connect_timeout=15) as connection:
            with connection.cursor(row_factory=self.psycopg.rows.dict_row) as cursor:
                yield cursor
            connection.commit()

    def logs(self, patient_id: str) -> dict[str, dict]:
        with self.connection() as db:
            db.execute("SELECT schedule_id,status,completed_at FROM patient_pwa_medication_logs WHERE patient_id=%s", (patient_id,)); rows=db.fetchall()
        return {row["schedule_id"]:{**row,"completed_at":row["completed_at"].isoformat()} for row in rows}

    def mark_taken(self, patient_id: str, schedule_id: str) -> dict:
        with self.connection() as db:
            db.execute("INSERT INTO patient_pwa_medication_logs (id,patient_id,schedule_id,status,completed_at,created_at) VALUES (%s,%s,%s,'taken',now(),now()) ON CONFLICT(patient_id,schedule_id) DO NOTHING", (str(uuid4()),patient_id,schedule_id))
            db.execute("SELECT schedule_id,status,completed_at FROM patient_pwa_medication_logs WHERE patient_id=%s AND schedule_id=%s", (patient_id,schedule_id)); row=db.fetchone()
        return {**row,"completed_at":row["completed_at"].isoformat()}

    def add_subscription(self, patient_id: str, subscription: dict) -> dict:
        with self.connection() as db:
            db.execute("INSERT INTO patient_pwa_push_subscriptions (id,patient_id,endpoint,subscription_json,created_at) VALUES (%s,%s,%s,%s::jsonb,now()) ON CONFLICT(endpoint) DO UPDATE SET patient_id=excluded.patient_id,subscription_json=excluded.subscription_json RETURNING id,endpoint,created_at", (str(uuid4()),patient_id,subscription["endpoint"],json.dumps(subscription))); row=db.fetchone()
        return {**row,"id":str(row["id"]),"created_at":row["created_at"].isoformat()}

    def remove_subscription(self, patient_id: str, sub_id: str) -> bool:
        with self.connection() as db:
            db.execute("DELETE FROM patient_pwa_push_subscriptions WHERE id=%s AND patient_id=%s", (sub_id,patient_id)); return db.rowcount>0

    def _session_dict(self, row):
        if not row: return None
        result=dict(row); result["id"]=str(result["id"])
        for key in ("started_at","completed_at","created_at"):
            if result.get(key): result[key]=result[key].isoformat()
        return result

    def create_session(self, patient_id: str, diagnosis: str, consultation_id: str) -> dict:
        session_id=str(uuid4())
        with self.connection() as db:
            db.execute("INSERT INTO patient_pwa_followup_sessions (id,patient_id,diagnosis_value,consultation_reference,status,started_at,created_at) VALUES (%s,%s,%s,%s,'active',now(),now())", (session_id,patient_id,diagnosis,consultation_id))
        return self.session(patient_id,session_id)

    def session(self, patient_id: str, session_id: str) -> dict | None:
        with self.connection() as db:
            db.execute("SELECT * FROM patient_pwa_followup_sessions WHERE id=%s AND patient_id=%s", (session_id,patient_id)); row=db.fetchone()
        return self._session_dict(row)

    def sessions(self, patient_id: str) -> list[dict]:
        with self.connection() as db:
            db.execute("SELECT * FROM patient_pwa_followup_sessions WHERE patient_id=%s ORDER BY started_at DESC", (patient_id,)); rows=db.fetchall()
        return [self._session_dict(row) for row in rows]

    def add_message(self, session_id: str, role: str, message: str) -> dict:
        message_id=str(uuid4())
        with self.connection() as db:
            db.execute("INSERT INTO patient_pwa_followup_messages (id,session_id,role,message,created_at) VALUES (%s,%s,%s,%s,now()) RETURNING created_at", (message_id,session_id,role,message)); created=db.fetchone()["created_at"]
        return {"id":message_id,"role":role,"message":message,"created_at":created.isoformat()}

    def messages(self, session_id: str) -> list[dict]:
        with self.connection() as db:
            db.execute("SELECT id,role,message,created_at FROM patient_pwa_followup_messages WHERE session_id=%s ORDER BY created_at,id", (session_id,)); rows=db.fetchall()
        return [{**row,"id":str(row["id"]),"created_at":row["created_at"].isoformat()} for row in rows]

    def complete_session(self, session_id: str):
        with self.connection() as db:
            db.execute("UPDATE patient_pwa_followup_sessions SET status='complete',completed_at=now() WHERE id=%s", (session_id,))

    def create_appointment_request(self, patient_id: str, consultation_id: str, reason: str) -> dict:
        with self.connection() as db:
            db.execute("INSERT INTO patient_pwa_appointment_requests (id,patient_id,consultation_reference,reason,status,requested_at,created_at) VALUES (%s,%s,%s,%s,'requested',now(),now()) ON CONFLICT DO NOTHING", (str(uuid4()),patient_id,consultation_id,reason))
            db.execute("SELECT id,consultation_reference,reason,status,requested_at FROM patient_pwa_appointment_requests WHERE patient_id=%s AND consultation_reference=%s AND status='requested'", (patient_id,consultation_id)); row=db.fetchone()
        return {**row,"id":str(row["id"]),"requested_at":row["requested_at"].isoformat()}

    def appointment_requests(self, patient_id: str) -> list[dict]:
        with self.connection() as db:
            db.execute("SELECT id,consultation_reference,reason,status,requested_at FROM patient_pwa_appointment_requests WHERE patient_id=%s ORDER BY requested_at DESC", (patient_id,)); rows=db.fetchall()
        return [{**row,"id":str(row["id"]),"requested_at":row["requested_at"].isoformat()} for row in rows]

    def create_uploaded_record(self, patient_id: str, file_name: str, mime_type: str, data: bytes) -> dict:
        record_id=str(uuid4())
        with self.connection() as db:
            db.execute("INSERT INTO patient_pwa_uploaded_records (id,patient_id,file_name,mime_type,file_size,file_data,extraction_status,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,'pending',now(),now())", (record_id,patient_id,file_name,mime_type,len(data),data))
        return self.uploaded_record(patient_id,record_id)

    def uploaded_record(self, patient_id: str, record_id: str, include_file: bool = False) -> dict | None:
        fields="*" if include_file else "id,patient_id,file_name,mime_type,file_size,extraction_status,extracted_data,patient_summary,created_at,updated_at"
        with self.connection() as db:
            db.execute(f"SELECT {fields} FROM patient_pwa_uploaded_records WHERE id=%s AND patient_id=%s",(record_id,patient_id)); row=db.fetchone()
        return self._uploaded_dict(row) if row else None

    def uploaded_records(self, patient_id: str) -> list[dict]:
        with self.connection() as db:
            db.execute("SELECT id,patient_id,file_name,mime_type,file_size,extraction_status,extracted_data,patient_summary,created_at,updated_at FROM patient_pwa_uploaded_records WHERE patient_id=%s ORDER BY created_at DESC",(patient_id,)); rows=db.fetchall()
        return [self._uploaded_dict(row) for row in rows]

    def save_extraction(self, patient_id: str, record_id: str, extracted: dict | None) -> dict | None:
        with self.connection() as db:
            db.execute("UPDATE patient_pwa_uploaded_records SET extraction_status=%s,extracted_data=%s::jsonb,updated_at=now() WHERE id=%s AND patient_id=%s",("complete" if extracted else "failed",json.dumps(extracted) if extracted else None,record_id,patient_id))
        return self.uploaded_record(patient_id,record_id)

    def update_uploaded_summary(self, patient_id: str, record_id: str, summary: str) -> dict | None:
        with self.connection() as db:
            db.execute("UPDATE patient_pwa_uploaded_records SET patient_summary=%s,updated_at=now() WHERE id=%s AND patient_id=%s",(summary,record_id,patient_id)); changed=db.rowcount
        return self.uploaded_record(patient_id,record_id) if changed else None

    @staticmethod
    def _uploaded_dict(row) -> dict:
        result=dict(row); result["id"]=str(result["id"])
        for key in ("created_at","updated_at"):
            if result.get(key): result[key]=result[key].isoformat()
        return result


def make_pwa_store(url: str):
    return PostgresPwaStore(url) if url.startswith(("postgresql://","postgres://")) else PwaStore(url)
