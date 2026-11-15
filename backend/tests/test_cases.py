"""The failure-case library (real startups, real sources), its retrieval, and what the API keeps private."""
import json
import re
from datetime import date
from urllib.parse import urlparse

import pytest

from app import cases
from conftest import USER_A, USER_B, headers_for

LIB = cases.load()
MODEL_TAGS = set(json.load(open(cases.LIBRARY.parent.parent / "models" / "model_config.json"))["stages"]["stage1"]["tags"])
REASONS_OK = re.compile(r"^[A-Z][A-Za-z ()\-]{3,40}$")
HOSTS = {"venturebeat.com", "fortune.com", "www.fortune.com", "medium.com", "www.entrepreneur.com", "www.nbcnews.com", "www.agbi.com", "sifted.eu",
         "businesstoday.in", "petapixel.com", "www.axios.com", "hlth.com", "techcrunch.com", "www.agtechnavigator.com"}


# ---- the library itself: every entry must be checkable by a reader ---------------------------------
def test_library_is_not_empty_and_ids_are_unique():
    assert len(LIB) >= 8 and len({c["id"] for c in LIB}) == len(LIB)


@pytest.mark.parametrize("c", LIB, ids=lambda c: c["id"])
def test_every_case_is_complete_and_sourced(c):
    for field in ("name", "years", "sector", "what", "how_it_failed", "reasons", "industries", "keywords", "sources", "verified_on"):
        assert c[field], f"{c['id']}: {field} is empty"
    assert 80 <= len(c["how_it_failed"]) <= 420 and len(c["what"]) <= 140
    assert '"' not in c["how_it_failed"] and "\u201c" not in c["how_it_failed"], "paraphrase, do not quote"
    assert 1 <= len(c["reasons"]) <= 3 and all(REASONS_OK.match(r) for r in c["reasons"])
    assert set(c["industries"]) <= MODEL_TAGS, set(c["industries"]) - MODEL_TAGS
    date.fromisoformat(c["verified_on"])
    for src in c["sources"]:
        u = urlparse(src["url"])
        assert u.scheme == "https" and u.hostname in HOSTS and not u.query and not u.fragment, src["url"]
        assert src["title"] and src["publisher"] and src["kind"] in {"news report", "post-mortem", "research report"}
        assert re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", src["published"])
        assert src["published"] <= c["verified_on"]


def test_library_has_recent_sources():
    newest = max(s["published"] for c in LIB for s in c["sources"])
    assert newest >= "2025-01"            # the library is not only old stories


# ---- retrieval ---------------------------------------------------------------------------------
def test_exact_industry_match_comes_first():
    found, matched = cases.retrieve(LIB, ["Photography"])
    assert matched and found[0]["id"] == "everpix" and found[0]["matched_on"] == ["Industry: Photography"]
    assert cases.retrieve(LIB, ["Health Care"])[0][0]["id"] == "pear"


def test_related_field_alone_is_not_enough_to_claim_a_match():
    found, _ = cases.retrieve(LIB, ["Social Media"], limit=5)
    assert found == []


def test_the_idea_text_can_break_a_tie():
    base, _ = cases.retrieve(LIB, ["Software"], {}, limit=3)
    boosted, _ = cases.retrieve(LIB, ["Software"], {"concept": "a hardware gadget with an assistant for consumers"}, limit=3)
    assert boosted[0]["id"] == "humane" and base[0]["id"] != "humane"
    assert any(m.startswith("Idea terms") for m in boosted[0]["matched_on"])


def test_nothing_similar_does_not_show_unrelated_general_lessons():
    found, matched = cases.retrieve(LIB, ["Some Unknown Tag"])
    assert not matched and found == []


def test_limit_order_and_determinism():
    a = cases.retrieve(LIB, ["Software", "Mobile"], {"concept": "photo app"}, limit=2)
    assert a == cases.retrieve(LIB, ["Software", "Mobile"], {"concept": "photo app"}, limit=2) and len(a[0]) == 2
    assert len(cases.retrieve(LIB, ["Software"], limit=5)[0]) <= 5


def test_private_keywords_never_leave():
    found, _ = cases.retrieve(LIB, ["Software"])
    assert all("keywords" not in c and "industries" not in c for c in found)


# ---- the API --------------------------------------------------------------------------------------
def make(client, tags=("Photography",), headers=None, ctx=None):
    body = {"title": "t", "stage": "stage1", "input": {"country": "USA", "state": "CA", "tags": list(tags)}}
    if ctx:
        body["context"] = ctx
    return client.post("/v1/analyses", json=body, headers=headers or headers_for(USER_A)).json()["id"]


def test_cases_endpoint_returns_sources_for_my_analysis(client):
    aid = make(client)
    r = client.get(f"/v1/analyses/{aid}/cases", headers=headers_for(USER_A))
    assert r.status_code == 200
    body = r.json()
    assert body["matched"] and body["cases"][0]["name"] == "Everpix" and body["cases"][0]["sources"][0]["url"].startswith("https://")
    assert "not predictions" in body["note"]
    assert "keywords" not in r.text


def test_cases_use_the_founders_notes_too(client):
    aid = make(client, ("Software",), ctx={"concept": "a wearable gadget with a voice assistant"})
    assert client.get(f"/v1/analyses/{aid}/cases?limit=1", headers=headers_for(USER_A)).json()["cases"][0]["name"] == "Humane"


def test_cases_need_login_and_respect_ownership(client, anon_client):
    aid = make(client)
    assert anon_client.get(f"/v1/analyses/{aid}/cases").status_code in (401, 403)
    assert client.get(f"/v1/analyses/{aid}/cases", headers=headers_for(USER_B)).status_code == 404
    assert client.get("/v1/analyses/not-a-uuid/cases", headers=headers_for(USER_A)).status_code == 422
    assert client.get(f"/v1/analyses/{aid}/cases?limit=99", headers=headers_for(USER_A)).status_code == 422


# ---- privacy of our data -------------------------------------------------------------------------
LEAKS = re.compile(r"2013|10,?941|\b922\b|\bAUC\b|auc|cv_|test_auc|observed_failure|failed_share|US startups|American|Crunchbase|\"rows\"", re.I)


def test_meta_exposes_only_what_the_forms_need(client):
    r = client.get("/v1/meta")
    assert r.status_code == 200 and not LEAKS.search(r.text), LEAKS.search(r.text)
    inputs = r.json()["stages"]["stage1"]["inputs"]
    assert set(inputs) == {"countries", "states", "tags", "notes"} and len(inputs["tags"]) > 100


def test_no_prediction_or_saved_analysis_leaks_dataset_details(client):
    from test_api import STAGE2_OK
    texts = [client.post("/v1/predict/stage1", json={"country": "USA", "state": "CA", "tags": ["Software"]}).text,
             client.post("/v1/predict/stage2", json=STAGE2_OK).text]
    aid = make(client)
    texts.append(client.get(f"/v1/analyses/{aid}", headers=headers_for(USER_A)).text)
    for t in texts:
        assert not LEAKS.search(t), LEAKS.search(t)
        assert "base_failure_rate" not in t


# ---- delete everything (Settings) ------------------------------------------------------------------
def test_delete_all_removes_only_my_analyses(client, anon_client):
    a1, a2, b1 = make(client), make(client), make(client, headers=headers_for(USER_B))
    r = client.delete("/v1/analyses", headers=headers_for(USER_A))
    assert r.status_code == 200 and r.json() == {"deleted": 2}
    assert client.get("/v1/analyses", headers=headers_for(USER_A)).json() == []
    assert client.get(f"/v1/analyses/{b1}", headers=headers_for(USER_B)).status_code == 200      # not touched
    assert client.delete("/v1/analyses", headers=headers_for(USER_A)).json() == {"deleted": 0}
    assert anon_client.delete("/v1/analyses").status_code in (401, 403)
