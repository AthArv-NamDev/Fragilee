# Current data flow

Audit date: 2026-11-15. This records the code that exists before the next implementation phase.

## New analysis and score path

```text
NewAnalysisFlow (app/new/NewAnalysisFlow.tsx)
  ├─ fetches Stage 1 options from GET /v1/meta
  ├─ collects title, country, optional US state, 1–5 tags, founder notes/context
  └─ Stage 2 form collects category, state and required funding/relationship numbers
       ↓
Pydantic Stage1Request / Stage2Request (backend/app/schemas.py)
       ↓
POST /v1/analyses (backend/app/main.py)
  ├─ validates stage request again
  ├─ checks per-user analysis limit and parent ownership
  ├─ invokes scoring.predict_stage1/2
  ├─ attaches optional cohort context for Stage 1
  └─ persists request + returned result snapshot
       ↓
features.build_stage1/build_stage2 → JSON XGBoost + TreeSHAP (model_store.py)
       ↓
Platt calibration + quantile bands + grouped TreeSHAP contributions (scoring.py)
       ↓
AnalysisStore → Supabase PostgREST as the user's JWT; RLS scopes rows
       ↓
History summaries or GET /v1/analyses/{id} snapshot
       ↓
AnalysisView / PlexTree / CasesPanel render saved result, retrieved research and curated cases
```

## Inputs, normalization and scored fields

- Stage 1 requires an ISO-like 3-letter country code, requires a state for USA, and requires one to five tags from `/v1/meta`. Feature construction maps unsupported location categories to `OTHER`, encodes country/state/tag flags and tag count. The score uses only these columns.
- Stage 2 validates category, numeric bounds, boolean funding flags and state. It constructs funding, investor/relationship, category and state features. Missing numeric inputs are rejected by schema rather than represented as unknown.
- `Context` stores concept, vision, customer, revenue model, stage, team size and biggest worry. The schema and UI explicitly say context does not affect the score. Context is available to research query construction and case matching.
- There is no profile extraction or normalization from free text. The user's words remain in `context`; there are no evidence spans or field provenance records.

## Model outputs

- `ModelStore` loads the checked-in XGBoost JSON artifact, verifies its SHA-256 against `model_config.json`, and calculates raw prediction plus TreeSHAP values under a lock.
- `scoring.py` Platt-calibrates the raw score, maps it to one of four stored quantile bands, computes observed band failure rate from training labels, and groups TreeSHAP contributions into Location, Industry, Funding and Traction.
- Stage 1 model metadata: 10,941 rows, target `closed`, held-out AUC 0.676 (95% bootstrap interval 0.654–0.696), time-check AUC 0.660. Source/census date and outcome horizon are not represented in the checked-in dataset card.
- Stage 2 model metadata: 922 US rows, target `closed=1` versus `acquired=0`, held-out AUC 0.786 (95% interval 0.711–0.854), time-check AUC 0.819. Terminal-outcome-only cohort and relationship snapshot leakage are acknowledged in the data notes.
- These outputs do not constitute a validated prospective startup-specific failure probability under the master prompt's eligibility requirements.

## Research path

1. Opening a factor requests `/v1/analyses/{id}/evidence?node=…&focus=…`.
2. API authenticates/authorizes via the saved row lookup. It reads industry/category and place from stored input, founder context and title from the row.
3. `evidence.build_queries` expands the selected Market/Industry/Funding/Traction/Location focus into at most two OpenAlex searches. It excludes startup title and sends up to 18 extracted topic words, not full notes.
4. `evidence.retrieve` requests recent OpenAlex works, widens the date window if needed, reconstructs abstract text, filters missing abstracts, irrelevant metadata/abstracts, non-journal or non-listed venues, future dates and duplicate DOI/title, then reranks by term/context/directness metadata.
5. The API returns up to eight source records. The client shows a compact initial subset and can reveal abstracts. Research is separate from model scoring.

## Historical cases

`analysis_cases` reads the user's saved input and context and passes tags plus topic text to `backend/app/cases.py`. Cases are stored in `backend/data/cases.json`, ranked by exact tag and overlap with idea words; the endpoint returns up to five. There is no external fetch at request time. Case result text is hand-curated with links, not generated from a claim-level evidence store.

## Persistence and auth

- Browser/server Supabase helpers manage login session and obtain claims. Backend accepts a bearer access token, validates signature with cached JWKS (or legacy HS256 only when explicitly configured), issuer, audience, expiry and role.
- `SupabaseStore` forwards the user's JWT and anon project key to PostgREST. It does not use a service-role key. RLS policies scope select/insert/delete; no update policy exists.
- Analyses are immutable snapshots with optional self-referential `parent_id`, JSON input/result and JSONB founder context. History list is paged; opening an old row renders its stored snapshot.

## Missing stages from the requested product flow

No current implementation performs normalized business-profile extraction, factor applicability, an unknown/completeness state, a startup-specific vulnerability assessment, evidence-to-risk claim validation, multidimensional case comparability, dependency graph, action recommendations, sensitivity scenarios, or persisted model/rules/factor provenance. These are not implicit in the model tree or in OpenAlex retrieval.
