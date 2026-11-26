"""Fragilee API. Module 2: prediction + risk tree. Module 3: login, saved analyses, rate limits."""
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from itertools import combinations
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import cases, cohort, evidence, evidence_comparison, scoring, settings
from .auth import User, ip_limit, predict_user, read_user
from .diagnostics import evaluate_profile
from .evidence_contract import (
    ContradictionAssessment, ContradictionCompareRequest, ContradictionDetectRequest, ContradictionReviewRequest, ContradictionSubmission,
    EvidenceAssociation, EvidenceAssociationSubmission, EvidenceAssociationValidationError,
    EvidenceReviewRequest, find_snapshot_source, validate_evidence_association,
)
from .model_store import ModelStore
from .schemas import (AnalysisCreate, AnalysisOut, AnalysisSummary, CasesResponse, EvidenceResponse,
                      EvidenceSnapshotHistory, EvidenceSnapshotSummary, PredictionResponse, StartupProfile,
                      Stage1Request, Stage2Request)
from .storage import StorageDenied, StorageError, make_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fragilee")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()                                    # refuse to start with an unsafe setup
    app.state.store = ModelStore(settings.MODELS_DIR)      # fails loudly if a model file was changed
    app.state.analyses = make_store()
    app.state.cases = cases.load(settings.CASES_JSON)
    app.state.cohort = cohort.load(settings.COHORT_CSV, app.state.store.config["stages"]["stage1"]["countries"]) if "stage1" in app.state.store.stages else None
    environment = settings.FRAGILEE_ENV if settings.FRAGILEE_ENV != "development" else settings.ENV
    log.info("models loaded: %s | storage: %s | environment: %s | Supabase project: %s",
             ", ".join(app.state.store.stages), settings.STORAGE, environment,
             settings.supabase_project_ref())
    yield
    if hasattr(app.state.analyses, "close"):
        app.state.analyses.close()


app = FastAPI(
    title="Fragilee API", version="0.3.0", lifespan=lifespan,
    dependencies=[Depends(ip_limit)],                      # per-IP limit on every route, before login is checked
    docs_url="/docs" if settings.ENV == "dev" else None,   # docs pages are hidden in production
    redoc_url=None,
    openapi_url="/openapi.json" if settings.ENV == "dev" else None,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS, allow_methods=["GET", "POST", "DELETE"],
                   allow_headers=["Content-Type", "Authorization"])


@app.middleware("http")
async def guard(request: Request, call_next):
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > settings.MAX_BODY_BYTES:
        return JSONResponse({"detail": "Request too large"}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(scoring.InputError)
async def input_error(request: Request, exc: scoring.InputError):
    return JSONResponse({"detail": [{"loc": ["body", exc.field], "msg": exc.message}]}, status_code=422)


@app.exception_handler(scoring.StageUnavailable)
async def stage_unavailable(request: Request, exc: scoring.StageUnavailable):
    return JSONResponse({"detail": "This prediction stage is not available"}, status_code=503)


@app.exception_handler(StorageDenied)
async def storage_denied(request: Request, exc: StorageDenied):
    return JSONResponse({"detail": [{"loc": ["body", "parent_id"], "msg": "No analysis with that id in your account"}]},
                        status_code=422)


@app.exception_handler(StorageError)
async def storage_error(request: Request, exc: StorageError):
    return JSONResponse({"detail": "Saved analyses are temporarily unavailable"}, status_code=503)


@app.exception_handler(Exception)
async def unexpected(request: Request, exc: Exception):
    ref = uuid.uuid4().hex[:8]
    log.exception("unhandled error ref=%s path=%s", ref, request.url.path)   # details stay in the server log
    return JSONResponse({"detail": "Internal error", "ref": ref}, status_code=500)


# ---- public ------------------------------------------------------------------
@app.get("/health")
def health(request: Request):
    return {"status": "ok", "stages": {k: True for k in request.app.state.store.stages}}


@app.get("/v1/meta")
def get_meta(request: Request):
    """Dropdown options for the forms, plus how good each stage is."""
    return scoring.meta(request.app.state.store)


# ---- predictions (login required) --------------------------------------------
def _run(fn, request, body, stage):
    t0 = time.perf_counter()
    result = fn(request.app.state.store, body)
    index = request.app.state.cohort
    if stage == "stage1" and index is not None and settings.EXPOSE_COHORT:
        result["cohort"] = index.describe(body.country, body.state, body.tags)   # context only, never part of the score
    log.info("predict stage=%s band=%s ms=%.0f", stage, result["band"], (time.perf_counter() - t0) * 1000)
    return result


@app.post("/v1/predict/stage1", response_model=PredictionResponse)
def predict_stage1(body: Stage1Request, request: Request, user: User = Depends(predict_user)):
    return _run(scoring.predict_stage1, request, body, "stage1")


@app.post("/v1/predict/stage2", response_model=PredictionResponse)
def predict_stage2(body: Stage2Request, request: Request, user: User = Depends(predict_user)):
    return _run(scoring.predict_stage2, request, body, "stage2")


# ---- saved analyses (login required, each user sees only their own) ----------
def _validate_input(stage: str, data: dict):
    model = Stage1Request if stage == "stage1" else Stage2Request
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise HTTPException(422, detail=[
            {"loc": ["body", "input", *map(str, err["loc"])], "msg": err["msg"]}
            for err in e.errors(include_url=False, include_context=False)])


@app.post("/v1/analyses", response_model=AnalysisOut, status_code=201)
def create_analysis(body: AnalysisCreate, request: Request, user: User = Depends(predict_user)):
    """Run a prediction and save it to your history."""
    store = request.app.state.analyses
    req = _validate_input(body.stage, body.input)
    if settings.FREE_ANALYSIS_LIMIT and store.count(user) >= settings.FREE_ANALYSIS_LIMIT:
        raise HTTPException(403, f"You have reached the limit of {settings.FREE_ANALYSIS_LIMIT} saved analyses")
    if body.parent_id and store.get(user, body.parent_id) is None:
        raise HTTPException(422, detail=[{"loc": ["body", "parent_id"], "msg": "No analysis with that id in your account"}])
    fn = scoring.predict_stage1 if body.stage == "stage1" else scoring.predict_stage2
    result = _run(fn, request, req, body.stage)
    return store.create(user, {
        "title": body.title, "stage": body.stage, "parent_id": str(body.parent_id) if body.parent_id else None,
        "input": req.model_dump(), "result": result, "band": result["band"], "probability": result["probability"],
        # only sent when given, so saving still works on a database that has not been migrated yet
        **({"context": body.context.model_dump(mode="json", exclude_none=True)} if body.context else {})})


@app.get("/v1/analyses", response_model=list[AnalysisSummary])
def list_analyses(request: Request, user: User = Depends(read_user),
                  limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0, le=10000)):
    return request.app.state.analyses.list(user, limit, offset)


@app.get("/v1/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: uuid.UUID, request: Request, user: User = Depends(read_user)):
    row = request.app.state.analyses.get(user, analysis_id)
    if row is None:                                       # someone else's analysis looks exactly like a missing one
        raise HTTPException(404, "Analysis not found")
    # Recompute from a validated profile on reads; never mutate or persist the
    # derived result or the stored model snapshot. Keep report reads available
    # if an old/unsupported profile or a rule implementation fails validation.
    response = dict(row)
    context = row.get("context")
    profile_data = context.get("profile") if isinstance(context, dict) else None
    if profile_data is None:
        try:
            response["diagnostics"] = evaluate_profile(None).model_dump(mode="json")
            response["diagnostics_state"] = "no_profile"
        except Exception as exc:  # preserve legacy report availability even if the diagnostic module fails
            log.warning("diagnostics unavailable analysis_id=%s reason=%s", analysis_id, type(exc).__name__)
            response["diagnostics"] = None
            response["diagnostics_state"] = "unavailable"
        return response
    try:
        profile = StartupProfile.model_validate(profile_data)
        diagnostics = evaluate_profile(profile)
        response["diagnostics"] = diagnostics.model_dump(mode="json")
        response["diagnostics_state"] = "available"
    except ValidationError:
        log.warning("diagnostics unavailable analysis_id=%s reason=invalid_profile", analysis_id)
        response["diagnostics"] = None
        response["diagnostics_state"] = "unavailable"
    except Exception as exc:  # diagnostics must not take down the saved report
        log.warning("diagnostics unavailable analysis_id=%s reason=%s", analysis_id, type(exc).__name__)
        response["diagnostics"] = None
        response["diagnostics_state"] = "unavailable"
    return response


@app.delete("/v1/analyses", status_code=200)
def delete_all_analyses(request: Request, user: User = Depends(read_user)):
    """Settings > delete all my analyses."""
    return {"deleted": request.app.state.analyses.delete_all(user)}


@app.get("/v1/analyses/{analysis_id}/cases", response_model=CasesResponse)
def analysis_cases(analysis_id: uuid.UUID, request: Request, limit: int = Query(3, ge=1, le=5), user: User = Depends(read_user)):
    """Return sourced historical examples with their match type and limits."""
    row = request.app.state.analyses.get(user, analysis_id)
    if row is None:
        raise HTTPException(404, "Analysis not found")
    found, matched = cases.retrieve(request.app.state.cases, row["input"].get("tags", []), row.get("context"), limit)
    library_count = len(request.app.state.cases)
    library_status = "unavailable" if library_count == 0 else "limited"
    if library_status == "unavailable":
        note = "The historical case library is unavailable. This does not affect the saved analysis or research section."
    elif matched:
        note = "The curated library currently contains a small set of failure examples only. Summaries are based on linked reporting; they are not representative, causal proof, or predictions."
    else:
        note = "No case met the minimum profile-overlap criteria. The available failure-only library is small and incomplete; unrelated examples are not shown."
    return {"matched": matched, "cases": found, "note": note, "library_status": library_status, "library_count": library_count}


def _analysis_evidence(analysis_id: uuid.UUID, request: Request, node: str, focus: str | None, limit: int, user: User, refresh: bool = False):
    """Return a saved retrieval snapshot, or retrieve and append one on first view/explicit refresh."""
    row = request.app.state.analyses.get(user, analysis_id)
    if row is None:
        raise HTTPException(404, "Analysis not found")
    selected = focus or node
    store = request.app.state.analyses
    snapshot_reader = getattr(store, "get_latest_evidence_snapshot", None)
    snapshot_writer = getattr(store, "save_evidence_snapshot", None)
    if not refresh and snapshot_reader:
        try:
            saved = snapshot_reader(user, analysis_id, node, selected)
            if saved:
                payload = dict(saved["payload"])
                payload.update(snapshot_id=saved.get("id"), snapshot_saved=True,
                               snapshot_persistence_note="This is the preserved retrieval shown previously; refresh research to check for newer records.")
                return payload
        except Exception as error:
            log.warning("evidence snapshot read failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
    inputs = row["input"]
    tags = inputs.get("tags") or ([inputs["category"]] if inputs.get("category") else [])
    place = " ".join(value for value in (inputs.get("country"), inputs.get("state")) if value and value != "OTHER")
    try:
        retrieval = evidence.retrieve_detailed(
            tags, node, row.get("context") or {}, place,
            row.get("title"), focus, limit,
        )
    except Exception as error:
        log.warning("research retrieval failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        retrieval = {"sources": [], "state": "provider_error", "queries_attempted": 0, "query_results": [],
                     "records_retrieved": 0, "candidates_filtered": 0, "weak_candidates": 0, "retrieved_at": date.today().isoformat()}
    found = retrieval["sources"]
    explanations = {
        "relevant_results": "Relevant records passed the deterministic profile, factor, abstract and source-screening checks.",
        "partial": "Some records passed the checks, but one or more retrieval requests failed; results may be incomplete.",
        "no_results": "OpenAlex returned no records for the bounded searches. This does not mean relevant research does not exist.",
        "filtered_out": "Records were retrieved, but none met the current source and relevance filters.",
        "weak_relevance": "Records were retrieved, but none had enough profile and factor relevance to display.",
        "provider_unavailable": "OpenAlex could not be reached after a bounded retry. No conclusion about the availability of research can be drawn.",
        "provider_timeout": "OpenAlex timed out after a bounded retry. No conclusion about the availability of research can be drawn.",
        "rate_limited": "OpenAlex rate limited the bounded requests after a retry. No conclusion about the availability of research can be drawn.",
        "provider_error": "OpenAlex returned an error or invalid response. The saved analysis remains available.",
        "insufficient_query_context": "The saved analysis does not contain enough industry context to construct a research query.",
    }
    note = ("Queries use submitted industry, geography, structured profile and selected founder notes; the startup name is excluded. "
            + explanations.get(retrieval["state"], "Research retrieval completed.")
            + " Ranking is a deterministic retrieval aid, not evidence strength or a startup outcome probability. Source abstracts and metadata are not a full-text review.")
    response = {"provider": "OpenAlex", "node": node, "sources": found, "note": note, **{
        "state": retrieval.get("state", "provider_error"), "queries_attempted": retrieval.get("queries_attempted", 0),
        "query_results": retrieval.get("query_results", []), "records_retrieved": retrieval.get("records_retrieved", 0),
        "candidates_filtered": retrieval.get("candidates_filtered", 0), "weak_candidates": retrieval.get("weak_candidates", 0),
        "retrieved_at": retrieval.get("retrieved_at", date.today().isoformat()),
    }}
    saved = None
    if snapshot_writer:
        try:
            saved = snapshot_writer(user, {"analysis_id": str(analysis_id), "node": node, "focus": selected, "payload": response})
        except Exception as error:
            log.warning("evidence snapshot write failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
    response.update(snapshot_id=(saved or {}).get("id"), snapshot_saved=bool(saved),
                    snapshot_persistence_note=("This retrieval is preserved. Refreshing will append a new snapshot; earlier retrievals are retained."
                                               if saved else "This retrieval is available now but could not be saved for later review."))
    return response


@app.get("/v1/analyses/{analysis_id}/evidence", response_model=EvidenceResponse)
def analysis_evidence(analysis_id: uuid.UUID, request: Request,
                      node: str = Query(..., min_length=1, max_length=100),
                      focus: Literal["Market", "Industry", "Funding", "Traction", "Location"] | None = Query(None),
                      limit: int = Query(8, ge=3, le=8), user: User = Depends(read_user)):
    """Return the preserved source-linked retrieval, or create the first snapshot."""
    return _analysis_evidence(analysis_id, request, node, focus, limit, user)


@app.get("/v1/analyses/{analysis_id}/evidence/history", response_model=EvidenceSnapshotHistory)
def evidence_snapshot_history(analysis_id: uuid.UUID, request: Request,
                      node: str = Query(..., min_length=1, max_length=100),
                      focus: Literal["Market", "Industry", "Funding", "Traction", "Location"] | None = Query(None),
                      limit: int = Query(20, ge=1, le=50), user: User = Depends(read_user)):
    """List saved snapshots without exposing other users' records or replacing the report's current selection."""
    if request.app.state.analyses.get(user, analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    store = request.app.state.analyses
    try:
        rows = store.list_evidence_snapshots(user, analysis_id, node, focus or node, limit)
    except Exception as error:
        log.warning("evidence snapshot history unavailable analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Saved research history is unavailable") from error
    return {"snapshots": [
        {"id": item["id"], "created_at": item["created_at"],
         "retrieved_at": item.get("payload", {}).get("retrieved_at", ""),
         "state": item.get("payload", {}).get("state", "unknown")}
        for item in rows
    ]}


@app.get("/v1/analyses/{analysis_id}/evidence/snapshots/{snapshot_id}", response_model=EvidenceResponse)
def get_evidence_snapshot(analysis_id: uuid.UUID, snapshot_id: uuid.UUID, request: Request,
                      user: User = Depends(read_user)):
    """Read one historical snapshot; viewing it never changes which snapshot is latest."""
    if request.app.state.analyses.get(user, analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    try:
        snapshot = request.app.state.analyses.get_evidence_snapshot(user, analysis_id, snapshot_id)
    except Exception as error:
        log.warning("evidence snapshot read unavailable analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Saved research history is unavailable") from error
    if snapshot is None:
        raise HTTPException(404, "Evidence snapshot not found")
    payload = dict(snapshot["payload"])
    payload.update(snapshot_id=snapshot["id"], snapshot_saved=True,
                   snapshot_persistence_note="Viewing a preserved historical retrieval. This does not change the latest snapshot.")
    return payload


@app.post("/v1/analyses/{analysis_id}/evidence/refresh", response_model=EvidenceResponse)
def refresh_analysis_evidence(analysis_id: uuid.UUID, request: Request,
                      node: str = Query(..., min_length=1, max_length=100),
                      focus: Literal["Market", "Industry", "Funding", "Traction", "Location"] | None = Query(None),
                      limit: int = Query(8, ge=3, le=8), user: User = Depends(read_user)):
    """Explicitly retrieve again and append a new evidence snapshot."""
    return _analysis_evidence(analysis_id, request, node, focus, limit, user, refresh=True)


def _association_payload(row: dict) -> dict:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else row
    return {**payload, "created_at": row.get("created_at", payload.get("created_at"))}


def _association_is_current(association_id: str, rows: list[dict]) -> bool:
    return association_id not in {
        row.get("supersedes_record_id") or (row.get("payload") or {}).get("supersedes_record_id")
        for row in rows
    }


def _read_snapshot(store, user: User, analysis_id: uuid.UUID, snapshot_id: uuid.UUID) -> dict:
    try:
        snapshot = store.get_evidence_snapshot(user, analysis_id, snapshot_id)
    except Exception as error:
        log.warning("evidence snapshot lookup failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Saved research snapshot is unavailable") from error
    if snapshot is None:
        raise HTTPException(404, "Evidence snapshot not found")
    return snapshot


def _comparison_candidate(analysis_id: uuid.UUID, associations: list[EvidenceAssociation], comparison: dict) -> ContradictionAssessment:
    return ContradictionAssessment(
        analysis_id=analysis_id,
        association_ids=[item.record_id for item in associations],
        compared_evidence=[{
            "association_id": item.record_id, "snapshot_id": item.snapshot_id,
            "source_id": item.source_id, "claim_text": item.claim_text,
            "exact_passage_text": item.exact_passage_text,
            "passage_location": item.passage_location,
            "source_access": item.source_access, "source_url": item.source_url,
            "publication": item.publication.model_dump(mode="json"),
        } for item in associations],
        nature=comparison["nature"], assessment_text=comparison["assessment_text"],
        relationship=comparison["relationship"],
        context_differences=comparison["context_differences"],
        methodological_differences=comparison["methodological_differences"],
        measurement_differences=comparison["measurement_differences"],
        population_differences=comparison["population_differences"],
        geographic_differences=comparison["geographic_differences"],
        time_period_differences=comparison["time_period_differences"],
        uncertainty_explanation=comparison["uncertainty_explanation"],
        source_access_limitations=comparison["source_access_limitations"],
        detection_method=comparison["detection_method"],
        verification_state="pending_review", verification_method="none",
        limitations=comparison["limitations"],
    )


@app.get("/v1/analyses/{analysis_id}/evidence/associations")
def list_evidence_associations(
    analysis_id: uuid.UUID, request: Request,
    snapshot_id: uuid.UUID | None = Query(None), limit: int = Query(100, ge=1, le=200),
    user: User = Depends(read_user),
):
    store = request.app.state.analyses
    if store.get(user, analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    if snapshot_id is not None:
        _read_snapshot(store, user, analysis_id, snapshot_id)
    try:
        rows = store.list_evidence_associations(user, analysis_id, snapshot_id, limit)
    except Exception as error:
        log.warning("evidence association list failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Saved evidence associations are unavailable") from error
    return {"associations": [{**_association_payload(row), "is_current": _association_is_current(str(row["id"]), rows)} for row in rows]}


@app.get("/v1/analyses/{analysis_id}/evidence/associations/{record_id}")
def get_evidence_association(analysis_id: uuid.UUID, record_id: uuid.UUID, request: Request,
                             user: User = Depends(read_user)):
    store = request.app.state.analyses
    if store.get(user, analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    try:
        row = store.get_evidence_association(user, analysis_id, record_id)
    except Exception as error:
        log.warning("evidence association read failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Saved evidence association is unavailable") from error
    if row is None:
        raise HTTPException(404, "Evidence association not found")
    rows = store.list_evidence_associations(user, analysis_id, None, 200)
    return {**_association_payload(row), "is_current": _association_is_current(str(row["id"]), rows)}


@app.post("/v1/analyses/{analysis_id}/evidence/associations", status_code=201)
def create_evidence_association(analysis_id: uuid.UUID, body: EvidenceAssociationSubmission,
                                request: Request, user: User = Depends(read_user)):
    store = request.app.state.analyses
    if store.get(user, analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    snapshot = _read_snapshot(store, user, analysis_id, body.snapshot_id)
    try:
        if body.claim_category == "historical_case_fact" and (snapshot.get("payload") or {}).get("provider") == "OpenAlex":
            raise HTTPException(422, "Historical case facts require a saved historical-source passage; OpenAlex research snapshots do not contain case-library sources")
        source_record = find_snapshot_source(snapshot, body.source_id)
        retrieved_at = None
        retrieved_day = source_record.get("retrieved_at") if source_record else None
        if isinstance(retrieved_day, str):
            try:
                retrieved_at = datetime.fromisoformat(f"{retrieved_day}T00:00:00+00:00")
            except ValueError:
                retrieved_at = None
        association = EvidenceAssociation(
            analysis_id=analysis_id, snapshot_id=body.snapshot_id,
            claim_text=body.claim_text, claim_category=body.claim_category,
            source_id=body.source_id, source_access=body.source_access,
            exact_passage_text=body.exact_passage_text, passage_location=body.passage_location,
            source_url=body.source_url, publication=body.publication,
            relationship=body.relationship, verification_state="pending_review",
            verification_method="none", limitations=body.limitations, retrieved_at=retrieved_at,
        )
        validate_evidence_association(association, snapshot)
    except (ValidationError, ValueError) as error:
        raise HTTPException(422, "Evidence association failed contract or snapshot validation") from error
    record = association.model_dump(mode="json")
    storage_record = {"id": str(association.record_id), "analysis_id": str(analysis_id),
                      "snapshot_id": str(body.snapshot_id), "supersedes_record_id": None, "payload": record}
    try:
        stored = store.save_evidence_association(user, storage_record)
    except StorageDenied as error:
        raise HTTPException(409, "Evidence association or correction target is invalid") from error
    except Exception as error:
        log.warning("evidence association save failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Evidence association could not be saved") from error
    return {**_association_payload(stored), "is_current": True}


@app.post("/v1/analyses/{analysis_id}/evidence/associations/{record_id}/review", status_code=201)
def review_evidence_association(analysis_id: uuid.UUID, record_id: uuid.UUID,
                               body: EvidenceReviewRequest, request: Request,
                               user: User = Depends(read_user)):
    store = request.app.state.analyses
    if store.get(user, analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    try:
        previous_row = store.get_evidence_association(user, analysis_id, record_id)
        history = store.list_evidence_associations(user, analysis_id, None, 200)
    except Exception as error:
        log.warning("evidence review lookup failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Evidence review history is unavailable") from error
    if previous_row is None:
        raise HTTPException(404, "Evidence association not found")
    if not _association_is_current(str(record_id), history):
        raise HTTPException(409, "This association was already superseded; review its current correction instead")
    previous = EvidenceAssociation.model_validate(_association_payload(previous_row))
    now = datetime.now(timezone.utc)
    revised = EvidenceAssociation.model_validate({
        **previous.model_dump(mode="json"), "record_id": str(uuid.uuid4()),
        "supersedes_record_id": str(record_id), "relationship": body.relationship,
        "verification_state": body.verification_state, "verification_method": "human_review",
        "reviewer_id": user.id,
        "limitations": list(dict.fromkeys([
            *previous.limitations,
            *body.limitations,
            "Reviewer is the authenticated analysis owner; this is not independent expert review.",
        ])),
        "reviewed_at": now.isoformat(),
        "verified_at": now.isoformat() if body.verification_state == "verified" else None,
        "created_at": now.isoformat(),
    })
    snapshot = _read_snapshot(store, user, analysis_id, revised.snapshot_id)
    try:
        validate_evidence_association(revised, snapshot)
        record = revised.model_dump(mode="json")
        stored = store.save_evidence_association(user, {
            "id": str(revised.record_id), "analysis_id": str(analysis_id),
            "snapshot_id": str(revised.snapshot_id), "supersedes_record_id": str(record_id),
            "payload": record,
        })
    except (ValidationError, EvidenceAssociationValidationError, StorageDenied) as error:
        raise HTTPException(422, "Evidence review failed validation") from error
    except Exception as error:
        log.warning("evidence review save failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Evidence review could not be saved") from error
    return {**_association_payload(stored), "is_current": True}


@app.get("/v1/analyses/{analysis_id}/evidence/contradictions")
def list_contradiction_assessments(analysis_id: uuid.UUID, request: Request,
                                   limit: int = Query(100, ge=1, le=200),
                                   user: User = Depends(read_user)):
    store = request.app.state.analyses
    if store.get(user, analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    try:
        rows = store.list_contradiction_assessments(user, analysis_id, limit)
    except Exception as error:
        log.warning("contradiction list failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Contradiction assessments are unavailable") from error
    superseded = {row.get("supersedes_record_id") or (row.get("payload") or {}).get("supersedes_record_id") for row in rows}
    assessments = []
    for row in rows:
        item = row.get("payload") or row
        linked = []
        try:
            for association_id in item.get("association_ids", []):
                association = store.get_evidence_association(user, analysis_id, uuid.UUID(str(association_id)))
                if association:
                    linked.append(_association_payload(association))
        except Exception as error:
            log.warning("contradiction source lookup failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
            raise HTTPException(503, "Contradiction source passages are unavailable") from error
        assessments.append({**item, "created_at": row.get("created_at"),
                            "linked_evidence": linked, "is_current": str(row["id"]) not in superseded})
    return {"assessments": assessments}


@app.post("/v1/analyses/{analysis_id}/evidence/contradictions/compare")
def compare_evidence_associations(analysis_id: uuid.UUID, body: ContradictionCompareRequest,
                                  request: Request, user: User = Depends(read_user)):
    """Explicitly compare two saved excerpts; report reads never trigger comparison."""
    store = request.app.state.analyses
    if store.get(user, analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    association_ids = body.association_ids
    try:
        existing = store.find_contradiction_for_pair(user, analysis_id, *association_ids)
        if existing is not None:
            payload = existing.get("payload") or existing
            history = store.list_contradiction_assessments(user, analysis_id, 200)
            superseded = {str(row.get("supersedes_record_id") or (row.get("payload") or {}).get("supersedes_record_id"))
                          for row in history if row.get("supersedes_record_id") or (row.get("payload") or {}).get("supersedes_record_id")}
            return {**payload, "created_at": existing.get("created_at", payload.get("created_at")),
                    "is_current": str(existing.get("id", payload.get("record_id"))) not in superseded,
                    "reused_existing": True}

        associations = []
        for association_id in association_ids:
            row = store.get_evidence_association(user, analysis_id, association_id)
            if row is None:
                raise HTTPException(404, "Evidence association not found")
            association = EvidenceAssociation.model_validate(_association_payload(row))
            if not association.exact_passage_text:
                raise HTTPException(422, "Comparison requires two stored source passages")
            snapshot = _read_snapshot(store, user, analysis_id, association.snapshot_id)
            validate_evidence_association(association, snapshot)
            associations.append(association)

        comparison = evidence_comparison.compare_saved_passages(*associations)
        candidate = _comparison_candidate(analysis_id, associations, comparison)
        stored = store.save_contradiction_assessment(user, {
            "id": str(candidate.record_id), "analysis_id": str(analysis_id),
            "association_ids": [str(item) for item in candidate.association_ids],
            "supersedes_record_id": None, "payload": candidate.model_dump(mode="json"),
        })
    except HTTPException:
        raise
    except (ValidationError, EvidenceAssociationValidationError) as error:
        raise HTTPException(422, "Saved source passages failed comparison validation") from error
    except StorageDenied as error:
        # A concurrent identical request may win the unique pair constraint.
        try:
            existing = store.find_contradiction_for_pair(user, analysis_id, *association_ids)
        except Exception:
            existing = None
        if existing is not None:
            payload = existing.get("payload") or existing
            return {**payload, "created_at": existing.get("created_at", payload.get("created_at")), "is_current": True, "reused_existing": True}
        raise HTTPException(409, "This evidence pair already has a comparison") from error
    except Exception as error:
        log.warning("evidence comparison failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Evidence comparison could not be saved") from error
    return {**stored["payload"], "created_at": stored["created_at"], "is_current": True, "reused_existing": False}


@app.post("/v1/analyses/{analysis_id}/evidence/contradictions/detect")
def detect_snapshot_disagreements(analysis_id: uuid.UUID, body: ContradictionDetectRequest,
                                  request: Request, user: User = Depends(read_user)):
    """Explicit bounded scan of one saved snapshot against current saved evidence."""
    store = request.app.state.analyses
    if store.get(user, analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    _read_snapshot(store, user, analysis_id, body.snapshot_id)
    try:
        rows = store.list_evidence_associations(user, analysis_id, None, 500)
        superseded = {str(row.get("supersedes_record_id") or (row.get("payload") or {}).get("supersedes_record_id"))
                      for row in rows if row.get("supersedes_record_id") or (row.get("payload") or {}).get("supersedes_record_id")}
        current_rows = [row for row in rows if str(row.get("id")) not in superseded]
        source_cache: dict[str, EvidenceAssociation] = {}
        snapshot_cache: dict[str, dict] = {}
        for row in current_rows:
            payload = _association_payload(row)
            association = EvidenceAssociation.model_validate(payload)
            if not association.exact_passage_text:
                continue
            snapshot_key = str(association.snapshot_id)
            if snapshot_key not in snapshot_cache:
                snapshot_cache[snapshot_key] = _read_snapshot(store, user, analysis_id, association.snapshot_id)
            validate_evidence_association(association, snapshot_cache[snapshot_key])
            source_cache[str(association.record_id)] = association
    except HTTPException:
        raise
    except (ValidationError, EvidenceAssociationValidationError) as error:
        raise HTTPException(422, "Saved evidence associations failed comparison validation") from error
    except Exception as error:
        log.warning("evidence comparison inputs unavailable analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Saved evidence for comparison is unavailable") from error

    target = [item for item in source_cache.values() if item.snapshot_id == body.snapshot_id]
    other = [item for item in source_cache.values() if item.snapshot_id != body.snapshot_id]
    proposed_pairs = list(combinations(target, 2))
    proposed_pairs.extend((left, right) for left in target for right in other)
    candidate_pair_count = len(proposed_pairs)
    bounded_pairs = proposed_pairs[body.offset:body.offset + 25]
    created = reused = skipped_insufficient = skipped_not_disagreement = 0
    persistence_incomplete = False

    for associations in bounded_pairs:
        pair_ids = [item.record_id for item in associations]
        try:
            if store.find_contradiction_for_pair(user, analysis_id, *pair_ids) is not None:
                reused += 1
                continue
            comparison = evidence_comparison.compare_saved_passages(*associations)
            if comparison["relationship"] == "insufficient":
                skipped_insufficient += 1
                continue
            if comparison["relationship"] not in {"contradicts", "partially_supports", "contextualizes"}:
                skipped_not_disagreement += 1
                continue
            candidate = _comparison_candidate(analysis_id, associations, comparison)
            store.save_contradiction_assessment(user, {
                "id": str(candidate.record_id), "analysis_id": str(analysis_id),
                "association_ids": [str(item) for item in candidate.association_ids],
                "supersedes_record_id": None, "payload": candidate.model_dump(mode="json"),
            })
            created += 1
        except StorageDenied:
            if store.find_contradiction_for_pair(user, analysis_id, *pair_ids) is not None:
                reused += 1
            else:
                persistence_incomplete = True
                break
        except Exception as error:
            log.warning("evidence disagreement save failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
            persistence_incomplete = True
            break

    next_offset = body.offset + len(bounded_pairs)
    truncated = next_offset < candidate_pair_count or len(rows) == 500
    complete = not truncated and not persistence_incomplete
    if persistence_incomplete:
        message = "The scan stopped because a comparison could not be saved. Some earlier candidates may have been appended; review the list before retrying."
    elif created:
        message = f"Saved {created} provisional disagreement candidate(s). Each needs human review and does not establish scientific truth."
    else:
        message = "The conservative rules found no new potential disagreement in the scanned passages. This is not evidence that no disagreement exists."
    return {
        "state": "complete" if complete else "partial",
        "snapshot_id": str(body.snapshot_id),
        "scanned_pairs": len(bounded_pairs),
        "next_offset": next_offset,
        "created": created,
        "reused_existing": reused,
        "skipped_insufficient": skipped_insufficient,
        "skipped_not_disagreement": skipped_not_disagreement,
        "truncated": truncated,
        "message": message,
    }


@app.post("/v1/analyses/{analysis_id}/evidence/contradictions", status_code=201)
def create_contradiction_assessment(analysis_id: uuid.UUID, body: ContradictionSubmission,
                                   request: Request, user: User = Depends(read_user)):
    store = request.app.state.analyses
    if store.get(user, analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    associations = []
    try:
        if store.find_contradiction_for_pair(user, analysis_id, *body.association_ids) is not None:
            raise HTTPException(409, "This evidence pair already has a comparison; review or correct its current record")
        for record_id in body.association_ids:
            row = store.get_evidence_association(user, analysis_id, record_id)
            if row is None:
                raise HTTPException(404, "Evidence association not found")
            association = EvidenceAssociation.model_validate(_association_payload(row))
            if not association.exact_passage_text:
                raise HTTPException(422, "Contradiction candidates require saved source passages")
            associations.append(association)
        candidate = ContradictionAssessment(
            analysis_id=analysis_id, association_ids=body.association_ids,
            compared_evidence=[{
                "association_id": item.record_id, "snapshot_id": item.snapshot_id,
                "source_id": item.source_id, "claim_text": item.claim_text,
                "exact_passage_text": item.exact_passage_text,
                "passage_location": item.passage_location,
                "source_access": item.source_access, "source_url": item.source_url,
                "publication": item.publication.model_dump(mode="json"),
            } for item in associations],
            nature=body.nature, assessment_text=body.assessment_text,
            verification_state="pending_review", verification_method="none",
            limitations=body.limitations + ["Candidate is based on saved excerpts; disagreement has not been human reviewed."],
        )
        stored = store.save_contradiction_assessment(user, {
            "id": str(candidate.record_id), "analysis_id": str(analysis_id),
            "association_ids": [str(item) for item in candidate.association_ids],
            "supersedes_record_id": None, "payload": candidate.model_dump(mode="json"),
        })
    except HTTPException:
        raise
    except ValidationError as error:
        raise HTTPException(422, "Contradiction candidate failed validation") from error
    except StorageDenied as error:
        raise HTTPException(422, "Contradiction candidate references an unavailable association") from error
    except Exception as error:
        log.warning("contradiction candidate save failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Contradiction candidate could not be saved") from error
    return {**stored["payload"], "created_at": stored["created_at"], "is_current": True}


@app.post("/v1/analyses/{analysis_id}/evidence/contradictions/{record_id}/review", status_code=201)
def review_contradiction_assessment(analysis_id: uuid.UUID, record_id: uuid.UUID,
                                    body: ContradictionReviewRequest, request: Request,
                                    user: User = Depends(read_user)):
    store = request.app.state.analyses
    if store.get(user, analysis_id) is None:
        raise HTTPException(404, "Analysis not found")
    try:
        previous_row = store.get_contradiction_assessment(user, analysis_id, record_id)
        history = store.list_contradiction_assessments(user, analysis_id, 200)
    except Exception as error:
        log.warning("contradiction review lookup failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Contradiction review history is unavailable") from error
    if previous_row is None:
        raise HTTPException(404, "Contradiction assessment not found")
    if record_id in {uuid.UUID(str(row.get("supersedes_record_id") or (row.get("payload") or {}).get("supersedes_record_id")))
                     for row in history if row.get("supersedes_record_id") or (row.get("payload") or {}).get("supersedes_record_id")}:
        raise HTTPException(409, "This assessment was already superseded")
    previous = previous_row.get("payload") or previous_row
    now = datetime.now(timezone.utc)
    assessment = ContradictionAssessment.model_validate({
        **previous, "record_id": str(uuid.uuid4()), "supersedes_record_id": str(record_id),
        "nature": body.nature, "assessment_text": body.assessment_text,
        "relationship": body.relationship or previous.get("relationship", "insufficient"),
        "verification_state": body.verification_state, "verification_method": "human_review",
        "reviewer_id": user.id, "reviewed_at": now.isoformat(),
        "created_at": now.isoformat(), "limitations": body.limitations,
        "reviewer_explanation": body.reviewer_explanation,
    })
    try:
        for association_id in assessment.association_ids:
            if store.get_evidence_association(user, analysis_id, association_id) is None:
                raise HTTPException(422, "Contradiction source association is unavailable")
        stored = store.save_contradiction_assessment(user, {
            "id": str(assessment.record_id), "analysis_id": str(analysis_id),
            "association_ids": [str(item) for item in assessment.association_ids],
            "supersedes_record_id": str(record_id), "payload": assessment.model_dump(mode="json"),
        })
    except HTTPException:
        raise
    except (ValidationError, StorageDenied) as error:
        raise HTTPException(422, "Contradiction review failed validation") from error
    except Exception as error:
        log.warning("contradiction review save failed analysis_id=%s reason=%s", analysis_id, type(error).__name__)
        raise HTTPException(503, "Contradiction review could not be saved") from error
    return {**stored["payload"], "created_at": stored["created_at"], "is_current": True}


@app.delete("/v1/analyses/{analysis_id}", status_code=204, response_class=Response)
def delete_analysis(analysis_id: uuid.UUID, request: Request, user: User = Depends(read_user)):
    if not request.app.state.analyses.delete(user, analysis_id):
        raise HTTPException(404, "Analysis not found")
    return Response(status_code=204)
