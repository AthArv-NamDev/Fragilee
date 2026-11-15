# Fragilee premium UI transformation

Date: 2026-11-15

## Design direction

ToneMaki's live site uses oversized display headlines, strong dark/light contrast, colorful visual accents, a sequence of editorial story sections and a prominent Spline 3D scene. The page source describes deferring the Spline viewer until it enters the viewport and removing it from display after the hero scrolls away. Fragilee adapts the visual hierarchy and layered dimensional treatment, without using ToneMaki branding, copy or assets. This was a static reference inspection; hover timing and the live responsive states were not measured.

The Fragilee palette uses its own charcoal/cream surfaces, coral emphasis and green action color. The existing Archivo Black / Inter typography, Tailwind 4 tokens, Motion library and light/dark preference are reused. Dark is the initial mode; the header toggle switches to light and persists the choice.

## Changes

- `app/globals.css`: shared brand accents, layered card surfaces, dotted analytical canvas, hover lift, and reduced-motion rules. WCAG checks cover foreground/body text, muted text, accent, selected controls, primary button and destructive confirmation combinations in both themes.
- `components/landing/FragileeHeroScene.tsx` and `app/page.tsx`: complete two-tone first-screen hero with meaningful navigation, primary/secondary CTA, animated pointer-responsive 3D CSS/SVG factor-and-evidence scene, keyboard-selectable nodes with accurate descriptions, and a factual capability strip. It is a lightweight perspective composition, not WebGL.
- `components/Nav.tsx`: working desktop section navigation, mobile disclosure menu, and account-aware dashboard/sign-in action.
- `components/AnalysisView.tsx`: editorial analysis overview, actual model-branch contribution visualization, explicit model limitations, startup identity, and clear navigation into the model trace and historical cases.
- `components/tree/PlexTree.tsx`: depth-lit spherical nodes, gentle pointer parallax, existing keyboard/pointer factor selection and 650 ms tree glide, relative factor contribution display, compact detail panel, and independently fetched Market/Industry evidence. Pointer motion and tree glide respect reduced motion.
- `components/CasesPanel.tsx`: source-linked research and curated company cases remain distinct; case text search, reported-theme filters, expandable source trails, a case network linked only by shared curated reason labels, and staggered once-only entrances.
- `components/AnalysisList.tsx`: data-backed loaded counts, name search, level filters and responsive saved-analysis cards. The count label states that it covers the latest loaded page.
- `app/history/page.tsx`, `app/new/NewAnalysisFlow.tsx`, `app/guide/page.tsx`, `app/settings/page.tsx`, `components/AppShell.tsx`, `components/AppNav.tsx`: extend the shared visual treatment, responsive navigation, and restrained interaction styling across the signed-in workflow.
- `app/analysis/[id]/page.tsx`: styled API-unavailable state.
- `lib/theme.ts`: use dark by default while preserving the two-option Light/Dark toggle.
- `app/dashboard/page.tsx`: protected dashboard renders the authenticated user's real saved analyses with real empty/loading-error states; `/dashboard` is no longer redirected to `/history`.
- `components/LoginForm.tsx`, `app/auth/callback/route.ts`, `lib/redirect.ts`, `lib/supabase/proxy.ts`: returning sign-ins default to `/dashboard`, new sign-ups to `/new`, PKCE confirmation exchanges server-side, and safe explicit return destinations remain supported. Existing users returned by an obfuscated signup response receive non-enumerating generic copy.
- `frontend.env.example` and `docs/auth-setup.md`: frontend Supabase public config and the required callback allowlist are documented. An ignored local `.env.local` was created in this checkout from the existing backend public Auth settings; it is excluded from the update ZIP.

## Product integrity

No model weights, risk calculations, API contracts, datasets, company matching rules, authentication logic or persisted analysis records were changed for this UI work. The branch map scales nodes from each existing absolute SHAP contribution and colors its direction; labels describe model attribution and explicitly avoid implying causes or individual forecasts. Research continues to load through the existing evidence API. Case search/filtering only operates on the API's returned curated records.

The visualization is a lightweight SVG/CSS dimensional treatment, not a WebGL scene. It remains usable without pointer motion. No new dependencies or illustrative company records were added.

## Verification and limits

- `npx tsc --noEmit`: passed.
- `npm run lint`: passed.
- `backend/.venv/bin/pytest -q`: 162 passed (three existing dependency/test-key warnings), including automated WCAG AA contrast checks for core controls in both themes.
- `npx next build --webpack`: passed. Next.js warns that a parent `package-lock.json` makes its inferred tracing root `/Users/atharvnamdev`; no config change was made for this visual task.
- Attempting to start FastAPI and Next.js failed with `Operation not permitted` while binding local ports. The computer-use browser inventory also reported no browser access for this chat. No desktop/tablet/mobile screenshots, real authenticated flow, or live external research response were visually verified. This means the requested running-app/browser verification is not complete.

## Remaining live checks

- Add `http://localhost:3000/auth/callback` (and the production app's exact callback URL) to Supabase Auth Redirect URLs.
- Start the app where local server binding is permitted and verify desktop/tablet/mobile layouts, keyboard and touch node selection, sign-up confirmation, returning-user sign-in, refresh, logout, expired-session redirect and actual Supabase-owned data.
- Verify the hero's CSS perspective on real devices; it has no WebGL renderer or GPU-dependent path.

