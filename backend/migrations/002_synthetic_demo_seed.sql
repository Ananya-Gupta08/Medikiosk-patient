-- Synthetic Patient PWA demo data only. Additive and safe to rerun.
-- This does not create, update, or delete Medikiosk-owned clinical records.
BEGIN;

INSERT INTO patient_pwa_reminder_preferences (patient_id, times_per_day, reminder_times)
VALUES
  ('TEST_PATIENT_001', 1, ARRAY['09:00'::time]),
  ('TEST_PATIENT_001', 3, ARRAY['09:00'::time, '14:00'::time, '21:00'::time])
ON CONFLICT (patient_id, times_per_day) DO NOTHING;

INSERT INTO patient_pwa_medication_logs
  (id, patient_id, schedule_id, status, completed_at, created_at)
VALUES
  ('10000000-0000-4000-8000-000000000001', 'TEST_PATIENT_001',
   'MED_001:2026-09-10T09:00:00', 'taken', '2026-09-10T09:08:00+05:30', '2026-09-10T09:08:00+05:30')
ON CONFLICT (patient_id, schedule_id) DO NOTHING;

INSERT INTO patient_pwa_followup_sessions
  (id, patient_id, diagnosis_value, consultation_reference, status, started_at, completed_at, created_at)
VALUES
  ('20000000-0000-4000-8000-000000000001', 'TEST_PATIENT_001',
   'Post-operative prostate surgery', 'CONSULTATION_001', 'complete',
   '2026-09-11T10:00:00+05:30', '2026-09-11T10:04:00+05:30', '2026-09-11T10:00:00+05:30')
ON CONFLICT (id) DO NOTHING;

INSERT INTO patient_pwa_followup_messages (id, session_id, role, message, created_at)
VALUES
  ('30000000-0000-4000-8000-000000000001', '20000000-0000-4000-8000-000000000001', 'assistant', 'How are you feeling today?', '2026-09-11T10:00:00+05:30'),
  ('30000000-0000-4000-8000-000000000002', '20000000-0000-4000-8000-000000000001', 'patient', 'I feel better, but I still have mild pain.', '2026-09-11T10:02:00+05:30'),
  ('30000000-0000-4000-8000-000000000003', '20000000-0000-4000-8000-000000000001', 'assistant', 'Thank you. Your check-in is complete for today.', '2026-09-11T10:04:00+05:30')
ON CONFLICT (id) DO NOTHING;

COMMIT;
