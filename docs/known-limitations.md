# Known limitations and continuation checklist

This is the implementation boundary after Phase 1 audit. It should be updated as work is completed.

## User-facing / methodology limitations

- [ ] **Historical prediction eligibility:** API still calculates, persists and exposes calibrated scores and risk bands, although current product pages no longer display them. The target has no explicit time horizon, one Stage 2 cohort contains only closed or acquired companies, and feature observation times are not consistently known. Add a backend eligibility gate and coordinate a backward-compatible API/database migration before making a diagnostic the primary assessment. Do not mutate legacy snapshots.
- [ ] **Unknown information:** Required Stage 2 fields are forced to numbers/booleans. Add an explicit unknown state and assess data completeness separately; never treat an absent field as zero.
- [ ] **Business profile:** Build a schema-backed profile that separates founder statements, plans, derived interpretations, external facts and unknowns, preserving source spans and correction capability.
- [ ] **Contextual factors:** Add versioned factor definitions and applicability rules. Do not assign severity without required inputs or validated deterministic method.
- [ ] **Historical cases:** Normalize case attributes and outcomes, classify comparability, expose matched/mismatched dimensions, and audit each outcome/mechanism against its sources. Current exact-tag OR two-word rules can overstate similarity.
- [ ] **Research status and quality:** Keep OpenAlex-only, lexical/metadata research truthful. Distinguish provider unavailable, empty result, and filtered weak results. Build a reviewed query/source benchmark before claiming ranking quality. No embeddings, official source adapters, claim-level provenance, or research-to-risk evidence gate exist.
- [ ] **Recommendations and scenarios:** Not implemented. Add only after profile/factor schema and defensible mechanics are present; calculations must show units and assumptions.
- [ ] **Model/data cards:** Dataset provenance for Stage 1 is incomplete. Document source date, inclusion/outcome definitions, temporal availability and evaluation artifacts before claims of prospective risk.
- [ ] **Persistence provenance:** Existing JSON snapshots preserve what was displayed, but do not carry first-class model/data/rules/factor/retrieval versions or source passage records. Add only with a backward-compatible migration and preserve old rows.

## Reliability/security limitations

- Rate limits are process-local and therefore multiply across worker processes. Shared/global throttling is absent.
- No idempotency key protects the expensive create-analysis path from duplicate submissions.
- External OpenAlex retrieval is synchronous, urllib-based and process-cached. There is no structured provider status, retry/backoff policy or production latency/relevance monitoring.
- Database errors are safely generalized to the client, but logs currently include a truncated provider response body for PostgREST errors. Review before production and prefer sanitized status/code fields.
- No browser-driven end-to-end test or real signed-in Supabase session was run in the baseline audit. Automated suite uses in-memory storage and fake auth keys.
- No live database records, credentials, secrets or production deployment were inspected.

## Visual implementation

- `design/out/v2-*.html` and `design/out/v2-design-system.html` are the project's design source. The dashboard mockup includes sample rows, examples and historical percentages that must not be copied into live UI; bind real user data only.
- The user chose a two-way Light/Dark toggle only. The latest UI direction makes dark the default and retains the v2 typography/component conventions with charcoal, cream, coral and green accents.
- The ToneMaki reference was statically inspected. The UI uses lightweight CSS/SVG perspective and Motion; it does not load a WebGL engine. The workspace denied local frontend/backend server binding, and browser access was unavailable in this chat, so there are no screenshot, hover/touch or live-auth results.
- The dashboard/history search and stage filters operate on the latest API page (up to 50 rows); they do not query/paginate the full account history. Case filters operate on the currently returned curated set.

## Auth setup still needed for a deployment

- Configure the Supabase Auth Redirect URLs allowlist with the local and production `/auth/callback` URLs. This Supabase dashboard setting could not be changed from the repository.
- A local `.env.local` was created only in the working checkout from the backend's existing public Auth settings; it is ignored and excluded from the deliverable. Use `frontend.env.example` when applying the ZIP.
- Signup, PKCE confirmation, returning-user sign-in, refresh, logout, and expiry routes were verified by code/build inspection only; no live test user/session was exercised.

## Phases not completed

Phase 1 audit documents exist. A first UI integration of the v2 system and data-bound dashboard is implemented. Phases 2–10 in `Fragilee_Master_Codex_Prompt_V2.md` remain incomplete except for prior research retrieval, model explanation, auth and persistence work described in `architecture-audit.md`. Continue in dependency order: model eligibility/data cards → profile/factor schema → assessment design → cases/research evaluation → recommendation/dependency/scenario support → UI → migration/security regression.
