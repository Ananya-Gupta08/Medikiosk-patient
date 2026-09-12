-- Patient-PWA-owned appointment requests. No clinical source table is modified.
CREATE TABLE IF NOT EXISTS patient_pwa_appointment_requests (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 patient_id text NOT NULL,
 consultation_reference text NOT NULL,
 reason text NOT NULL,
 status text NOT NULL CHECK (status IN ('requested', 'acknowledged', 'scheduled', 'cancelled')) DEFAULT 'requested',
 requested_at timestamptz NOT NULL DEFAULT now(),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS patient_pwa_one_open_appointment_request
 ON patient_pwa_appointment_requests(patient_id, consultation_reference)
 WHERE status = 'requested';
CREATE INDEX IF NOT EXISTS patient_pwa_appointment_patient_idx
 ON patient_pwa_appointment_requests(patient_id, requested_at DESC);
