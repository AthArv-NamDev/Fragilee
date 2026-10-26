"""Saved analyses: ownership, versions, limits and input checks."""
import uuid

import pytest

from app import settings
from conftest import USER_A, USER_B, headers_for

STAGE2 = {"category": "software", "state": "CA", "funding_total_usd": 250000, "funding_rounds": 2,
          "has_VC": False, "has_angel": True, "has_roundA": True, "has_roundB": False, "has_roundC": False,
          "has_roundD": False, "avg_participants": 2.0, "relationships": 5,
          "age_first_funding_year": 1.0, "age_last_funding_year": 2.0}


def make(client, headers=None, **over):
    body = {"title": "Coffee box", "stage": "stage2", "input": STAGE2, **over}
    return client.post("/v1/analyses", json=body, headers=headers)


def test_create_list_get_delete(anon_client):
    ha = headers_for(USER_A)
    created = make(anon_client, ha)
    assert created.status_code == 201
    row = created.json()
    assert "user_id" not in row                       # internal fields never leave the server
    assert row["band"] in ("Low", "Medium", "High", "Critical") and row["result"]["tree"]["children"]
    assert [a["id"] for a in anon_client.get("/v1/analyses", headers=ha).json()] == [row["id"]]
    assert "result" not in anon_client.get("/v1/analyses", headers=ha).json()[0]    # the list is a light summary
    assert anon_client.get(f"/v1/analyses/{row['id']}", headers=ha).json()["result"] == row["result"]
    assert anon_client.delete(f"/v1/analyses/{row['id']}", headers=ha).status_code == 204
    assert anon_client.get(f"/v1/analyses/{row['id']}", headers=ha).status_code == 404


def test_users_cannot_see_or_delete_each_others_analyses(anon_client):
    ha, hb = headers_for(USER_A), headers_for(USER_B)
    mine = make(anon_client, ha).json()
    assert anon_client.get("/v1/analyses", headers=hb).json() == []
    assert anon_client.get(f"/v1/analyses/{mine['id']}", headers=hb).status_code == 404
    assert anon_client.delete(f"/v1/analyses/{mine['id']}", headers=hb).status_code == 404
    assert anon_client.get(f"/v1/analyses/{mine['id']}", headers=ha).status_code == 200      # still there


def test_new_version_links_to_the_original(anon_client):
    ha = headers_for(USER_A)
    first = make(anon_client, ha).json()
    second = make(anon_client, ha, title="Coffee box v2", parent_id=first["id"])
    assert second.status_code == 201 and second.json()["parent_id"] == first["id"]


def test_cannot_use_someone_elses_analysis_as_parent(anon_client):
    theirs = make(anon_client, headers_for(USER_B)).json()
    r = make(anon_client, headers_for(USER_A), parent_id=theirs["id"])
    assert r.status_code == 422
    r = make(anon_client, headers_for(USER_A), parent_id=str(uuid.uuid4()))
    assert r.status_code == 422


def test_saved_stage1_analysis(anon_client):
    tag = anon_client.get("/v1/meta").json()["stages"]["stage1"]["inputs"]["tags"][0]
    r = make(anon_client, headers_for(USER_A), stage="stage1", input={"country": "USA", "state": "CA", "tags": [tag]})
    assert r.status_code == 201 and r.json()["stage"] == "stage1"


@pytest.mark.parametrize("change", [
    {"stage": "stage1"},                                    # stage2 fields sent as stage1
    {"input": {**STAGE2, "funding_total_usd": -5}},
    {"input": {**STAGE2, "surprise": 1}},
    {"title": ""}, {"title": "x" * 81}, {"title": "bad\x00title"}, {"title": "line\nbreak"},
    {"extra": "field"}, {"parent_id": "not-a-uuid"}, {"stage": "stage9"},
])
def test_bad_save_requests_are_refused(anon_client, change):
    assert make(anon_client, headers_for(USER_A), **change).status_code == 422


def test_422_details_name_the_field(anon_client):
    r = make(anon_client, headers_for(USER_A), input={**STAGE2, "funding_total_usd": -5})
    assert r.json()["detail"][0]["loc"] == ["body", "input", "funding_total_usd"]


def test_free_analysis_limit(anon_client, monkeypatch):
    monkeypatch.setattr(settings, "FREE_ANALYSIS_LIMIT", 2)
    ha = headers_for(USER_A)
    assert [make(anon_client, ha).status_code for _ in range(3)] == [201, 201, 403]
    assert make(anon_client, headers_for(USER_B)).status_code == 201      # the cap is per account
    first = anon_client.get("/v1/analyses", headers=ha).json()[0]["id"]
    anon_client.delete(f"/v1/analyses/{first}", headers=ha)
    assert make(anon_client, ha).status_code == 201                        # deleting frees a slot


def test_pagination(anon_client):
    ha = headers_for(USER_A)
    for i in range(3):
        make(anon_client, ha, title=f"t{i}")
    assert len(anon_client.get("/v1/analyses?limit=2", headers=ha).json()) == 2
    assert len(anon_client.get("/v1/analyses?limit=2&offset=2", headers=ha).json()) == 1
    for bad in ("limit=0", "limit=500", "offset=-1", "limit=abc"):
        assert anon_client.get(f"/v1/analyses?{bad}", headers=ha).status_code == 422


def test_bad_ids_are_refused(anon_client):
    ha = headers_for(USER_A)
    assert anon_client.get("/v1/analyses/not-a-uuid", headers=ha).status_code == 422
    assert anon_client.get("/v1/analyses/1;drop table analyses", headers=ha).status_code == 422
