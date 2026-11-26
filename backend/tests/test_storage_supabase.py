"""The Supabase store must call the database AS THE USER, never with a powerful key."""
import json
import uuid

import httpx
import pytest

from app.auth import User
from app.storage import StorageDenied, StorageError, SupabaseStore

USER = User(id=str(uuid.uuid4()), token="the-users-own-token")
ANON = "public-anon-key"


def store_with(handler):
    client = httpx.Client(base_url="https://x.supabase.co/rest/v1", transport=httpx.MockTransport(handler))
    return SupabaseStore("https://x.supabase.co", ANON, client)


def test_every_call_runs_as_the_user():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=[], headers={"content-range": "*/0"})

    s = store_with(handler)
    s.list(USER, 20, 0); s.get(USER, uuid.uuid4()); s.delete(USER, uuid.uuid4()); s.count(USER)
    assert len(seen) == 4
    for r in seen:
        assert r.headers["authorization"] == "Bearer the-users-own-token"
        assert r.headers["apikey"] == ANON


def test_insert_never_sends_user_id():
    sent = {}

    def handler(request):
        sent["body"] = json.loads(request.content)
        sent["prefer"] = request.headers["prefer"]
        return httpx.Response(201, json=[{"id": "abc", **sent["body"]}])

    store_with(handler).create(USER, {"title": "t", "stage": "stage2", "input": {}, "result": {}, "band": "Low", "probability": 0.1})
    assert "user_id" not in sent["body"] and sent["prefer"] == "return=representation"


def test_ids_are_sent_as_query_parameters():
    seen = []
    s = store_with(lambda r: (seen.append(r), httpx.Response(200, json=[]))[1])
    target = uuid.uuid4()
    s.get(USER, target)
    assert seen[0].url.params["id"] == f"eq.{target}" and seen[0].url.path.endswith("/analyses")


def test_delete_reports_whether_anything_was_deleted():
    assert store_with(lambda r: httpx.Response(200, json=[{"id": "x"}])).delete(USER, uuid.uuid4()) is True
    assert store_with(lambda r: httpx.Response(200, json=[])).delete(USER, uuid.uuid4()) is False


def test_count_reads_content_range():
    assert store_with(lambda r: httpx.Response(200, headers={"content-range": "0-0/7"})).count(USER) == 7
    assert store_with(lambda r: httpx.Response(200, headers={"content-range": "*/0"})).count(USER) == 0


def test_evidence_snapshot_queries_use_user_token_and_deterministic_latest_order():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=[])

    s = store_with(handler)
    analysis_id = uuid.uuid4()
    s.get_latest_evidence_snapshot(USER, analysis_id, "Industry", "Market")
    s.list_evidence_snapshots(USER, analysis_id, "Industry", "Market", 20)
    assert len(seen) == 2
    for request in seen:
        assert request.url.path.endswith("/evidence_snapshots")
        assert request.url.params["analysis_id"] == f"eq.{analysis_id}"
        assert request.url.params["order"] == "created_at.desc,id.desc"
        assert request.headers["authorization"] == "Bearer the-users-own-token"


def test_snapshot_insert_and_exact_history_read_preserve_snapshot_identity():
    seen = []
    snapshot_id = str(uuid.uuid4())
    analysis_id = str(uuid.uuid4())

    def handler(request):
        seen.append(request)
        if request.method == "POST":
            return httpx.Response(201, json=[{"id": snapshot_id, **json.loads(request.content)}])
        return httpx.Response(200, json=[{"id": snapshot_id, "analysis_id": analysis_id, "payload": {"state": "partial"}}])

    s = store_with(handler)
    created = s.save_evidence_snapshot(USER, {"analysis_id": analysis_id, "node": "Industry", "focus": "Market", "payload": {"state": "partial"}})
    loaded = s.get_evidence_snapshot(USER, uuid.UUID(analysis_id), uuid.UUID(snapshot_id))
    assert created["id"] == snapshot_id and "user_id" not in json.loads(seen[0].content)
    assert seen[1].url.params["id"] == f"eq.{snapshot_id}"
    assert loaded["payload"]["state"] == "partial"


def test_rls_refusal_becomes_storage_denied():
    body = {"code": "42501", "message": "new row violates row-level security policy"}
    with pytest.raises(StorageDenied):
        store_with(lambda r: httpx.Response(403, json=body)).create(USER, {})


def test_database_errors_become_storage_error_without_leaking_details():
    with pytest.raises(StorageError) as e:
        store_with(lambda r: httpx.Response(500, text="secret internal detail")).list(USER, 1, 0)
    assert "secret" not in str(e.value)


def test_unreachable_database_becomes_storage_error():
    def handler(request):
        raise httpx.ConnectError("down")
    with pytest.raises(StorageError):
        store_with(handler).list(USER, 1, 0)


def test_delete_all_runs_as_the_user_and_only_filters_on_their_own_id():
    seen = {}

    def handler(request):
        seen["req"] = request
        return httpx.Response(200, json=[{"id": "a"}, {"id": "b"}, {"id": "c"}])

    assert store_with(handler).delete_all(USER) == 3
    r = seen["req"]
    assert r.method == "DELETE" and r.url.params["user_id"] == f"eq.{USER.id}"
    assert r.headers["authorization"] == "Bearer the-users-own-token" and r.headers["apikey"] == ANON


def test_evidence_association_storage_is_owner_scoped_and_snapshot_filterable():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=[])

    s = store_with(handler)
    analysis_id, snapshot_id = uuid.uuid4(), uuid.uuid4()
    assert s.list_evidence_associations(USER, analysis_id, snapshot_id, 20) == []
    request = seen[0]
    assert request.url.path.endswith("/evidence_associations")
    assert request.url.params["analysis_id"] == f"eq.{analysis_id}"
    assert request.url.params["snapshot_id"] == f"eq.{snapshot_id}"
    assert request.headers["authorization"] == "Bearer the-users-own-token"


def test_evidence_association_and_contradiction_writes_use_user_token_without_user_id():
    seen = []

    def handler(request):
        seen.append(request)
        body = json.loads(request.content)
        return httpx.Response(201, json=[{"id": body["id"], **body}])

    s = store_with(handler)
    analysis_id, snapshot_id, association_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    association = {"id": str(uuid.uuid4()), "analysis_id": str(analysis_id), "snapshot_id": str(snapshot_id),
                   "supersedes_record_id": None, "payload": {"example": True}}
    s.save_evidence_association(USER, association)
    contradiction = {"id": str(uuid.uuid4()), "analysis_id": str(analysis_id),
                     "association_ids": [str(association_id), str(uuid.uuid4())],
                     "supersedes_record_id": None,
                     "payload": {"record_id": "versioned-comparison", "analysis_id": str(analysis_id),
                                 "contract_version": "1.0", "nature": "insufficient_information"}}
    s.save_contradiction_assessment(USER, contradiction)
    assert seen[0].url.path.endswith("/evidence_associations")
    assert seen[1].url.path.endswith("/evidence_contradictions")
    for request in seen:
        assert request.headers["authorization"] == "Bearer the-users-own-token"
        assert "user_id" not in json.loads(request.content)
    assert json.loads(seen[1].content)["association_1_id"] == str(association_id)
    assert json.loads(seen[1].content)["payload"] == contradiction["payload"]
    assert "association_ids" not in json.loads(seen[1].content)["payload"]


def test_contradiction_pair_lookup_is_analysis_scoped_and_order_independent():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=[])

    s = store_with(handler)
    analysis_id, first, second = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    assert s.find_contradiction_for_pair(USER, analysis_id, first, second) is None
    request = seen[0]
    assert request.url.path.endswith("/evidence_contradictions")
    assert request.url.params["analysis_id"] == f"eq.{analysis_id}"
    assert "association_1_id.eq." in request.url.params["or"]
    assert "association_2_id.eq." in request.url.params["or"]
    assert request.headers["authorization"] == "Bearer the-users-own-token"


def test_concurrent_comparison_unique_conflict_is_returned_as_safe_storage_denial():
    from app.storage import StorageDenied

    s = store_with(lambda _request: httpx.Response(409, json={"message": "private payload omitted"}))
    record = {"id": str(uuid.uuid4()), "analysis_id": str(uuid.uuid4()),
              "association_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
              "supersedes_record_id": None, "payload": {"detection_method": "deterministic_excerpt_rules"}}
    with pytest.raises(StorageDenied):
        s.save_contradiction_assessment(USER, record)
