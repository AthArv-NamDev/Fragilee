"""Launch Fragilee against only the local Supabase CLI stack."""
from __future__ import annotations

import os
import socket
import subprocess
import sys

from local_supabase_config import (
    LOCAL_API_URL, LOCAL_FRONTEND_ORIGIN, LOCAL_SUPABASE_URL, LocalSupabaseConfigError,
    REPO_ROOT, load_local_config,
)


def ensure_port_available(port: int) -> None:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            raise LocalSupabaseConfigError(f"Port {port} is already in use; this launcher will not stop another process.")


def clean_runtime_env(values: dict[str, str], *, frontend: bool) -> dict[str, str]:
    # Do not inherit existing shell/Production variables. Required Next.js values are explicitly
    # present in `values`, so its automatic .env.local loading cannot override them.
    keep = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "TERM", "NPM_CONFIG_CACHE")
    env = {key: os.environ[key] for key in keep if key in os.environ}
    env.update(values)
    env["FRAGILEE_ENV"] = "local"
    if frontend:
        env["NEXT_PUBLIC_API_URL"] = LOCAL_API_URL
        env["NEXT_TELEMETRY_DISABLED"] = "1"
    else:
        env["FRAGILEE_ENV"] = "local"
    return env


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"check", "frontend", "backend"}:
        print("Usage: python3 scripts/local_supabase.py {check|frontend|backend}", file=sys.stderr)
        return 2
    mode = sys.argv[1]
    try:
        frontend_values, backend_values = load_local_config()
        print("Fragilee local configuration verified | environment: local | Supabase: 127.0.0.1:54321")
        if mode == "check":
            print("Frontend: http://localhost:3001 | Backend: http://127.0.0.1:8001")
            print("Supabase: API 54321 | DB 54322 | Studio 54323 | email 54324")
            return 0
        port = 3001 if mode == "frontend" else 8001
        ensure_port_available(port)
    except LocalSupabaseConfigError as exc:
        print(f"Local startup refused: {exc}", file=sys.stderr)
        return 2

    if mode == "frontend":
        cmd = ["npm", "run", "dev", "--", "--hostname", "127.0.0.1", "--port", "3001"]
        cwd = REPO_ROOT
        runtime = clean_runtime_env(frontend_values, frontend=True)
        print("Starting local Fragilee frontend at http://localhost:3001")
    else:
        python = REPO_ROOT / "backend" / ".venv" / "bin" / "python"
        executable = str(python) if python.is_file() else sys.executable
        cmd = [executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"]
        cwd = REPO_ROOT / "backend"
        runtime = clean_runtime_env(backend_values, frontend=False)
        print("Starting local Fragilee API at http://127.0.0.1:8001")
    return subprocess.run(cmd, cwd=cwd, env=runtime, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
