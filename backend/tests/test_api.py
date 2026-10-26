"""Run from backend/:   pytest -q     (needs models/ from scripts/train.py)"""
import json
import shutil

import pandas as pd
import pytest

from app.features import BANDS, build_stage1, build_stage2
from app.model_store import ModelStore
from app.settings import MODELS_DIR

pytestmark = pytest.mark.skipif(not (MODELS_DIR / "model_config.json").exists(),
                                reason="run scripts/train.py first")

GROUPS = {"Funding", "Traction", "Market", "Location"}
STAGE2_OK = {"category": "software", "state": "CA", "funding_total_usd": 250000, "funding_rounds": 2,
             "has_VC": False, "has_angel": True, "has_roundA": True, "has_roundB": False, "has_roundC": False,
             "has_roundD": False, "avg_participants": 2.0, "relationships": 5,
             "age_first_funding_year": 1.0, "age_last_funding_year": 2.0}


@pytest.fixture(scope="module")
def meta(client):
    return client.get("/v1/meta").json()


def stage1_ok(meta):
    return {"country": "USA", "state": "CA", "tags": [meta["stages"]["stage1"]["inputs"]["tags"][0]]}


def check_response(d):
    assert d["band"] in BANDS and 0 <= d["probability"] <= 1
    assert d["tree"]["band"] == d["band"]
    assert {b["group"] for b in d["tree"]["children"]} <= GROUPS
    assert all(b["band"] in BANDS for b in d["tree"]["children"])
    assert d["disclaimer"] and d["limitations"]


# ---- happy paths -----------------------------------------------------------
def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "no-store"


def test_stage1_prediction(client, meta):
    r = client.post("/v1/predict/stage1", json=stage1_ok(meta))
    assert r.status_code == 200
    check_response(r.json())
    assert r.json()["confidence"] == "limited"


def test_stage2_prediction(client):
    r = client.post("/v1/predict/stage2", json=STAGE2_OK)
    assert r.status_code == 200
    check_response(r.json())


def test_same_input_same_answer(client):
    a = client.post("/v1/predict/stage2", json=STAGE2_OK).json()
    b = client.post("/v1/predict/stage2", json=STAGE2_OK).json()
    assert a == b


def test_non_us_country_needs_no_state(client, meta):
    body = {"country": "IND", "tags": [meta["stages"]["stage1"]["inputs"]["tags"][0]]}
    assert client.post("/v1/predict/stage1", json=body).status_code == 200


def test_out_of_range_value_adds_note_and_lowers_confidence(client):
    r = client.post("/v1/predict/stage2", json={**STAGE2_OK, "funding_total_usd": 5e10}).json()
    assert r["confidence"] == "low" and r["notes"]


def test_docs_examples_are_valid(client):
    """The pre-filled example in /docs must work, so 'Try it out' succeeds on the first click."""
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    for name, url in [("Stage1Request", "/v1/predict/stage1"), ("Stage2Request", "/v1/predict/stage2")]:
        example = schema[name]["examples"][0]
        assert client.post(url, json=example).status_code == 200, name


# ---- bad input is refused ---------------------------------------------------
@pytest.mark.parametrize("change", [
    {"funding_total_usd": -1}, {"funding_rounds": 0}, {"relationships": 10_000},
    {"has_VC": "yes"}, {"surprise_field": 1}, {"age_last_funding_year": -5, "age_first_funding_year": 3},
    {"category": "not-a-category"}, {"state": "California"},
])
def test_stage2_rejects_bad_input(client, change):
    assert client.post("/v1/predict/stage2", json={**STAGE2_OK, **change}).status_code == 422


def test_stage2_rejects_missing_field(client):
    body = dict(STAGE2_OK)
    body.pop("relationships")
    assert client.post("/v1/predict/stage2", json=body).status_code == 422


@pytest.mark.parametrize("body", [
    {"country": "USA", "tags": ["Software"]},                              # state missing
    {"country": "IND", "state": "CA", "tags": ["Software"]},               # state for non-US
    {"country": "USA", "state": "CA", "tags": []},                         # no tags
    {"country": "USA", "state": "CA", "tags": ["a"] * 6},                  # too many tags
    {"country": "USA", "state": "CA", "tags": ["Definitely Not A Tag"]},   # unknown tag
    {"country": "United States", "state": "CA", "tags": ["Software"]},     # not a 3-letter code
    {"country": "USA", "state": "CA", "tags": ["Software"], "x": 1},       # extra field
])
def test_stage1_rejects_bad_input(client, body):
    assert client.post("/v1/predict/stage1", json=body).status_code == 422


def test_huge_request_refused(client):
    r = client.post("/v1/predict/stage1", content=b"x" * 50_000, headers={"content-type": "application/json"})
    assert r.status_code == 413


def test_injection_text_is_just_rejected(client):
    body = {"country": "USA", "state": "CA", "tags": ["'; DROP TABLE users;--"]}
    assert client.post("/v1/predict/stage1", json=body).status_code == 422


# ---- model integrity ---------------------------------------------------------
def test_tampered_model_file_is_refused(tmp_path):  # noqa: E302
    shutil.copytree(MODELS_DIR, tmp_path / "m")
    f = tmp_path / "m" / "stage2.json"
    f.write_bytes(f.read_bytes() + b" ")
    with pytest.raises(RuntimeError, match="hash"):
        ModelStore(tmp_path / "m")


def test_feature_columns_match_trained_model():
    cfg = json.loads((MODELS_DIR / "model_config.json").read_text())
    e1, e2 = cfg["stages"]["stage1"], cfg["stages"]["stage2"]
    x1 = build_stage1(pd.DataFrame([{"country": "USA", "state": "CA", "tags": e1["tags"][0]}]),
                      e1["countries"], e1["states"], e1["tags"])
    x2 = build_stage2(pd.DataFrame([{**STAGE2_OK, "category": e2["categories"][0], "state": "CA"}]),
                      e2["numeric"], e2["categories"], e2["states"])
    assert list(x1.columns) == e1["features"] and list(x2.columns) == e2["features"]
