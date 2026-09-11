# Medikiosk database integration contract

## Ownership boundary

The Patient PWA reads clinical information created by Medikiosk and the doctor/hospital portal. Patients, doctors, consultations, diagnoses, prescriptions, medicines, and original OCR documents remain Medikiosk-owned source records.

Clinical mappings belong only in `backend/app/repositories/medikiosk_repository.py`. Routes and services consume normalized domain models so schema changes remain adapter changes rather than application rewrites.

Patient actions are stored separately in:

- `patient_pwa_medication_logs`
- `patient_pwa_reminder_preferences`
- `patient_pwa_push_subscriptions`
- `patient_pwa_followup_sessions`
- `patient_pwa_followup_messages`
- `patient_pwa_history_edits`

Original OCR output is immutable. Patient corrections reference it through `patient_id` and `medical_document_id`.

## Current status

| Area | Status |
|---|---|
| Patient-PWA-owned PostgreSQL storage | Connected to Supabase |
| Taken status/reminder preferences | PostgreSQL implementation available |
| Follow-up sessions/messages | PostgreSQL implementation available |
| Patient history corrections | PostgreSQL implementation available |
| OCR document discovery | Mapped to `public.medical_documents` |
| Clinical patient/consultation/prescription adapter | Awaiting portal schema |
| Production authentication | Awaiting JWT mapping and RLS |
| Development clinical data | Synthetic mock repository |

`DATA_SOURCE=mock` currently controls clinical reads. `PATIENT_PWA_DATABASE_URL` controls Patient-PWA-owned Supabase storage.

## Required normalized clinical fields

| Patient PWA field | Required | Medikiosk mapping |
|---|---:|---|
| `patient_id` | Yes | TBD canonical patient key |
| `patient_name` | Yes | TBD |
| `abha_number` | Optional | TBD with normalization rules |
| `preferred_language` | Optional | TBD |
| `timezone` | Recommended | TBD |
| `consultation_id` | Yes | TBD |
| `consultation_datetime` | Yes | TBD with timezone semantics |
| `consultation_status` | Recommended | TBD completed-record rule |
| `doctor_id` | Recommended | TBD |
| `doctor_name` | Yes | TBD |
| `speciality` | Optional | TBD |
| `facility_id` | Optional | TBD |
| `facility_name/location` | Optional | TBD |
| `diagnosis_id` | Recommended | TBD |
| `diagnosis` | Yes | TBD final/primary diagnosis |
| `diagnosis_code` | Optional | TBD |
| `clinical_summary` | Optional | TBD |
| `prescription_id` | Yes | TBD |
| `prescribed_at` | Yes | TBD |
| `prescription_status` | Recommended | TBD |
| `prescription_medicine_id` | Yes | TBD stable line ID |
| `medicine_id` | Recommended | TBD |
| `medicine_name` | Yes | TBD |
| `dosage/strength` | Yes | TBD |
| `dose_quantity` | Yes | TBD, e.g. `1 tablet` |
| `dose_unit` | Recommended | TBD |
| `frequency_text` | Yes | TBD |
| `times_per_day` | Strongly recommended | TBD normalized integer |
| `duration_days` | Yes | TBD normalized integer |
| `start_date` | Yes | TBD |
| `end_date` | Recommended | TBD |
| `instructions` | Optional | TBD |
| `administration_route` | Optional | TBD |
| `exact_medication_times` | Optional | TBD doctor-prescribed times only |
| `medicine_status` | Recommended | TBD |
| `prescription_document` | Optional | TBD storage reference |

The portal must distinguish doctor-prescribed exact times from general frequency and patient-selected reminders. AI never determines medicine, dosage, frequency, or duration.

## Discovered OCR schema

The shared database contains `public.medical_documents`:

| Column | Type | Use |
|---|---|---|
| `id` | `uuid` | Stable document reference |
| `patient_id` | `text` | Ownership/authorization |
| `ocr_document_id` | `uuid` | OCR processing reference |
| `document_type` | `text` | Display category |
| `extraction_timestamp` | `timestamptz` | OCR processing time |
| `clinical_document_date` | `date`, nullable | Timeline date |
| `confidence_score` | `double precision` | OCR confidence |
| `structured_data` | `jsonb` | Primary extracted history source |
| `extraction_errors` | `jsonb` | Processing errors |
| `complete_ocr_result` | `jsonb` | Full OCR result |
| `original_file_reference` | `text`, nullable | Storage reference |
| `created_at` | `timestamptz` | Creation time |
| `updated_at` | `timestamptz` | Update time |
| `indexing_status` | `text` | Internal indexing state |
| `indexing_attempts` | `integer` | Internal metadata |
| `indexing_error` | `text`, nullable | Internal metadata |
| `indexed_at` | `timestamptz`, nullable | Internal metadata |
| `encounter_id` | `uuid`, nullable | Potential consultation link |

### Discovered `structured_data` keys

`clinical_notes`, `diagnosis`, `final_diagnosis`, `findings`, `impression`, `medications`, `discharge_medications`, `discharge_advice`, `recommendations`, `test_results`, `tests`, `vital_signs`, `extra_notes`, `remarks`, `other_info`, `patient_info`, and `metadata`.

The History adapter currently presents these narrative fields when available:

1. `clinical_notes`
2. `findings`
3. `impression`
4. `diagnosis`
5. `final_diagnosis`
6. `extra_notes`
7. `remarks`

The portal team must supply a stable JSON schema defining each key's value type, nullability, and meaning.

### Discovered `complete_ocr_result` keys

`clinical_entities`, `clinical_summary`, `data`, `document_metadata`, `document_type`, `ocr_status`, `patient_info`, `structured_document`, and `test_marker`.

`structured_data` is preferred because it exposes normalized fields directly. `complete_ocr_result` may be used as an adapter fallback after its schema is documented.

## Editable history

History is read from `medical_documents.structured_data`. The Patient PWA never updates that JSON.

```text
patient_pwa_history_edits
  id
  patient_id
  medical_document_id
  edited_history
  created_at
  updated_at
  UNIQUE(patient_id, medical_document_id)
```

Rules:

- List queries filter source documents by authenticated `patient_id`.
- Updates use `/api/me/history/{document_id}`.
- The backend verifies document ownership before saving.
- The original source is returned separately as `extracted_history`.
- Corrections do not modify diagnoses, prescriptions, medicines, or files.

The mock patient is not inserted into real clinical tables because `medical_documents.patient_id` references the real `patients` table. Development uses `patient_pwa_demo_ocr_documents`; production continues to read `public.medical_documents`.

## Original document access requirements

The hospital team must provide the Storage bucket, object-path format, MIME types, document categories, signed-URL generation and expiry policy, patient authorization/RLS rules, and superseded-document behavior. Medical documents must not use permanent public URLs.

## Required relationships

```text
patient
├── consultations
│   ├── diagnoses
│   ├── prescriptions
│   │   └── prescription medicines
│   └── medical documents (possibly via encounter_id)
└── medical documents
```

For every relationship, provide primary/foreign keys, cardinality, cascade behavior, soft-delete columns, visibility status rules, and version-history behavior.

## Authentication and RLS

Required from the database team:

- Supabase Auth user identifier.
- JWT claim containing or mapping to canonical `patient_id`.
- `auth.users.id` to clinical patient mapping.
- Patient clinical-read RLS policies.
- Patient ownership policies for `patient_pwa_*` rows.
- Separate doctor/hospital policies.
- Rules for inactive, merged, or duplicate patients.
- Token expiration/refresh behavior.
- A least-privilege backend role. No database secret may reach frontend code.

## Recommended stable views

- `patient_pwa_patient_view`
- `patient_pwa_consultations_view`
- `patient_pwa_prescriptions_view`
- `patient_pwa_medications_view`
- `patient_pwa_medical_documents_view`

Views should expose only Patient-PWA fields and exclude drafts, deleted records, unrelated files, and non-patient-facing internal notes.

## Integration checklist

1. Supply canonical patient identity and verified JWT mapping.
2. Supply exact patient, doctor, consultation, diagnosis, prescription, and medicine schemas.
3. Document status values, visibility, soft deletion, and timezone rules.
4. Document medicine frequency/duration and exact-time semantics.
5. Publish the stable `structured_data` JSON schema.
6. Confirm how `encounter_id` maps to consultations.
7. Supply the Storage signed-URL policy.
8. Implement parameterized reads in `PostgresMedikioskRepository`.
9. Apply only required `patient_pwa_*` migrations and enable RLS.
10. Test cross-patient access, source immutability, scheduling, Taken state, OCR corrections, and document access in staging.
11. Set `DATA_SOURCE=postgres` only after contract and authorization tests pass.

The shareable field checklist is in `docs/DOCTOR_HOSPITAL_PORTAL_REQUIRED_FIELDS.txt`.

Never write Patient-PWA actions into source prescriptions, diagnoses, medicines, consultations, doctors, patients, or original OCR results.
