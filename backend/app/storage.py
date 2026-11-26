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
from .evidence_contract import ContradictionAssessment, EvidenceAssociation, validate_evidence_association

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
    def delete_all(self, user: User) -> int: ...
    def get_latest_evidence_snapshot(self, user: User, analysis_id: uuid.UUID, node: str, focus: str) -> dict | None: ...
    def list_evidence_snapshots(self, user: User, analysis_id: uuid.UUID, node: str, focus: str, limit: int) -> list[dict]: ...
    def get_evidence_snapshot(self, user: User, analysis_id: uuid.UUID, snapshot_id: uuid.UUID) -> dict | None: ...
    def save_evidence_snapshot(self, user: User, record: dict) -> dict: ...
    def list_evidence_associations(self, user: User, analysis_id: uuid.UUID, snapshot_id: uuid.UUID | None = None, limit: int = 100) -> list[dict]: ...
    def get_evidence_association(self, user: User, analysis_id: uuid.UUID, record_id: uuid.UUID) -> dict | None: ...
    def save_evidence_association(self, user: User, record: dict) -> dict: ...
    def list_contradiction_assessments(self, user: User, analysis_id: uuid.UUID, limit: int = 100) -> list[dict]: ...
    def find_contradiction_for_pair(self, user: User, analysis_id: uuid.UUID, association_a: uuid.UUID, association_b: uuid.UUID) -> dict | None: ...
    def save_contradiction_assessment(self, user: User, record: dict) -> dict: ...
    def get_contradiction_assessment(self, user: User, analysis_id: uuid.UUID, record_id: uuid.UUID) -> dict | None: ...


class MemoryStore:
    """Same behaviour as the database, kept in a dict. Used by the tests."""

    def __init__(self):
        self._rows: dict[str, dict] = {}
        self._evidence_snapshots: list[dict] = []
        self._evidence_associations: list[dict] = []
        self._contradiction_assessments: list[dict] = []

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
        self._evidence_snapshots = [r for r in self._evidence_snapshots if r["analysis_id"] != str(analysis_id)]
        self._evidence_associations = [r for r in self._evidence_associations if r["analysis_id"] != str(analysis_id)]
        self._contradiction_assessments = [r for r in self._contradiction_assessments if r["analysis_id"] != str(analysis_id)]
        return True

    def count(self, user):
        return len(self._mine(user))

    def delete_all(self, user):
        mine = [r["id"] for r in self._mine(user)]
        for i in mine:
            del self._rows[i]
        mine_ids = set(mine)
        self._evidence_snapshots = [r for r in self._evidence_snapshots if r["analysis_id"] not in mine_ids]
        self._evidence_associations = [r for r in self._evidence_associations if r["analysis_id"] not in mine_ids]
        self._contradiction_assessments = [r for r in self._contradiction_assessments if r["analysis_id"] not in mine_ids]
        return len(mine)

    def get_latest_evidence_snapshot(self, user, analysis_id, node, focus):
        if self.get(user, analysis_id) is None:
            return None
        matches = [r for r in self._evidence_snapshots if r["analysis_id"] == str(analysis_id) and r["node"] == node and r["focus"] == focus]
        return dict(max(matches, key=lambda r: (r["created_at"], r["id"]))) if matches else None

    def list_evidence_snapshots(self, user, analysis_id, node, focus, limit):
        if self.get(user, analysis_id) is None:
            return []
        matches = [r for r in self._evidence_snapshots if r["analysis_id"] == str(analysis_id) and r["node"] == node and r["focus"] == focus]
        return [dict(row) for row in sorted(matches, key=lambda r: (r["created_at"], r["id"]), reverse=True)[:limit]]

    def get_evidence_snapshot(self, user, analysis_id, snapshot_id):
        if self.get(user, analysis_id) is None:
            return None
        row = next((r for r in self._evidence_snapshots if r["analysis_id"] == str(analysis_id) and r["id"] == str(snapshot_id)), None)
        return dict(row) if row else None

    def save_evidence_snapshot(self, user, record):
        if self.get(user, uuid.UUID(str(record["analysis_id"]))) is None:
            raise StorageDenied("analysis not found")
        row = {**record, "id": str(uuid.uuid4()), "user_id": user.id,
               "created_at": datetime.now(timezone.utc).isoformat()}
        self._evidence_snapshots.append(row)
        return dict(row)

    def list_evidence_associations(self, user, analysis_id, snapshot_id=None, limit=100):
        if self.get(user, analysis_id) is None:
            return []
        matches = [row for row in self._evidence_associations
                   if row["analysis_id"] == str(analysis_id)
                   and (snapshot_id is None or row["snapshot_id"] == str(snapshot_id))]
        return [dict(row) for row in sorted(matches, key=lambda row: (row["created_at"], row["id"]), reverse=True)[:limit]]

    def get_evidence_association(self, user, analysis_id, record_id):
        if self.get(user, analysis_id) is None:
            return None
        row = next((row for row in self._evidence_associations
                    if row["analysis_id"] == str(analysis_id) and row["id"] == str(record_id)), None)
        return dict(row) if row else None

    def save_evidence_association(self, user, record):
        analysis_id = uuid.UUID(str(record["analysis_id"]))
        if self.get(user, analysis_id) is None:
            raise StorageDenied("analysis not found")
        snapshot_id = uuid.UUID(str(record["snapshot_id"]))
        snapshot = self.get_evidence_snapshot(user, analysis_id, snapshot_id)
        if snapshot is None:
            raise StorageDenied("evidence snapshot not found")
        try:
            association = EvidenceAssociation.model_validate(record["payload"])
            if association.analysis_id != analysis_id or association.snapshot_id != snapshot_id:
                raise StorageDenied("association payload IDs do not match storage references")
            validate_evidence_association(association, snapshot)
        except ValueError as error:
            raise StorageDenied("evidence association failed snapshot validation") from error
        if any(row["id"] == str(record["id"]) for row in self._evidence_associations):
            raise StorageDenied("evidence association already exists")
        supersedes = record.get("supersedes_record_id")
        if supersedes:
            previous = self.get_evidence_association(user, analysis_id, uuid.UUID(str(supersedes)))
            if previous is None or any(row.get("supersedes_record_id") == str(supersedes) for row in self._evidence_associations):
                raise StorageDenied("correction target not found or already superseded")
            if previous["snapshot_id"] != str(record["snapshot_id"]):
                raise StorageDenied("correction must use the original snapshot")
        row = {**record, "user_id": user.id, "created_at": datetime.now(timezone.utc).isoformat()}
        self._evidence_associations.append(row)
        return dict(row)

    def list_contradiction_assessments(self, user, analysis_id, limit=100):
        if self.get(user, analysis_id) is None:
            return []
        matches = [row for row in self._contradiction_assessments if row["analysis_id"] == str(analysis_id)]
        return [dict(row) for row in sorted(matches, key=lambda row: (row["created_at"], row["id"]), reverse=True)[:limit]]

    def find_contradiction_for_pair(self, user, analysis_id, association_a, association_b):
        if self.get(user, analysis_id) is None:
            return None
        pair = {str(association_a), str(association_b)}
        matches = [row for row in self._contradiction_assessments
                   if row["analysis_id"] == str(analysis_id)
                   and set(row.get("association_ids", [])) == pair]
        return dict(max(matches, key=lambda row: (row["created_at"], row["id"]))) if matches else None

    def save_contradiction_assessment(self, user, record):
        analysis_id = uuid.UUID(str(record["analysis_id"]))
        if self.get(user, analysis_id) is None:
            raise StorageDenied("analysis not found")
        try:
            assessment = ContradictionAssessment.model_validate(record["payload"])
        except ValueError as error:
            raise StorageDenied("contradiction failed contract validation") from error
        if assessment.analysis_id != analysis_id or str(assessment.record_id) != str(record["id"]):
            raise StorageDenied("contradiction payload IDs do not match storage references")
        for association_id in record["association_ids"]:
            linked = self.get_evidence_association(user, analysis_id, uuid.UUID(str(association_id)))
            if linked is None or not (linked.get("payload") or {}).get("exact_passage_text"):
                raise StorageDenied("evidence association not found")
        supersedes = record.get("supersedes_record_id")
        if not supersedes:
            existing = self.find_contradiction_for_pair(user, analysis_id, *assessment.association_ids)
            if existing is not None:
                raise StorageDenied("comparison already exists for this evidence pair")
        if supersedes:
            previous = next((row for row in self._contradiction_assessments if row["analysis_id"] == str(analysis_id) and row["id"] == str(supersedes)), None)
            if previous is None or any(row.get("supersedes_record_id") == str(supersedes) for row in self._contradiction_assessments):
                raise StorageDenied("contradiction correction target not found or already superseded")
            if sorted(previous["association_ids"]) != sorted(record["association_ids"]):
                raise StorageDenied("contradiction correction must retain the original association pair")
        row = {**record, "user_id": user.id, "created_at": datetime.now(timezone.utc).isoformat()}
        self._contradiction_assessments.append(row)
        return dict(row)

    def get_contradiction_assessment(self, user, analysis_id, record_id):
        if self.get(user, analysis_id) is None:
            return None
        row = next((row for row in self._contradiction_assessments
                    if row["analysis_id"] == str(analysis_id) and row["id"] == str(record_id)), None)
        return dict(row) if row else None


class SupabaseStore:
    def __init__(self, url: str, anon_key: str, client: httpx.Client | None = None):
        self._client = client or httpx.Client(base_url=f"{url}/rest/v1", timeout=8.0)
        self._anon_key = anon_key

    def close(self):
        self._client.close()

    def _headers(self, user: User, **extra) -> dict:
        # apikey identifies the project. Authorization makes the database treat us AS this user.
        return {"apikey": self._anon_key, "Authorization": f"Bearer {user.token}", **extra}

    def _send(self, method: str, user: User, params: dict | None = None, json=None, *, table: str = "analyses", **headers) -> httpx.Response:
        try:
            r = self._client.request(method, f"/{table}", params=params, json=json, headers=self._headers(user, **headers))
        except httpx.HTTPError as e:
            log.error("database unreachable: %s", type(e).__name__)
            raise StorageError("Storage unavailable") from e
        if r.status_code in (401, 403) and "42501" in r.text:
            raise StorageDenied("row-level security refused the write")
        if r.status_code == 409 and table == "evidence_contradictions":
            # Let the API check whether a concurrent idempotent comparison won.
            # Keep the provider response body out of logs and exception text.
            raise StorageDenied("contradiction pair conflicts with an existing record")
        if r.status_code >= 400:
            # Responses may echo claim text or founder supplied evidence. Keep logs metadata-only.
            log.error("database error status=%s", r.status_code)
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

    def delete_all(self, user):
        rows = self._send("DELETE", user, params={"user_id": f"eq.{user.id}"}, Prefer="return=representation").json()
        return len(rows)

    def count(self, user):
        r = self._send("HEAD", user, params={"select": "id"}, Prefer="count=exact")
        m = re.search(r"/(\d+)$", r.headers.get("content-range", ""))
        return int(m.group(1)) if m else 0

    def get_latest_evidence_snapshot(self, user, analysis_id, node, focus):
        params = {"analysis_id": f"eq.{analysis_id}", "node": f"eq.{node}", "focus": f"eq.{focus}",
                  "select": "id,analysis_id,node,focus,payload,created_at", "order": "created_at.desc,id.desc", "limit": "1"}
        rows = self._send("GET", user, params=params, table="evidence_snapshots").json()
        return rows[0] if rows else None

    def list_evidence_snapshots(self, user, analysis_id, node, focus, limit):
        params = {"analysis_id": f"eq.{analysis_id}", "node": f"eq.{node}", "focus": f"eq.{focus}",
                  "select": "id,analysis_id,node,focus,payload,created_at", "order": "created_at.desc,id.desc", "limit": str(limit)}
        return self._send("GET", user, params=params, table="evidence_snapshots").json()

    def get_evidence_snapshot(self, user, analysis_id, snapshot_id):
        params = {"analysis_id": f"eq.{analysis_id}", "id": f"eq.{snapshot_id}",
                  "select": "id,analysis_id,node,focus,payload,created_at", "limit": "1"}
        rows = self._send("GET", user, params=params, table="evidence_snapshots").json()
        return rows[0] if rows else None

    def save_evidence_snapshot(self, user, record):
        r = self._send("POST", user, json=record, table="evidence_snapshots", Prefer="return=representation")
        rows = r.json()
        if not rows:
            raise StorageError("Storage returned nothing")
        return rows[0]

    def list_evidence_associations(self, user, analysis_id, snapshot_id=None, limit=100):
        params = {"analysis_id": f"eq.{analysis_id}", "select": "id,analysis_id,snapshot_id,supersedes_record_id,payload,created_at", "order": "created_at.desc,id.desc", "limit": str(limit)}
        if snapshot_id:
            params["snapshot_id"] = f"eq.{snapshot_id}"
        return self._send("GET", user, params=params, table="evidence_associations").json()

    def get_evidence_association(self, user, analysis_id, record_id):
        params = {"analysis_id": f"eq.{analysis_id}", "id": f"eq.{record_id}", "select": "id,analysis_id,snapshot_id,supersedes_record_id,payload,created_at", "limit": "1"}
        rows = self._send("GET", user, params=params, table="evidence_associations").json()
        return rows[0] if rows else None

    def save_evidence_association(self, user, record):
        body = {key: record[key] for key in ("id", "analysis_id", "snapshot_id", "supersedes_record_id", "payload")}
        rows = self._send("POST", user, json=body, table="evidence_associations", Prefer="return=representation").json()
        if not rows:
            raise StorageError("Storage returned nothing")
        return rows[0]

    def list_contradiction_assessments(self, user, analysis_id, limit=100):
        params = {"analysis_id": f"eq.{analysis_id}", "select": "id,analysis_id,association_1_id,association_2_id,supersedes_record_id,payload,created_at", "order": "created_at.desc,id.desc", "limit": str(limit)}
        return self._send("GET", user, params=params, table="evidence_contradictions").json()

    def find_contradiction_for_pair(self, user, analysis_id, association_a, association_b):
        pair_filter = (
            f"(and(association_1_id.eq.{association_a},association_2_id.eq.{association_b}),"
            f"and(association_1_id.eq.{association_b},association_2_id.eq.{association_a}))"
        )
        params = {"analysis_id": f"eq.{analysis_id}", "or": pair_filter,
                  "select": "id,analysis_id,association_1_id,association_2_id,supersedes_record_id,payload,created_at",
                  "order": "created_at.desc,id.desc", "limit": "1"}
        rows = self._send("GET", user, params=params, table="evidence_contradictions").json()
        return rows[0] if rows else None

    def save_contradiction_assessment(self, user, record):
        body = {"id": record["id"], "analysis_id": record["analysis_id"],
                "association_1_id": record["association_ids"][0], "association_2_id": record["association_ids"][1],
                "supersedes_record_id": record.get("supersedes_record_id"), "payload": record["payload"]}
        rows = self._send("POST", user, json=body, table="evidence_contradictions", Prefer="return=representation").json()
        if not rows:
            raise StorageError("Storage returned nothing")
        return rows[0]

    def get_contradiction_assessment(self, user, analysis_id, record_id):
        params = {"analysis_id": f"eq.{analysis_id}", "id": f"eq.{record_id}", "select": "id,analysis_id,association_1_id,association_2_id,supersedes_record_id,payload,created_at", "limit": "1"}
        rows = self._send("GET", user, params=params, table="evidence_contradictions").json()
        return rows[0] if rows else None


def make_store() -> AnalysisStore:
    if settings.STORAGE == "memory":
        return MemoryStore()
    return SupabaseStore(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
