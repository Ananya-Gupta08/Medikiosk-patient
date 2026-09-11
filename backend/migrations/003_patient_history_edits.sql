-- Patient corrections are stored separately; original OCR documents stay immutable.
CREATE TABLE IF NOT EXISTS patient_pwa_history_edits (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id text NOT NULL,
  medical_document_id uuid NOT NULL,
  edited_history text NOT NULL CHECK (char_length(edited_history) BETWEEN 1 AND 10000),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(patient_id, medical_document_id)
);
CREATE INDEX IF NOT EXISTS patient_pwa_history_edits_patient_idx
  ON patient_pwa_history_edits(patient_id);

