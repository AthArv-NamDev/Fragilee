"""Run Fragilee against a verified, isolated staging Supabase project."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path

from staging_config import REPO_ROOT, StagingConfigError, load_staging_config, verify_remote_public_key


def ensure_port_available(port: int) -> None:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            raise StagingConfigError(f"Port {port} is already in use. Stop the known local service yourself, then retry; this script will not terminate processes.")


def clean_runtime_env(values: dict[str, str]) -> dict[str, str]:
    env = {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "TERM") if key in os.environ}
    env.update(values)
    return env


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"check", "frontend", "backend"}:
        print("Usage: python3 scripts/staging.py {check|frontend|backend}", file=sys.stderr)
        return 2
    mode = sys.argv[1]
    try:
        frontend, backend, project_ref = load_staging_config()
        print(f"Fragilee staging configuration verified | project ref: {project_ref}")
        if mode == "check":
            print("Frontend API: http://127.0.0.1:8001 | frontend origin: http://localhost:3001")
            return 0
        verify_remote_public_key(frontend, project_ref)
        print("Read-only staging API-key check: passed")
        port = 3001 if mode == "frontend" else 8001
        ensure_port_available(port)
    except StagingConfigError as exc:
        print(f"Staging startup refused: {exc}", file=sys.stderr)
        return 2

    if mode == "frontend":
        runtime = clean_runtime_env(frontend)
        cmd = ["npm", "run", "dev", "--", "--hostname", "127.0.0.1", "--port", "3001"]
        cwd = REPO_ROOT
        print("Starting staging frontend at http://localhost:3001")
    else:
        runtime = clean_runtime_env(backend)
        backend_python = REPO_ROOT / "backend" / ".venv" / "bin" / "python"
        python = str(backend_python) if backend_python.is_file() else sys.executable
        cmd = [python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"]
        cwd = REPO_ROOT / "backend"
        print("Starting staging API at http://127.0.0.1:8001")
    return subprocess.run(cmd, cwd=cwd, env=runtime, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
