# Ultimate UI/auth implementation audit

Date: 2026-11-15

## Findings and root causes

| Severity | Finding | Root cause | Change / result |
|---|---|---|---|
| High | Returning sign-in and first sign-up shared `/new` as their default | A single `LANDING_AFTER_LOGIN` constant was used by both branches | Split defaults: returning sign-in → `/dashboard`; new sign-up → `/new`; validated protected return destinations still win |
| High | `/dashboard` was not a dashboard route | Next config redirected the URL to `/history` | Added an authenticated dashboard that reads the signed-in user's real saved analyses and a real empty/error state |
| High | Email-confirmed registration had no app session handoff | Signup had no callback URL or PKCE exchange route | Added `/auth/callback` code exchange and safe return target; Supabase redirect allowlist must still be configured |
| Medium | The home page lacked a complete hero and meaningful product graphic | Existing `app/page.tsx` began with the lower-page statistics/tree content | Added editorial hero, CTAs, mobile nav, factual capability strip and keyboard/pointer-responsive model/evidence scene |
| Medium | Selected accents and destructive button foreground combinations were not checked systematically | Color combinations were hand-authored without contrast regression coverage | Added contrast tests; they caught light coral and delete-button misses and verify core pairs in both themes |
| Medium | Case comparison had no direct visual exploration between returned companies | Case card display exposed sources and reasons but no set-level index | Added case navigation network; edges mean only shared curated reason labels and explicitly do not establish direct comparability/causation |
| Medium | The frontend local Supabase env was missing | Only backend Auth URL/public key were configured in `backend/.env` | Created ignored `.env.local` from that existing public configuration for this checkout; added a safe example for other checkouts |

## Scope preserved

No backend scoring code, model weights, historical datasets, API contracts, auth authorization checks, database schema, RLS policy or company matching algorithm were changed. Home stats remain data-backed; analysis and case visuals use actual saved/API values and do not include demo companies or made-up scores.

## Verification

- TypeScript: passed after build regenerated Next route types.
- ESLint: passed.
- Backend suite: 162 passed, including the new contrast test (three dependency/test-key warnings).
- Next production Webpack build: passed and includes `/dashboard` and `/auth/callback`.
- Local runtime attempt: FastAPI and Next.js both failed to bind a port with `Operation not permitted`. The computer-use browser inventory was empty and reported browser access unavailable for this chat. Therefore actual browser, viewport, auth, form and live research acceptance checks remain unverified. The production build is not described as runtime verification.

## Remaining external/runtime steps

1. Apply the update ZIP, copy `frontend.env.example` to `.env.local`, and set the same public Supabase URL/key as the existing backend.
2. Add local and production `/auth/callback` URLs to Supabase Auth Redirect URLs.
3. Run frontend/backend where local port binding is allowed; inspect desktop/tablet/mobile and execute sign-up confirmation, returning sign-in, page refresh, logout, expiry, protected route, data ownership, analysis submit, research, cases and keyboard/touch flows with disposable test data.

