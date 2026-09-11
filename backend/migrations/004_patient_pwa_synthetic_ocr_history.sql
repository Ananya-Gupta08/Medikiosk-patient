-- Synthetic OCR-like source for mock identity only; no clinical tables are changed.
CREATE TABLE IF NOT EXISTS patient_pwa_demo_ocr_documents (
  id uuid PRIMARY KEY,
  patient_id text NOT NULL,
  document_type text NOT NULL,
  clinical_document_date date NOT NULL,
  extraction_timestamp timestamptz NOT NULL,
  confidence_score double precision NOT NULL,
  structured_data jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(patient_id,id)
);
INSERT INTO patient_pwa_demo_ocr_documents
  (id,patient_id,document_type,clinical_document_date,extraction_timestamp,confidence_score,structured_data)
VALUES ('40000000-0000-4000-8000-000000000001','TEST_PATIENT_001','discharge_summary','2026-09-10',
  '2026-09-10T12:00:00+05:30',0.96,
  '{"clinical_notes":"Patient reviewed after prostate surgery. Recovery was stable at discharge.","findings":"Mild post-operative pain noted.","final_diagnosis":"Post-operative prostate surgery","discharge_advice":"Rest, stay hydrated, and follow the treating doctor’s instructions."}'::jsonb)
ON CONFLICT (id) DO NOTHING;
