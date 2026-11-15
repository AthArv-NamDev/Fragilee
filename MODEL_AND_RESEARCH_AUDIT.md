# Fragilee model and research audit

## Current data flow

1. `NewAnalysisFlow` collects location, selected industry tags and optional startup notes. Notes are stored as context and do not enter the prediction feature matrix.
2. `/v1/analyses` validates the selected stage, calls the matching `scoring.predict_stage*` function, and saves the inputs and result snapshot. Supabase row-level security scopes saved records to the signed-in user.
3. `features.py` builds the same feature columns used in training. `ModelStore` checks the model file hash, loads XGBoost and TreeSHAP, and `scoring.py` calibrates the model output and groups TreeSHAP contributions.
4. Historical failure cases are looked up from the curated, source-linked library. Research candidates are fetched separately from OpenAlex when a person opens a tree factor.

## What the trained models can support

- Stage 1 predicts the historical `closed` label using location and industry tags plus the number of tags. The checked-in validation report records 10,941 rows, cross-validation AUC 0.671, held-out AUC 0.676 (95% bootstrap interval 0.654–0.696), and a time-based AUC of 0.660. This is modest separation, not an individual-startup forecast.
- Stage 2 uses 42 features across funding, relationships/traction, industry category and state. The checked-in report records 922 rows, cross-validation AUC 0.815, held-out AUC 0.786 (95% bootstrap interval 0.711–0.854), and a time-based AUC of 0.819. The `relationships` field may reflect company success observed after the fact; the existing limitation is kept visible.
- The model does not receive product, customer, revenue model, startup stage, team size or founder worries. Those notes guide research and historical-case matching only.
- The historical labels and feature timestamps are not enough to verify that every factor was observed before closure/acquisition. Correlated funding and stage inputs may share TreeSHAP attribution. The project has no feature-level causal study.
- Stage 1 has no direct market-demand or competition feature. Its former `Market` branch was only industry tags/categories, so it is now named `Industry`. Market research is a separate evidence lens; it is not represented as a model score.
- Branch-level Low/Medium/High/Critical thresholds were heuristic, so they have been removed. Branches expose signed SHAP contributions instead. The prediction-level bands remain because they come from the calibrated model's stored cutoffs and observed outcome groups.
- The API no longer emits an unvalidated confidence category. It returns `confidence: null`; input-range caveats remain as explicit notes.
- Stage 1 location/tags are validated against the saved model's supported options. Stage 2 numeric inputs are required and range-checked; the state is optional and maps to the existing `OTHER` bucket. Missing numeric values are not silently imputed at request time.

## Research retrieval

- Market and Industry use separate query expansions. Market emphasizes demand, competition, acquisition, retention and differentiation. Industry emphasizes inventory, unsold stock, trend volatility, apparel returns, sizing, supply chains and margins. Other selected tree factors have their own funding, traction or location terms.
- Queries include selected industry, available place and up to 18 extracted words from concept, vision, customer and revenue-model notes. The startup title and full note text are excluded. The idea form discloses that extracted topic words go to OpenAlex when research is opened.
- OpenAlex candidates are deduplicated by DOI (or normalized title), filtered to current/past publication dates, articles with abstracts, and journal sources OpenAlex lists in DOAJ or CWTS Core. Source-list status is only a screening signal.
- Candidates need both industry and selected-factor evidence in their metadata/abstract. A direct excerpt contains both in one non-negated abstract sentence; a contextual excerpt matches the field and factor in separate passages. The API returns at most eight so the interface can show an initial three and let the user expand.
- Existing infrastructure has no embedding index. Retrieval therefore uses OpenAlex search plus title/abstract term and metadata reranking; it does not claim semantic-vector search. Weak matches are dropped. Excerpts are copied from the source abstract, not generated, and citations are never fabricated.
- A paper's abstract can still be incomplete or ambiguous. Open each source and inspect its methods and venue. Academic research is background evidence, separate from the historical company-failure examples and from the model's output.

## Changes made without retraining

The predictor, feature matrix, calibration, cutoffs and model files were not retrained or reweighted. The changes correct branch labels, remove unsupported branch severity/confidence labels, expose the actual signed TreeSHAP log-odds contribution, and improve the separate research retrieval path. Retraining or adding market scoring would require suitable time-stamped inputs and outcome data plus fresh held-out and temporal validation.
