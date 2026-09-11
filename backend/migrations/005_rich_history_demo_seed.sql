-- Rich synthetic history fixtures for UI/edit testing. No real clinical rows are touched.
BEGIN;
INSERT INTO patient_pwa_demo_ocr_documents
  (id,patient_id,document_type,clinical_document_date,extraction_timestamp,confidence_score,structured_data)
VALUES
  ('40000000-0000-4000-8000-000000000002','TEST_PATIENT_001','operative_summary','2026-09-08','2026-09-08T16:30:00+05:30',0.94,
   '{"clinical_notes":"Synthetic operative summary for demonstration. The patient underwent the planned prostate procedure and was observed after surgery. Recovery in the observation area was stable.","findings":"Post-operative observations were within the expected range. Mild lower abdominal discomfort was recorded. No acute breathing difficulty was documented.","final_diagnosis":"Post-operative prostate surgery recovery.","impression":"Stable immediate recovery with routine follow-up advised.","extra_notes":"The patient was able to drink fluids and walk with assistance before discharge from observation.","remarks":"This is synthetic test information and not a real medical record."}'::jsonb),
  ('40000000-0000-4000-8000-000000000003','TEST_PATIENT_001','laboratory_report','2026-09-09','2026-09-09T11:15:00+05:30',0.91,
   '{"clinical_notes":"Synthetic follow-up laboratory report captured through OCR for history-screen testing.","findings":"Haemoglobin: 13.4 g/dL. White blood cell count: 7,600 /µL. Platelet count: 245,000 /µL. Creatinine: 0.9 mg/dL.","impression":"Values recorded in this synthetic report were marked within the stated reference ranges.","extra_notes":"The OCR engine marked the platelet value for visual confirmation because the source scan was slightly blurred.","remarks":"Demonstration data only."}'::jsonb),
  ('40000000-0000-4000-8000-000000000004','TEST_PATIENT_001','follow_up_note','2026-09-11','2026-09-11T10:45:00+05:30',0.97,
   '{"clinical_notes":"Synthetic follow-up note. The patient reported that pain had improved since discharge and was able to eat and drink normally.","findings":"Mild pain on movement. No reported fever or chills. No reported difficulty passing urine.","diagnosis":"Routine post-operative recovery after prostate surgery.","impression":"Symptoms described in the synthetic note were improving.","extra_notes":"Continue following the treating doctor’s original discharge instructions.","remarks":"Next routine review date was recorded as 17 September 2026."}'::jsonb)
ON CONFLICT (id) DO NOTHING;

INSERT INTO patient_pwa_history_edits
  (id,patient_id,medical_document_id,edited_history,created_at,updated_at)
VALUES
  ('50000000-0000-4000-8000-000000000001','TEST_PATIENT_001','40000000-0000-4000-8000-000000000002',
   E'Clinical Notes:\nI felt comfortable after the procedure and was able to drink water normally.\n\nFindings:\nI had mild lower abdominal discomfort, mainly while standing up.\n\nFinal Diagnosis:\nPost-operative prostate surgery recovery.\n\nAdditional Information:\nI walked without assistance before leaving the hospital.\n\nPatient Note:\nThis correction was added as synthetic test data for the editable-history feature.',
   '2026-09-11T12:00:00+05:30','2026-09-11T12:00:00+05:30')
ON CONFLICT (patient_id,medical_document_id) DO NOTHING;
COMMIT;
