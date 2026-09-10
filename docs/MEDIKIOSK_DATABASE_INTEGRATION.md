# Medikiosk database integration contract

The Patient PWA treats Medikiosk clinical information as read-only source data. Clinical schema knowledge must remain inside `backend/app/repositories/medikiosk_repository.py`. Routes and services consume normalized domain models, so a schema change should require adapter changes rather than an application rewrite.

| Patient PWA field | Required | Medikiosk DB mapping |
|---|---:|---|
| patient_id | Yes | TBD |
| patient_name | Yes | TBD |
| consultation_id | Yes | TBD |
| consultation_date | Yes | TBD |
| doctor_id | Optional | TBD |
| doctor_name | Yes | TBD |
| location | Optional | TBD |
| diagnosis | Yes | TBD |
| medicine_id | Yes | TBD |
| medicine_name | Yes | TBD |
| dosage | Yes | TBD |
| quantity | Optional | TBD |
| frequency | Yes | TBD |
| normalized times_per_day | Yes | TBD or deterministic mapping in adapter |
| duration | Yes | TBD |
| start_date | Yes | TBD |
| instructions | Optional | TBD |
| exact_medication_times | Optional | TBD |
| prescription_document | Optional | TBD |

## Information required from the database team

- Table/view names, columns, keys, and clinical relationships.
- Canonical patient identifier (including ABHA normalization rules, if applicable).
- Supabase authentication/JWT claims and row-level security policy.
- Medication frequency and duration encodings, timezone semantics, and whether exact times are clinical instructions.
- Document storage bucket, signed-URL rules, and expiry behavior.
- A least-privilege database role or server-side access mechanism with read-only clinical permissions and read/write access only to `patient_pwa_*` tables.

## Adapter implementation checklist

1. Set `DATABASE_URL` to the Supabase pooler/direct Postgres URL on the backend only.
2. Implement parameterized reads in `PostgresMedikioskRepository`; never interpolate identity values into SQL.
3. Map rows to `Patient`, `Consultation`, `Doctor`, and `Medication` domain models.
4. Replace mock identity with verified Supabase JWT claims and derive the canonical patient ID server-side.
5. Apply `backend/migrations/001_patient_pwa_owned_tables.sql` only for PWA-owned data and enable appropriate RLS.
6. Move the owned-data `PwaStore` from SQLite to a Postgres implementation with the same methods.
7. Run contract, authorization, scheduling, and end-to-end tests in a staging Supabase project before setting `DATA_SOURCE=postgres`.

Never write back into source prescriptions, diagnoses, medicines, consultations, doctors, or patients.

