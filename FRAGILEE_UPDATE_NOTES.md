# Fragilee update

## What changed

- Added a complete two-tone homepage hero with desktop/mobile navigation, primary and secondary CTAs, a keyboard-selectable pointer-responsive CSS/SVG perspective scene tied to actual model/evidence categories, and an animated strip of real product capabilities.
- Set dark as the default and kept the persistent Light/Dark toggle. Core foreground/background pairs are automatically checked against WCAG AA in both modes; the contrast test caught and fixed the too-light light-theme coral and destructive action contrast.
- Added a real protected `/dashboard` route that loads the signed-in user's saved analyses. Removed the old `/dashboard` → `/history` redirect. Returning sign-in defaults to `/dashboard`; first sign-up defaults to `/new`; explicit validated return destinations are preserved.
- Added a Supabase PKCE email-confirmation callback route. The frontend public Supabase config is documented in `frontend.env.example`; this local checkout also has an ignored `.env.local` derived from the backend's existing public Auth configuration.
- Redesigned results around startup identity, an actual model-contribution map and the existing interactive factor tree. Research and company cases remain separate; the returned case set now has search, reason filters, shared-reported-theme navigation links and source trails.
- Applied the design across history, new analysis, guide, settings, sign-in, signed-in navigation, loading failures and sign out. Existing Motion is reused; no dependency was added.
- Kept risk calculations, model weights, persistence data, company matching logic and API contracts unchanged. The case network links only curated shared reason labels; its copy says these do not establish cause or direct comparability.

## Remaining work

The full analytical-engine program described in the earlier master prompt is separate from this UI/auth phase and remains incomplete. In particular, the evidence does not yet support an individual startup probability; profile extraction, unknown-data handling, a validated startup-specific factor engine, audited comparable cases, claim-level evidence links, scenarios/recommendations and a provider-quality benchmark remain future work. See `docs/architecture-audit.md` and `docs/known-limitations.md` before extending the model or changing API/database contracts.

No live Supabase account records or production data were inspected, and no database migration was made. The dashboard mockup's fictional examples and metrics were not copied into user data. Supabase must allow `/auth/callback` for local and deployed origins; see `docs/auth-setup.md`.

## Apply this update

Download `fragilee-update.zip` to `~/Downloads`. In Terminal, go to the existing Fragilee project root (the folder containing `package.json` and `backend/`) and run:

```bash
unzip -o ~/Downloads/fragilee-update.zip -d .
cp frontend.env.example .env.local
```

Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` in `.env.local` to match the existing `backend/.env`; set the API URL if your backend is not on port 8000. Add `http://localhost:3000/auth/callback` to Supabase **Authentication → URL Configuration → Redirect URLs**. See `docs/auth-setup.md`. Then restart FastAPI and Next.js. The archive excludes secrets, local dependencies, virtual environments, build output, caches and OS metadata. The backend needs internet access for OpenAlex research.

## Verification

- `npx tsc --noEmit`: passed.
- `npm run lint`: passed.
- Backend `.venv/bin/pytest -q`: 162 passed (three dependency/test-key warnings), including WCAG AA checks for shared text and button token pairs in light and dark.
- `npx next build --webpack`: passed. Next.js printed a package-lock tracing-root warning because this project is nested beneath a parent folder with another `package-lock.json`.
- Starting the local frontend and backend was denied while binding local ports (`Operation not permitted`). Browser access is unavailable in this chat, so screenshots, the live authenticated Supabase flow, live OpenAlex response and device interaction were not verified. The production build is not a substitute for those checks; see `docs/ui-transformation.md`.
