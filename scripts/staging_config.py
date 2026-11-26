"""Fail-closed validation for Fragilee's local staging configuration."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

PRODUCTION_PROJECT_REF = "ayrxcjlonouqluysnhlg"
REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ENV = REPO_ROOT / ".env.staging.local"
BACKEND_ENV = REPO_ROOT / "backend" / ".env.staging"
_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROJECT_HOST = re.compile(r"^([a-z0-9]{20})\.supabase\.co$")


class StagingConfigError(ValueError):
    pass


def read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise StagingConfigError(f"Missing staging configuration file: {path.name}")
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise StagingConfigError(f"Invalid {path.name} line {number}; use KEY=value.")
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not _KEY.fullmatch(key) or key in values:
            raise StagingConfigError(f"Invalid or duplicate environment variable in {path.name} line {number}.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if "${" in value or "`" in value or "\n" in value or "\r" in value:
            raise StagingConfigError(f"Unsupported value syntax in {path.name} line {number}.")
        values[key] = value
    return values


def _project_ref(url: str, field: str) -> str:
    parsed = urlparse(url)
    match = _PROJECT_HOST.fullmatch(parsed.hostname or "")
    if parsed.scheme != "https" or not match:
        raise StagingConfigError(f"{field} must be an https://<project-ref>.supabase.co URL.")
    return match.group(1)


def _required(values: dict[str, str], names: tuple[str, ...], filename: str) -> None:
    for name in names:
        value = values.get(name, "").strip()
        if not value or any(token in value.lower() for token in ("your-project", "your-anon", "your-publishable", "replace-me", "<", ">", "placeholder")):
            raise StagingConfigError(f"Set {name} to a real staging value in {filename}.")


def load_staging_config(frontend_path: Path = FRONTEND_ENV, backend_path: Path = BACKEND_ENV):
    frontend = read_env_file(frontend_path)
    backend = read_env_file(backend_path)
    _required(frontend, ("NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "NEXT_PUBLIC_API_URL"), frontend_path.name)
    _required(backend, ("SUPABASE_URL", "SUPABASE_ANON_KEY"), backend_path.name)
    if frontend.get("FRAGILEE_ENV") != "staging" or backend.get("FRAGILEE_ENV") != "staging":
        raise StagingConfigError("Both staging files must set FRAGILEE_ENV=staging.")
    if backend.get("ENV", "dev") == "prod":
        raise StagingConfigError("Staging backend must not set ENV=prod.")
    if backend.get("STORAGE") != "supabase":
        raise StagingConfigError("Staging backend must set STORAGE=supabase.")
    if "SUPABASE_SERVICE_ROLE_KEY" in frontend or "SUPABASE_SERVICE_ROLE_KEY" in backend:
        raise StagingConfigError("Do not configure a service-role key; the current API uses the caller's user token and anon key.")
    front_ref = _project_ref(frontend["NEXT_PUBLIC_SUPABASE_URL"], "NEXT_PUBLIC_SUPABASE_URL")
    back_ref = _project_ref(backend["SUPABASE_URL"], "SUPABASE_URL")
    if front_ref == PRODUCTION_PROJECT_REF or back_ref == PRODUCTION_PROJECT_REF:
        raise StagingConfigError("Staging refuses the known Production Supabase project.")
    if front_ref != back_ref:
        raise StagingConfigError("Frontend and backend Supabase project references do not match.")
    if frontend["NEXT_PUBLIC_API_URL"].rstrip("/") != "http://127.0.0.1:8001":
        raise StagingConfigError("Staging frontend API URL must be http://127.0.0.1:8001.")
    if frontend["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"] != backend["SUPABASE_ANON_KEY"]:
        raise StagingConfigError("Frontend and backend must use the same staging public key.")
    expected_origin = "http://localhost:3001"
    origins = {item.strip().rstrip("/") for item in backend.get("ALLOWED_ORIGINS", "").split(",") if item.strip()}
    if origins != {expected_origin}:
        raise StagingConfigError("Staging backend ALLOWED_ORIGINS must contain only http://localhost:3001.")
    return frontend, backend, front_ref


def verify_remote_public_key(frontend: dict[str, str], project_ref: str) -> None:
    """Make a read-only PostgREST root request; never print key, URL, or response body."""
    if project_ref == PRODUCTION_PROJECT_REF:
        raise StagingConfigError("Refusing network verification against the known Production project.")
    request = Request(
        frontend["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/") + "/rest/v1/",
        headers={"apikey": frontend["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"], "Accept": "application/openapi+json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=8) as response:
            if response.status != 200:
                raise StagingConfigError(f"Staging PostgREST public-key check returned HTTP {response.status}.")
            response.read(1)  # read only enough to confirm the endpoint responded; never retain or print schema data
    except HTTPError as exc:
        raise StagingConfigError(f"Staging PostgREST public-key check returned HTTP {exc.code}.") from None
    except URLError:
        raise StagingConfigError("Could not reach the configured staging Supabase API.") from None
