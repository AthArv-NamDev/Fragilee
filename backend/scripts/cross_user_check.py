"""Cross-user checks are restricted to an explicitly confirmed staging project.

This script creates and deletes a disposable analysis. It will not read backend/.env,
accept an arbitrary API URL, or run without both staging confirmations.
"""
import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import sys

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from staging_config import StagingConfigError, load_staging_config  # noqa: E402


def staging_startup():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-staging-project-ref", required=True,
                        help="must exactly match the non-Production staging project ref")
    parser.add_argument("--confirm-cleanup", action="store_true",
                        help="confirm creation and deletion of a disposable staging analysis")
    args = parser.parse_args()
    if not args.confirm_cleanup:
        parser.error("--confirm-cleanup is required because this check creates and deletes a staging analysis")
    try:
        frontend, backend, project_ref = load_staging_config()
    except StagingConfigError as exc:
        parser.error(f"staging configuration rejected: {exc}")
    if args.confirm_staging_project_ref != project_ref:
        parser.error("the confirmed project reference does not match the configured staging project")
    os.environ.update(backend)
    return "http://127.0.0.1:8001", project_ref


URL, STAGING_PROJECT_REF = staging_startup()
STAGE2 = {"category": "software", "state": "CA", "funding_total_usd": 250000, "funding_rounds": 2, "has_VC": False,
          "has_angel": True, "has_roundA": True, "has_roundB": False, "has_roundC": False, "has_roundD": False,
          "avg_participants": 2.0, "relationships": 5, "age_first_funding_year": 1.0, "age_last_funding_year": 2.0}


def sign_in(label):
    """Ask for an email and password, and return a fresh access token from Supabase."""
    base, anon = os.environ.get("SUPABASE_URL", "").rstrip("/"), os.environ.get("SUPABASE_ANON_KEY", "")
    if not base or not anon:
        sys.exit("Staging SUPABASE_URL and SUPABASE_ANON_KEY are required in backend/.env.staging.")
    email = os.environ.get(f"EMAIL_{label}") or input(f"Email of test user {label}: ").strip()
    password = os.environ.get(f"PASSWORD_{label}") or getpass.getpass(f"Password of {email} (hidden): ")
    try:
        r = httpx.post(f"{base}/auth/v1/token", params={"grant_type": "password"}, timeout=20,
                       headers={"apikey": anon, "Content-Type": "application/json"},
                       json={"email": email, "password": password})
    except httpx.TransportError:
        sys.exit(f"Cannot reach the configured staging Supabase project {STAGING_PROJECT_REF}.")
    if r.status_code != 200:
        sys.exit(f"Sign-in failed for user {label} ({r.status_code}): wrong email or password, or the user is not confirmed.")
    return r.json()["access_token"]


def user_of(token):
    """Read the user id out of the token (for display only; the server does the real checking)."""
    try:
        body = token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))["sub"]
    except Exception:
        sys.exit("That does not look like an access token. Paste only the access_token value.")


TOKEN_A = os.environ.get("TOKEN_A") or sign_in("A")
TOKEN_B = os.environ.get("TOKEN_B") or sign_in("B")
a_id, b_id = user_of(TOKEN_A), user_of(TOKEN_B)
if a_id == b_id:
    sys.exit("TOKEN_A and TOKEN_B belong to the same user. Use two different users.")
print(f"User A {a_id[:8]}...  User B {b_id[:8]}...  Server {URL}\n")

A = {"Authorization": f"Bearer {TOKEN_A}"}
B = {"Authorization": f"Bearer {TOKEN_B}"}
c = httpx.Client(base_url=URL, timeout=30)
failures = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + ("" if ok else f"   <- {detail}"))
    if not ok:
        failures.append(label)


try:
    up = c.get("/health").status_code == 200
except httpx.TransportError:
    sys.exit(f"Cannot reach the server at {URL}. Is uvicorn running? Start it with: uvicorn app.main:app --reload --env-file .env")
check("server is up", up)
check("no token is refused (401)", c.get("/v1/analyses").status_code == 401)

r = c.post("/v1/analyses", headers=A, json={"title": "cross-user check", "stage": "stage2", "input": STAGE2})
check("A saves an analysis (201)", r.status_code == 201, f"{r.status_code} {r.text[:150]}")
if r.status_code != 201:
    sys.exit("Cannot continue: A could not save. Fix that first (see the status code above).")
aid = r.json()["id"]
check("response does not leak user_id", "user_id" not in r.json())

check("A can list it", aid in [x["id"] for x in c.get("/v1/analyses", headers=A).json()])
check("A can open it (200)", c.get(f"/v1/analyses/{aid}", headers=A).status_code == 200)

rb = c.get("/v1/analyses", headers=B)
check("B's list does NOT contain A's analysis", rb.status_code == 200 and aid not in [x["id"] for x in rb.json()], rb.text[:150])
check("B cannot open A's analysis (404)", c.get(f"/v1/analyses/{aid}", headers=B).status_code == 404)
check("B cannot delete A's analysis (404)", c.delete(f"/v1/analyses/{aid}", headers=B).status_code == 404)
r = c.post("/v1/analyses", headers=B, json={"title": "sneaky", "stage": "stage2", "input": STAGE2, "parent_id": aid})
check("B cannot attach a new version to A's analysis (422)", r.status_code == 422, f"{r.status_code} {r.text[:150]}")

check("A's analysis survived B's attempts", c.get(f"/v1/analyses/{aid}", headers=A).status_code == 200)
check("cleanup: A deletes it (204)", c.delete(f"/v1/analyses/{aid}", headers=A).status_code == 204)

print("\nALL CHECKS PASSED" if not failures else f"\n{len(failures)} CHECK(S) FAILED: " + "; ".join(failures))
sys.exit(1 if failures else 0)
