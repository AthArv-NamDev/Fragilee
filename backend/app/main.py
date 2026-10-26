"""Fragilee API. Module 2: prediction + risk tree. Module 3: login, saved analyses, rate limits."""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import scoring, settings
from .auth import User, ip_limit, predict_user, read_user
from .model_store import ModelStore
from .schemas import (AnalysisCreate, AnalysisOut, AnalysisSummary, PredictionResponse,
                      Stage1Request, Stage2Request)
from .storage import StorageDenied, StorageError, make_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fragilee")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()                                    # refuse to start with an unsafe setup
    app.state.store = ModelStore(settings.MODELS_DIR)      # fails loudly if a model file was changed
    app.state.analyses = make_store()
    log.info("models loaded: %s | storage: %s | env: %s", ", ".join(app.state.store.stages), settings.STORAGE, settings.ENV)
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
        "input": req.model_dump(), "result": result, "band": result["band"], "probability": result["probability"]})


@app.get("/v1/analyses", response_model=list[AnalysisSummary])
def list_analyses(request: Request, user: User = Depends(read_user),
                  limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0, le=10000)):
    return request.app.state.analyses.list(user, limit, offset)


@app.get("/v1/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: uuid.UUID, request: Request, user: User = Depends(read_user)):
    row = request.app.state.analyses.get(user, analysis_id)
    if row is None:                                       # someone else's analysis looks exactly like a missing one
        raise HTTPException(404, "Analysis not found")
    return row


@app.delete("/v1/analyses/{analysis_id}", status_code=204, response_class=Response)
def delete_analysis(analysis_id: uuid.UUID, request: Request, user: User = Depends(read_user)):
    if not request.app.state.analyses.delete(user, analysis_id):
        raise HTTPException(404, "Analysis not found")
    return Response(status_code=204)
