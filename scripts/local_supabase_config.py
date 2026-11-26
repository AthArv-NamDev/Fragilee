"""Fail-closed, local-only Fragilee configuration for the Supabase CLI stack."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ENV = REPO_ROOT / ".env.local-supabase"
BACKEND_ENV = REPO_ROOT / "backend" / ".env.local-supabase"
LOCAL_SUPABASE_URL = "http://127.0.0.1:54321"
LOCAL_API_URL = "http://127.0.0.1:8001"
LOCAL_FRONTEND_ORIGIN = "http://localhost:3001"
LOCAL_PROJECT_ID = "fragilee-local"
_KEY_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class LocalSupabaseConfigError(ValueError):
    """Local configuration is missing, inconsistent, or unsafe."""


def read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise LocalSupabaseConfigError(f"Missing local configuration file: {path.name}")
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise LocalSupabaseConfigError(f"Invalid {path.name} line {number}; use KEY=value.")
        name, value = (part.strip() for part in line.split("=", 1))
        if not _KEY_NAME.fullmatch(name) or name in values:
            raise LocalSupabaseConfigError(f"Invalid or duplicate variable in {path.name} line {number}.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if any(token in value for token in ("${", "`", "\n", "\r")):
            raise LocalSupabaseConfigError(f"Unsupported value syntax in {path.name} line {number}.")
        values[name] = value
    return values


def _decode_jwt_payload(value: str) -> dict | None:
    parts = value.split(".")
    if len(parts) != 3:
        return None
    try:
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        result = json.loads(decoded)
        return result if isinstance(result, dict) else None
    except (ValueError, UnicodeError, json.JSONDecodeError, binascii.Error):
        return None


def _decode_jwt_header(value: str) -> dict | None:
    parts = value.split(".")
    if len(parts) != 3:
        return None
    try:
        padded = parts[0] + "=" * (-len(parts[0]) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        result = json.loads(decoded)
        return result if isinstance(result, dict) else None
    except (ValueError, UnicodeError, json.JSONDecodeError, binascii.Error):
        return None


def _validate_public_key(key: str, field: str, local_jwt_secret: str = "") -> None:
    lowered = key.strip().lower()
    if not key or any(marker in lowered for marker in ("<", ">", "placeholder", "replace-me", "your-", "example")):
        raise LocalSupabaseConfigError(f"Set {field} to the local Supabase publishable/anon key.")
    if lowered.startswith(("sb_secret_", "sb_service_role_")):
        raise LocalSupabaseConfigError(f"{field} must be a local public publishable/anon key, never a secret key.")
    if lowered.startswith("sb_publishable_"):
        suffix = key[len("sb_publishable_"):]
        if len(suffix) < 16 or not re.fullmatch(r"[A-Za-z0-9_-]+", suffix):
            raise LocalSupabaseConfigError(f"{field} is not a valid publishable key.")
        return
    claims = _decode_jwt_payload(key)
    if claims is None or claims.get("role") != "anon":
        raise LocalSupabaseConfigError(f"{field} must be a local publishable key or an anon-role JWT.")
    header = _decode_jwt_header(key)
    parts = key.split(".")
    if not local_jwt_secret or not header or header.get("alg") != "HS256":
        raise LocalSupabaseConfigError(f"{field} legacy anon JWT must be verified with the local SUPABASE_JWT_SECRET.")
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    expected_signature = hmac.new(local_jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        padding = "=" * (-len(parts[2]) % 4)
        signature = base64.urlsafe_b64decode((parts[2] + padding).encode("ascii"))
    except (ValueError, UnicodeError, binascii.Error):
        signature = b""
    if not hmac.compare_digest(expected_signature, signature):
        raise LocalSupabaseConfigError(f"{field} legacy anon JWT signature does not match the local JWT secret.")


def _reject_unsafe_variables(frontend: dict[str, str], backend: dict[str, str]) -> None:
    for values in (frontend, backend):
        if any("SERVICE_ROLE" in name.upper() or "SECRET_KEY" in name.upper() for name in values):
            raise LocalSupabaseConfigError("Service-role and secret keys are not allowed in Fragilee local app configuration.")
    allowed_front = {
        "FRAGILEE_ENV", "NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "NEXT_PUBLIC_API_URL",
    }
    allowed_back = {
        "FRAGILEE_ENV", "ENV", "STORAGE", "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_JWT_SECRET", "ALLOWED_ORIGINS",
    }
    if extra := sorted(set(frontend) - allowed_front):
        raise LocalSupabaseConfigError(f"Unsupported variable in frontend local file: {extra[0]}.")
    if extra := sorted(set(backend) - allowed_back):
        raise LocalSupabaseConfigError(f"Unsupported variable in backend local file: {extra[0]}.")


def load_local_config(frontend_path: Path = FRONTEND_ENV, backend_path: Path = BACKEND_ENV):
    frontend = read_env_file(frontend_path)
    backend = read_env_file(backend_path)
    _reject_unsafe_variables(frontend, backend)

    for values, names, filename in (
        (frontend, ("FRAGILEE_ENV", "NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "NEXT_PUBLIC_API_URL"), frontend_path.name),
        (backend, ("FRAGILEE_ENV", "ENV", "STORAGE", "SUPABASE_URL", "SUPABASE_ANON_KEY", "ALLOWED_ORIGINS"), backend_path.name),
    ):
        missing = [name for name in names if not values.get(name, "").strip()]
        if missing:
            raise LocalSupabaseConfigError(f"Set {missing[0]} in {filename}.")
    if frontend["FRAGILEE_ENV"] != "local" or backend["FRAGILEE_ENV"] != "local":
        raise LocalSupabaseConfigError("Both local files must set FRAGILEE_ENV=local.")
    if backend["ENV"].lower() == "prod":
        raise LocalSupabaseConfigError("Local mode cannot start with ENV=prod.")
    if backend["STORAGE"] != "supabase":
        raise LocalSupabaseConfigError("Local mode requires STORAGE=supabase.")

    # Require the exact loopback endpoint. This rejects every hosted URL (including known Production)
    # and prevents the launcher from falling back to a remotely hosted instance.
    for field, value in (
        ("NEXT_PUBLIC_SUPABASE_URL", frontend["NEXT_PUBLIC_SUPABASE_URL"]),
        ("SUPABASE_URL", backend["SUPABASE_URL"]),
    ):
        parsed = urlparse(value)
        if value.rstrip("/") != LOCAL_SUPABASE_URL or parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port != 54321:
            raise LocalSupabaseConfigError(f"{field} must be exactly {LOCAL_SUPABASE_URL}; hosted URLs are refused.")
    if frontend["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/") != backend["SUPABASE_URL"].rstrip("/"):
        raise LocalSupabaseConfigError("Frontend and backend must use the same local Supabase URL.")
    if frontend["NEXT_PUBLIC_API_URL"].rstrip("/") != LOCAL_API_URL:
        raise LocalSupabaseConfigError(f"NEXT_PUBLIC_API_URL must be {LOCAL_API_URL}.")
    origins = {part.strip().rstrip("/") for part in backend["ALLOWED_ORIGINS"].split(",") if part.strip()}
    if origins != {LOCAL_FRONTEND_ORIGIN}:
        raise LocalSupabaseConfigError(f"ALLOWED_ORIGINS must contain only {LOCAL_FRONTEND_ORIGIN}.")

    frontend_key = frontend["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"]
    backend_key = backend["SUPABASE_ANON_KEY"]
    secret = backend.get("SUPABASE_JWT_SECRET", "").strip()
    if secret and (len(secret) < 32 or any(marker in secret.lower() for marker in ("<", ">", "placeholder", "replace-me"))):
        raise LocalSupabaseConfigError("SUPABASE_JWT_SECRET must be omitted for JWKS signing or set to the local JWT secret.")
    _validate_public_key(frontend_key, "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", secret)
    _validate_public_key(backend_key, "SUPABASE_ANON_KEY", secret)
    if frontend_key != backend_key:
        raise LocalSupabaseConfigError("Frontend and backend must use the same local public key.")
    return frontend, backend
