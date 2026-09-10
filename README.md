# Patient PWA

A mobile-first, accessible patient application for viewing Medikiosk-created clinical records, following a medication reminder plan, recording Taken status, and completing optional Gemini-powered follow-up check-ins. The visible name is configurable; `Patient Care` is only the development placeholder.

## Architecture and boundaries

`frontend` (React/Vite/Tailwind/PWA) calls one FastAPI backend. The backend reads clinical data through a replaceable `MedikioskRepository`; mock and future Supabase adapters share the same interface. Scheduling and follow-up logic operate on internal domain models. SQLite stores mock-development Patient-PWA actions durably. The supplied PostgreSQL migration contains only `patient_pwa_*` tables.

Gemini is an optional server-side service. Dashboard, records, medicine scheduling, calendar, and Taken tracking do not depend on it. The assistant receives only diagnosis, limited check-in context, and the current conversation. No assistant answers are sent to doctors. Follow-ups are deterministically due 1, 3, and 7 days after a visit by default; this policy is configurable in `followup_scheduling.py` and never decided by Gemini.

## Structure

```text
backend/
  app/                   FastAPI routes, domain, identity, repositories, services, owned-data store
  migrations/            Patient-PWA-owned PostgreSQL migration only
  tests/                 Backend unit/API tests
  .env.example
frontend/
  public/                 Neutral PWA icon
  src/                    API client, accessible components, five pages
  .env.example
docs/
  MEDIKIOSK_DATABASE_INTEGRATION.md
```

## Run locally (mock mode)

Requires Python 3.11+ and Node 20+.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

In another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open `http://localhost:5173`. The API docs are at `http://localhost:8000/api/docs`. Mock Taken state persists in `backend/patient_pwa.db`. The synthetic schedule begins on 10 September 2026; use that date in Calendar when demonstrating outside its active range.

## Environment

Backend: `DATA_SOURCE`, `DATABASE_URL`, `PATIENT_PWA_DATABASE_URL`, `MOCK_PATIENT_ID`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `FRONTEND_ORIGIN`, and VAPID private/public/subject variables. Frontend: `VITE_API_BASE_URL`, `VITE_APP_NAME`, and public `VITE_VAPID_PUBLIC_KEY`. Secrets never use the `VITE_` prefix.

Without `GEMINI_API_KEY`, starting a check-in returns a safe 503 while all other features work. Push needs a VAPID keypair plus a production reminder worker that selects due schedules and calls Web Push. Permission is requested only when the patient chooses “Turn on reminders.” API responses use `no-store`; the PWA service worker uses network-only behavior for `/api`.

## Tests and builds

```powershell
cd backend
python -m pytest
python -m compileall app
cd ..\frontend
npm run typecheck
npm run test
npm run build
```

Tests do not call Gemini. They cover repository normalization, schedule frequency/duration/exact times, persistent and idempotent Taken behavior, calendar reflection, identity/session isolation, follow-up context/storage/completion, and Gemini missing-key/malformed/timeout handling.

## Real Supabase mode

See [the database integration contract](docs/MEDIKIOSK_DATABASE_INTEGRATION.md). The real adapter is intentionally fail-closed until the schema is supplied. Implement mappings there, add verified Supabase identity, implement a Postgres owned-data store, apply only the supplied owned-table migration, then set `DATA_SOURCE=postgres`. Do not expose the database service key to the browser.

## Known limitations

- Development identity is a clearly isolated mock header/provider, not production authentication.
- Shared Medikiosk mapping and the Postgres owned-data store await the actual schema and access policy.
- Push subscription capture and failure UX are implemented; scheduled delivery requires deployment of a worker/cron job and VAPID credentials. Expired endpoints should be deleted when Web Push returns 404/410.
- The manifest uses a neutral SVG placeholder. Supply branded 192px and 512px PNG icons when the final name/identity is chosen.
- PWA installability and notification behavior require HTTPS outside localhost and vary by browser, especially iOS.
