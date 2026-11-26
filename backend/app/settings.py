"""Settings read from environment variables, with safe local defaults.

For local work put them in backend/.env and start with:  uvicorn app.main:app --reload --env-file .env
"""
import os
import re
import base64
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ENV = os.getenv("ENV", "dev")                      # set ENV=prod when deployed
FRAGILEE_ENV = os.getenv("FRAGILEE_ENV", "development").strip().lower()
MODELS_DIR = Path(os.getenv("MODELS_DIR", ROOT / "models"))
EXPOSE_COHORT = os.getenv("EXPOSE_COHORT", "false").lower() == "true"   # counts from the training data stay private unless you turn this on
CASES_JSON = Path(os.getenv("CASES_JSON", ROOT / "data" / "cases.json"))
COHORT_CSV = Path(os.getenv("COHORT_CSV", ROOT / "data" / "processed" / "stage1_clean.csv"))   # for "startups like yours" counts
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", "16000"))   # requests here are tiny, so refuse big ones

# --- Supabase (login + database) ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")       # the public "anon"/"publishable" key. NOT the service key.
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")   # only for old projects that still sign tokens with HS256
STORAGE = os.getenv("STORAGE", "supabase")                   # "memory" is for tests only
PUBLIC_SUPABASE_PROJECT_REF = os.getenv("FRAGILEE_PUBLIC_SUPABASE_PROJECT_REF", "").strip().lower()
PRODUCTION_SUPABASE_PROJECT_REF = "ayrxcjlonouqluysnhlg"
LOCAL_SUPABASE_PROJECT_REF = "fragilee-local"


def supabase_project_ref() -> str:
    """Return only the non-secret Supabase project reference, never a URL or key."""
    parsed = urlparse(SUPABASE_URL)
    host = (parsed.hostname or "").lower()
    if FRAGILEE_ENV == "local" and parsed.scheme == "http" and host == "127.0.0.1" and parsed.port == 54321:
        return LOCAL_SUPABASE_PROJECT_REF
    match = re.fullmatch(r"([a-z0-9]{20})\.supabase\.co", host)
    return match.group(1) if match else "unknown"

# --- limits ---
FREE_ANALYSIS_LIMIT = int(os.getenv("FREE_ANALYSIS_LIMIT", "0"))   # 0 = unlimited (beta). Planned: 3 per account.
RATE_LIMIT_PREDICT = os.getenv("RATE_LIMIT_PREDICT", "20/minute")  # per user: predictions and saves
RATE_LIMIT_READ = os.getenv("RATE_LIMIT_READ", "60/minute")        # per user: list, open, delete
RATE_LIMIT_IP = os.getenv("RATE_LIMIT_IP", "200/minute")           # per IP address, before login is even checked


def validate() -> None:
    """Refuse to start with an unsafe or incomplete setup."""
    host = urlparse(SUPABASE_URL).hostname or ""
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not set. See backend.env.example.")
    if not SUPABASE_URL.startswith("https://") and host not in ("localhost", "127.0.0.1"):
        raise RuntimeError("SUPABASE_URL must start with https://")
    if STORAGE not in ("supabase", "memory"):
        raise RuntimeError("STORAGE must be 'supabase' or 'memory'")
    if STORAGE == "supabase" and not SUPABASE_ANON_KEY:
        raise RuntimeError("SUPABASE_ANON_KEY is not set. See .env.example.")
    if FRAGILEE_ENV == "staging":
        project_ref = supabase_project_ref()
        if ENV == "prod":
            raise RuntimeError("Staging cannot start with ENV=prod.")
        if STORAGE != "supabase":
            raise RuntimeError("Staging requires STORAGE=supabase for isolated persistent test data.")
        if project_ref == "unknown":
            raise RuntimeError("Staging SUPABASE_URL must identify a Supabase project.")
        if project_ref == PRODUCTION_SUPABASE_PROJECT_REF:
            raise RuntimeError("Staging refuses the known Production Supabase project.")
    if FRAGILEE_ENV == "public":
        parsed = urlparse(SUPABASE_URL)
        if ENV != "prod":
            raise RuntimeError("Public deployment requires ENV=prod.")
        if STORAGE != "supabase":
            raise RuntimeError("Public deployment requires STORAGE=supabase.")
        if parsed.scheme != "https" or supabase_project_ref() == "unknown":
            raise RuntimeError("Public SUPABASE_URL must be an HTTPS Supabase project URL.")
        project_ref = supabase_project_ref()
        if not PUBLIC_SUPABASE_PROJECT_REF:
            raise RuntimeError("Public deployment requires FRAGILEE_PUBLIC_SUPABASE_PROJECT_REF.")
        if project_ref != PUBLIC_SUPABASE_PROJECT_REF:
            raise RuntimeError("Public deployment Supabase URL does not match the explicitly configured project reference.")
        if SUPABASE_JWT_SECRET:
            raise RuntimeError("Public deployment must use Supabase JWKS verification; unset SUPABASE_JWT_SECRET.")
        if not _is_public_supabase_key(SUPABASE_ANON_KEY):
            raise RuntimeError("Public deployment requires a Supabase publishable or legacy anon key.")
        if not ALLOWED_ORIGINS or any(not _is_https_origin(origin) for origin in ALLOWED_ORIGINS):
            raise RuntimeError("Public ALLOWED_ORIGINS must contain only exact HTTPS frontend origins.")
    if ENV == "prod":
        if STORAGE != "supabase":
            raise RuntimeError("STORAGE=memory is not allowed when ENV=prod")
        if "*" in ALLOWED_ORIGINS:
            raise RuntimeError("ALLOWED_ORIGINS must list your real frontend origin, not '*'")


def _is_https_origin(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and parsed.path in ("", "/") and not parsed.query and not parsed.fragment


def _is_public_supabase_key(value: str) -> bool:
    """Accept only publishable keys or legacy anon JWTs; never service-role/secret keys."""
    if value.startswith("sb_publishable_"):
        return True
    parts = value.split(".")
    if len(parts) != 3:
        return False
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, json.JSONDecodeError):
        return False
    return isinstance(claims, dict) and claims.get("role") == "anon"
