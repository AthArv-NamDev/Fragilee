"""Where saved analyses live.

SupabaseStore talks to the database as the signed-in USER (it forwards their token), so Postgres
row-level security enforces 'only your own rows' independently of this code. MemoryStore is for tests.
"""
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Protocol

import httpx

from . import settings
from .auth import User

log = logging.getLogger("fragilee.storage")
SUMMARY_COLUMNS = "id,stage,title,band,probability,parent_id,created_at"


class StorageError(RuntimeError):
    """The database could not be reached or answered with an error."""


class StorageDenied(RuntimeError):
    """The database refused the write (for example a parent that is not yours)."""


class AnalysisStore(Protocol):
    def create(self, user: User, record: dict) -> dict: ...
    def list(self, user: User, limit: int, offset: int) -> list[dict]: ...
    def get(self, user: User, analysis_id: uuid.UUID) -> dict | None: ...
    def delete(self, user: User, analysis_id: uuid.UUID) -> bool: ...
    def count(self, user: User) -> int: ...


class MemoryStore:
    """Same behaviour as the database, kept in a dict. Used by the tests."""

    def __init__(self):
        self._rows: dict[str, dict] = {}

    def create(self, user, record):
        parent = record.get("parent_id")
        if parent and self._rows.get(str(parent), {}).get("user_id") != user.id:
            raise StorageDenied("parent not found")
        row = {**record, "id": str(uuid.uuid4()), "user_id": user.id,
               "created_at": datetime.now(timezone.utc).isoformat()}
        self._rows[row["id"]] = row
        return dict(row)

    def _mine(self, user):
        return sorted((r for r in self._rows.values() if r["user_id"] == user.id),
                      key=lambda r: r["created_at"], reverse=True)

    def list(self, user, limit, offset):
        keys = SUMMARY_COLUMNS.split(",")
        return [{k: r[k] for k in keys} for r in self._mine(user)[offset: offset + limit]]

    def get(self, user, analysis_id):
        r = self._rows.get(str(analysis_id))
        return dict(r) if r and r["user_id"] == user.id else None

    def delete(self, user, analysis_id):
        if self.get(user, analysis_id) is None:
            return False
        del self._rows[str(analysis_id)]
        return True

    def count(self, user):
        return len(self._mine(user))


class SupabaseStore:
    def __init__(self, url: str, anon_key: str, client: httpx.Client | None = None):
        self._client = client or httpx.Client(base_url=f"{url}/rest/v1", timeout=8.0)
        self._anon_key = anon_key

    def close(self):
        self._client.close()

    def _headers(self, user: User, **extra) -> dict:
        # apikey identifies the project. Authorization makes the database treat us AS this user.
        return {"apikey": self._anon_key, "Authorization": f"Bearer {user.token}", **extra}

    def _send(self, method: str, user: User, params: dict | None = None, json=None, **headers) -> httpx.Response:
        try:
            r = self._client.request(method, "/analyses", params=params, json=json, headers=self._headers(user, **headers))
        except httpx.HTTPError as e:
            log.error("database unreachable: %s", type(e).__name__)
            raise StorageError("Storage unavailable") from e
        if r.status_code in (401, 403) and "42501" in r.text:
            raise StorageDenied("row-level security refused the write")
        if r.status_code >= 400:
            log.error("database error status=%s body=%s", r.status_code, r.text[:200])
            raise StorageError("Storage error")
        return r

    def create(self, user, record):
        r = self._send("POST", user, json=record, Prefer="return=representation")   # no user_id: the database fills it in
        rows = r.json()
        if not rows:
            raise StorageError("Storage returned nothing")
        return rows[0]

    def list(self, user, limit, offset):
        params = {"select": SUMMARY_COLUMNS, "order": "created_at.desc", "limit": limit, "offset": offset}
        return self._send("GET", user, params=params).json()

    def get(self, user, analysis_id):
        rows = self._send("GET", user, params={"id": f"eq.{analysis_id}", "select": "*"}).json()
        return rows[0] if rows else None

    def delete(self, user, analysis_id):
        rows = self._send("DELETE", user, params={"id": f"eq.{analysis_id}"}, Prefer="return=representation").json()
        return bool(rows)

    def count(self, user):
        r = self._send("HEAD", user, params={"select": "id"}, Prefer="count=exact")
        m = re.search(r"/(\d+)$", r.headers.get("content-range", ""))
        return int(m.group(1)) if m else 0


def make_store() -> AnalysisStore:
    if settings.STORAGE == "memory":
        return MemoryStore()
    return SupabaseStore(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
