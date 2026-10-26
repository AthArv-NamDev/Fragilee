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
