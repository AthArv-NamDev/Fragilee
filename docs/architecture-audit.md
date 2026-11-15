# Architecture audit — Phase 1

Audit date: 2026-11-15. This is a repository/code audit plus the existing automated test evidence; no production Supabase records or live provider session were inspected. Secret values were not read.

## Stack and entry points

- Frontend: Next.js 16.4 App Router, React 19, TypeScript 5, Tailwind CSS 4, `motion` 14.9. `app/` contains the landing page, sign-in, new-analysis flow, history, analysis detail, guide and settings.
- Backend: FastAPI 0.143 / Pydantic 2.14, synchronous endpoints, NumPy/pandas, XGBoost and SHAP. Requirements are pinned in `backend/requirements.txt`.
- Auth and data: Supabase Auth in the browser/server helpers; FastAPI verifies user JWTs against Supabase JWKS. `SupabaseStore` calls PostgREST with the user's own bearer token and the public anon key. SQL enables RLS; tests use `MemoryStore`.
- Models: checked-in XGBoost JSON models plus `model_config.json` and SHA-256 verification. Training code and processed CSVs are in `backend/scripts/` and `backend/data/`.
- External retrieval: OpenAlex works API accessed through Python's `urllib`; a process-local six-hour cache. Historical cases are a curated JSON library.
- Persistence: Supabase `analyses` table stores input and immutable result snapshots as JSONB. SQL migrations define ownership, parent analysis linkage, payload-size checks and RLS.

## Feature status

| Area | Status | Evidence / issue |
|---|---|---|
| Landing, auth, history, analysis, settings routes | Working and tested | Next App Router source and previous successful production build; no browser E2E evidence. |
| Supabase login/session | Present; tests partially verify | Supabase SSR helpers and JWT validation. Live credentials/account not inspected in this audit. |
| Ownership boundary | Working and tested in unit/integration suite | API queries by authenticated `User`; SQL RLS and tests prohibit cross-user access. |
| Save/reopen/delete analysis | Working and tested | Version snapshots, pagination, ownership checks, RLS migration. No idempotency key for duplicate submissions. |
| Stage 1 historical model | Present, but not eligible as an individual startup probability | Model uses place and industry tags only; target `closed`; no explicit prediction horizon or censoring. Source/provenance for the 10,941-row stage-1 dataset is not recorded in `datasets.csv`. |
| Stage 2 historical model | Misleading if read as prospective startup risk | 922 US companies, `closed` versus `acquired`, only final-outcome companies; funding features and `relationships` can be snapshot/post-outcome. No prediction horizon; not representative of idea-stage ventures. |
| Calibration/bands | Present but unsuitable for the broad product claim | Platt scaling and score quantiles exist; time-based metric is reported, but the target/time-at-risk and feature timestamps do not establish prospective calibrated individual risk. |
| Explainability | Partially working | TreeSHAP describes model-feature contributions; contributions are historical associations, not causal exposures. Industry and location groups are model features, not startup vulnerabilities. |
| Founder profile extraction | Missing | Context fields are typed founder notes. There is no extraction, normalized business-model profile, correction step, field-level source spans or applicability engine. |
| Missing-information/completeness assessment | Missing | Required model request fields validate, but no completeness score/unknown factor state is produced. Stage 2 forces populated numeric values. |
| Contextual vulnerability/risk taxonomy | Missing | No versioned factor library, deterministic startup-specific assessment, dependency graph or scenario engine. |
| Research retrieval | Partially working | Real OpenAlex metadata and abstract index are retrieved; Market and Industry query expansions, dedup and filtering exist. It is lexical/metadata retrieval without embeddings or measured relevance benchmark. No official/regulator adapters. |
| Research result status | Misleading/inconsistent | Provider unavailable and successful search with no accepted source can converge to an empty result/note. API does not report distinct timeout/rate-limit/provider statuses. |
| Evidence traceability | Partially working | Citation metadata and an abstract excerpt are exposed; no persisted claim-to-passage record, retrieval timestamp per result, methodology/geography fields or human review. |
| Historical cases | Partially working | Curated cases have links and hand-written summaries. Retrieval accepts any exact tag OR two shared idea terms; no comparable class, differences, entity normalization, factual outcome status or per-case failure-cause evidence audit. |
| Recommendations/scenarios | Missing | No recommendation or sensitivity/scenario endpoint/UI. |
| Error/security controls | Partially working | Pydantic validation, body limit, per-process IP/user rate limiting, generic API exception response, no-store and security headers. Rate limits are not shared across workers; no request id surfaced as structured observability, retry/idempotency or provider metrics. |
| Visual design system | Implemented across main routes; browser review unverified | Shared tokens and layout now cover landing, analysis, case/research panels, saved analysis/history, sign-in, new analysis, guide and settings. The analysis tree uses actual contribution values. The visual reference and local source were reviewed statically; browser screenshot/E2E verification was blocked by local server bind permissions. |

## Critical consistency findings

1. The API still calculates, persists and exposes a calibrated `probability`, risk band and “similar startups failure rate” despite no explicit target horizon and material cohort/snapshot limitations. Product pages no longer display those values, but the backend still needs an explicit eligibility gate and contract migration plan. Current evidence does not pass the master prompt's eligibility gate for an individual startup probability.
2. Stage 1 SHAP groups are place and industry. They are not evidence of demand, competition, customer fit or operations. The Market/Industry research lens is separate and must remain so.
3. Stage 2 asks for all funding/relationship fields and turns them into a score, but input stage alone does not prove values were available at a common prospective prediction time. It is trained on US-only terminal outcomes.
4. Research is source-linked retrieval, not generated-answer RAG. There is no embedding store; generic “RAG” labels overstate its semantic capabilities.
5. Historical match rules and case content do not yet establish that a match is a direct business comparable or that the stated mechanism caused closure.

## Regression-sensitive boundaries

- Preserve auth redirects and API contracts until frontend/backend migration is coordinated.
- Preserve immutable analysis snapshots and legacy history reads. Do not rewrite saved model results in place.
- Model feature columns and hashes must stay aligned with checked-in JSON artifacts; do not edit scoring inputs without retraining and validation.
- Supabase RLS SQL is a security boundary; test with two users before changing storage/schema.
- Founder notes currently stay out of model scoring but selected topic terms are sent to OpenAlex for research. Keep this disclosure and do not send title/full notes.
- Dashboard mockup includes fictional sample cards and outcome percentages. Reuse its layout/tokens only; render actual saved rows and never copy sample records.

## Baseline verification

Before the current UI work, backend `pytest -q` ran with 161 passed; `npx tsc --noEmit`, `npm run lint` (with `backend/.venv` excluded), and `npm run build` passed. No browser-driven page flow was verified. Re-run these after the current UI work; this baseline does not verify those changes.
