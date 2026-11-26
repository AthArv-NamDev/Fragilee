"""Read-only reproducibility and Phase 5 data/model readiness audit.

Run from backend/: python scripts/phase5_readiness.py
This script never trains, exports models, or rewrites datasets.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_shape(path: Path) -> tuple[int, list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        columns = next(reader, [])
        rows = sum(1 for _ in reader)
    return rows, columns


def build_report() -> dict:
    manifest = json.loads((ROOT / "data/provenance_manifest.json").read_text())
    registry = json.loads((ROOT / "data/feature_registry.json").read_text())
    config = json.loads((ROOT / "models/model_config.json").read_text())
    stages = {}
    for dataset in manifest["datasets"]:
        audit = {"training_eligible": dataset["training_eligible"], "blockers": list(dataset["eligibility_blockers"]), "artifacts": {}}
        for role in ("raw_artifact", "processed_artifact"):
            expected = dataset.get(role)
            if expected is None:
                audit["artifacts"][role] = {"exists": False}
                continue
            path = ROOT / expected["path"]
            if not path.exists():
                audit["artifacts"][role] = {
                    "exists": False,
                    "path": expected["path"],
                    "matches_manifest": None,
                }
                continue
            rows, columns = csv_shape(path)
            matches = (digest(path) == expected["sha256"] and rows == expected["rows"] and columns == expected["column_names"])
            audit["artifacts"][role] = {"exists": True, "matches_manifest": matches, "sha256": digest(path), "rows": rows, "columns": len(columns)}
        stages[dataset["stage"]] = audit

    registry_by_stage: dict[str, set[str]] = {}
    for feature in registry["features"]:
        registry_by_stage.setdefault(feature["stage"], set()).add(feature["feature_name"])
    model_integrity = {}
    for stage, entry in config["stages"].items():
        path = ROOT / "models" / entry["model_file"]
        model_integrity[stage] = {
            "artifact_exists": path.exists(),
            "artifact_hash_matches_config": path.exists() and digest(path) == entry["sha256"],
            "feature_count": len(entry["features"]),
            "registry_covers_all_features": set(entry["features"]).issubset(registry_by_stage.get(stage, set())),
            "redevelopment_eligible": False,
        }

    return {
        "report_version": "1.0",
        "scope": "read_only; no model training, artifact writes, or dataset rewrites",
        "datasets": stages,
        "models": model_integrity,
        "prospective_redevelopment": "blocked_pending_verified_provenance_outcome_timing_and_censoring",
        "legacy_artifacts": "preserved; integrity verified separately from prospective eligibility",
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, sort_keys=True))
