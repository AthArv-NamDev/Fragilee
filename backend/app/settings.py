"""Settings read from environment variables, with safe local defaults.

For local work put them in backend/.env and start with:  uvicorn app.main:app --reload --env-file .env
"""
import os
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ENV = os.getenv("ENV", "dev")                      # set ENV=prod when deployed
MODELS_DIR = Path(os.getenv("MODELS_DIR", ROOT / "models"))
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", "10000"))   # requests here are tiny, so refuse big ones

# --- Supabase (login + database) ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")       # the public "anon"/"publishable" key. NOT the service key.
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")   # only for old projects that still sign tokens with HS256
STORAGE = os.getenv("STORAGE", "supabase")                   # "memory" is for tests only

# --- limits ---
FREE_ANALYSIS_LIMIT = int(os.getenv("FREE_ANALYSIS_LIMIT", "0"))   # 0 = unlimited (beta). Planned: 3 per account.
RATE_LIMIT_PREDICT = os.getenv("RATE_LIMIT_PREDICT", "20/minute")  # per user: predictions and saves
RATE_LIMIT_READ = os.getenv("RATE_LIMIT_READ", "60/minute")        # per user: list, open, delete
RATE_LIMIT_IP = os.getenv("RATE_LIMIT_IP", "200/minute")           # per IP address, before login is even checked


def validate() -> None:
    """Refuse to start with an unsafe or incomplete setup."""
    host = urlparse(SUPABASE_URL).hostname or ""
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not set. See .env.example.")
    if not SUPABASE_URL.startswith("https://") and host not in ("localhost", "127.0.0.1"):
        raise RuntimeError("SUPABASE_URL must start with https://")
    if STORAGE not in ("supabase", "memory"):
        raise RuntimeError("STORAGE must be 'supabase' or 'memory'")
    if STORAGE == "supabase" and not SUPABASE_ANON_KEY:
        raise RuntimeError("SUPABASE_ANON_KEY is not set. See .env.example.")
    if ENV == "prod":
        if STORAGE != "supabase":
            raise RuntimeError("STORAGE=memory is not allowed when ENV=prod")
        if "*" in ALLOWED_ORIGINS:
            raise RuntimeError("ALLOWED_ORIGINS must list your real frontend origin, not '*'")
