-- Apply only to the Patient-PWA-owned schema. No Medikiosk clinical tables are created or changed.
CREATE TABLE IF NOT EXISTS patient_pwa_medication_logs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id text NOT NULL, schedule_id text NOT NULL,
 status text NOT NULL CHECK (status = 'taken'), completed_at timestamptz NOT NULL DEFAULT now(),
 created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(patient_id, schedule_id));
CREATE TABLE IF NOT EXISTS patient_pwa_reminder_preferences (
 patient_id text NOT NULL, times_per_day smallint NOT NULL CHECK(times_per_day BETWEEN 1 AND 12),
 reminder_times time[] NOT NULL, PRIMARY KEY(patient_id, times_per_day));
CREATE TABLE IF NOT EXISTS patient_pwa_push_subscriptions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id text NOT NULL, endpoint text NOT NULL UNIQUE,
 subscription_json jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS patient_pwa_followup_sessions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id text NOT NULL, diagnosis_value text NOT NULL,
 consultation_reference text NOT NULL, status text NOT NULL CHECK(status IN ('active','complete')),
 started_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS patient_pwa_followup_messages (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), session_id uuid NOT NULL REFERENCES patient_pwa_followup_sessions(id) ON DELETE CASCADE,
 role text NOT NULL CHECK(role IN ('patient','assistant')), message text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS patient_pwa_logs_patient_idx ON patient_pwa_medication_logs(patient_id);
CREATE INDEX IF NOT EXISTS patient_pwa_sessions_patient_idx ON patient_pwa_followup_sessions(patient_id);
