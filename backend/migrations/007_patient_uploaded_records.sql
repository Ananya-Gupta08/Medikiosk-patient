-- Patient-owned uploads and AI extraction. Medikiosk clinical documents remain unchanged.
CREATE TABLE IF NOT EXISTS patient_pwa_uploaded_records (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 patient_id text NOT NULL,
 file_name text NOT NULL,
 mime_type text NOT NULL,
 file_size integer NOT NULL CHECK (file_size > 0 AND file_size <= 4194304),
 file_data bytea NOT NULL,
 extraction_status text NOT NULL CHECK (extraction_status IN ('pending','complete','failed')) DEFAULT 'pending',
 extracted_data jsonb,
 patient_summary text,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS patient_pwa_uploaded_records_patient_idx
 ON patient_pwa_uploaded_records(patient_id, created_at DESC);
