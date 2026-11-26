# Fragilee

Fragilee helps founders examine startup risks using founder-provided information, historical model context, research sources, and startup case studies. It does not predict whether an individual startup will fail.

## Run locally

1. Copy `frontend.env.example` to `.env.local` and add your Supabase URL and public key.
2. Copy `backend/backend.env.example` to `backend/.env` and configure the same Supabase project and public key.
3. Install the frontend with `npm ci` and run `npm run dev`.
4. In `backend/`, install `requirements.txt`, then run `.venv/bin/uvicorn app.main:app --reload --env-file .env`.

Never use a Supabase service-role key in the frontend or ordinary backend requests.

## Deploy

The GitHub repository is connected to Vercel. **`main` is the production branch**: push a change to `main` and Vercel builds and deploys it. `vercel.json` routes the frontend and API through one site.

Set the required public Supabase URL/key and deployment-mode variables in the Vercel Production environment. Keep preview deployments separate from production credentials. Add the deployed site's `/auth/callback` URL to Supabase's allowed redirect URLs.

## Help

Open the in-app [Guide](/guide) for explanations of startup breakpoints, research, historical cases, and model context.
