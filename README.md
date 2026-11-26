# Fragilee

Fragilee is an evidence-aware startup analysis and decision-support app. It combines a historical statistical model with founder-submitted context, source-linked OpenAlex research, and a small curated library of historical company examples. These sources are presented separately; the current data do not support an individual startup failure forecast.

## Architecture

- **Frontend:** Next.js App Router, React, TypeScript, Tailwind CSS, and Motion (`app/`, `components/`, `lib/`).
- **Backend:** FastAPI endpoints and analysis logic (`backend/app/`).
- **Authentication and saved analyses:** Supabase Auth and user-scoped PostgREST storage with RLS (`lib/supabase/`, `backend/app/auth.py`, `backend/app/storage.py`, `backend/sql/`).
- **Models and data:** checked-in XGBoost JSON artifacts with hash verification (`backend/models/`); training and preprocessing scripts are in `backend/scripts/`.
- **Research and cases:** on-demand OpenAlex retrieval and curated case data (`backend/app/evidence.py`, `backend/app/cases.py`, `backend/data/cases.json`).

## Local development

Configure the public Supabase URL/key and API URL using [`frontend.env.example`](frontend.env.example) copied to `.env.local`. Configure the same Supabase project URL and public key for the backend using [`backend/backend.env.example`](backend/backend.env.example) copied to `backend/.env`. Do not put a service-role key in either file. Add the app's `/auth/callback` URL to Supabase's allowed redirect URLs for each environment.

Run the frontend from the repository root:

```bash
npm install
npm run dev
```

Run the API from `backend/` with its virtual environment and requirements installed:

```bash
.venv/bin/uvicorn app.main:app --reload --env-file .env
```

## Checks

From the repository root:

```bash
npm run lint
npx tsc --noEmit --incremental false
```

From `backend/`:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider
```

Use the in-app [Guide](/guide) to understand the model trace, startup breakpoints, unknown inputs, research evidence and historical cases. These are separate context layers; they do not predict an individual startup's outcome.

## Vercel deployment

The root [`vercel.json`](vercel.json) configures Vercel Services for the Next.js frontend and FastAPI backend. The API is routed through the same public origin; server-side frontend requests use a private backend service binding. Keep the Render deployment available until the Vercel deployment has passed the sign-in, saved-analysis, research, and evidence workflows.

Set these Vercel Production environment variables using values from the currently selected Supabase project:

- `NEXT_PUBLIC_FRAGILEE_ENV=public`
- `NEXT_PUBLIC_FRAGILEE_SUPABASE_PROJECT_REF`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_FRAGILEE_API_SAME_ORIGIN=true`
- `ENV=prod`
- `FRAGILEE_ENV=public`
- `FRAGILEE_PUBLIC_SUPABASE_PROJECT_REF`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `STORAGE=supabase`
- `ALLOWED_ORIGINS=https://<your-production-vercel-domain>`

Do not set `NEXT_PUBLIC_API_URL` for this same-origin configuration. Vercel injects `FRAGILEE_BACKEND_SERVICE_URL` from the service binding. Never add a service-role key. Add the deployed domain's `/auth/callback` URL to Supabase's allowed redirect URLs. Keep Preview deployments protected and do not attach Production Supabase credentials to untrusted preview branches.
