"""Simple load test: many users hitting predict, save and list at once.

Setup: sign in as a test user to get an access token (see the instructions), then:
    TOKEN=<access token> python scripts/loadtest.py http://127.0.0.1:8000 40 6
        (server URL, simultaneous users, rounds per user)

The server enforces rate limits per user, and this test uses ONE token, so start the server with high limits:
    RATE_LIMIT_PREDICT=100000/minute RATE_LIMIT_READ=100000/minute RATE_LIMIT_IP=1000000/minute
Saved analyses pile up in that user's history. Delete them afterwards, and do not run this against a
deployment you do not own.
"""
import concurrent.futures as cf
import os
import statistics
import sys
import time

import httpx

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
USERS = int(sys.argv[2]) if len(sys.argv) > 2 else 40
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 6
TOKEN = os.environ.get("TOKEN") or sys.exit("Set TOKEN=<access token>")
H = {"Authorization": f"Bearer {TOKEN}"}
STAGE2 = {"category": "software", "state": "CA", "funding_total_usd": 250000, "funding_rounds": 2, "has_VC": False,
          "has_angel": True, "has_roundA": True, "has_roundB": False, "has_roundC": False, "has_roundD": False,
          "avg_participants": 2.0, "relationships": 5, "age_first_funding_year": 1.0, "age_last_funding_year": 2.0}


def one_user(_):
    lat, bad = [], {}
    with httpx.Client(base_url=URL, timeout=60, headers=H) as c:
        for _ in range(ROUNDS):
            calls = (lambda: c.post("/v1/predict/stage2", json=STAGE2),
                     lambda: c.post("/v1/analyses", json={"title": "load test", "stage": "stage2", "input": STAGE2}),
                     lambda: c.get("/v1/analyses"))
            for call in calls:
                t = time.perf_counter()
                r = call()
                lat.append((time.perf_counter() - t) * 1000)
                if r.status_code not in (200, 201):
                    bad[r.status_code] = bad.get(r.status_code, 0) + 1
    return lat, bad


t0 = time.perf_counter()
with cf.ThreadPoolExecutor(USERS) as ex:
    results = list(ex.map(one_user, range(USERS)))
dt = time.perf_counter() - t0
lat = sorted(x for l, _ in results for x in l)
errors = {}
for _, b in results:
    for k, v in b.items():
        errors[k] = errors.get(k, 0) + v
print(f"{USERS} users at once, {len(lat)} requests in {dt:.1f}s = {len(lat) / dt:.0f} requests/s")
print(f"median {statistics.median(lat):.0f} ms | 95th percentile {lat[int(0.95 * len(lat))]:.0f} ms | slowest {lat[-1]:.0f} ms")
print("errors:", errors or "none")
