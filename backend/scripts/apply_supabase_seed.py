"""Apply Patient-PWA-only schema and synthetic seed data.

DATABASE_URL must be supplied through the process environment. The URL is never
printed. This script never issues UPDATE, DELETE, DROP, or TRUNCATE statements.
"""
import os
from pathlib import Path

import psycopg


ROOT = Path(__file__).parents[1]
MIGRATIONS = [
    ROOT / "migrations" / "001_patient_pwa_owned_tables.sql",
    ROOT / "migrations" / "002_synthetic_demo_seed.sql",
]
TABLES = [
    "patient_pwa_medication_logs",
    "patient_pwa_reminder_preferences",
    "patient_pwa_push_subscriptions",
    "patient_pwa_followup_sessions",
    "patient_pwa_followup_messages",
]


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    with psycopg.connect(database_url, connect_timeout=15) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            database, user = cursor.fetchone()
            print(f"Connected to database={database}, user={user}")
            for path in MIGRATIONS:
                cursor.execute(path.read_text(encoding="utf-8"))
                print(f"Applied {path.name}")
            for table in TABLES:
                cursor.execute(f"SELECT count(*) FROM {table}")  # fixed allowlist only
                print(f"{table}: {cursor.fetchone()[0]} rows")
        connection.commit()


if __name__ == "__main__":
    main()
