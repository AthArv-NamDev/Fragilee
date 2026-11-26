import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.phase5_outcomes import OutcomeObservation
from app.phase5_preprocessing import make_preprocessor, validate_feature_frame
from scripts.phase5_readiness import ROOT, build_report


def source():
    return [{"source_name": "Public filing", "source_url": "https://example.org/source",
             "retrieved_at": "2026-01-10", "evidence_note": "Company status stated in filing.",
             "verification_state": "pending"}]


def base_observation(**changes):
    return {"observation_id": "2de38308-e251-4e5b-8f1c-cecc6f7b7371", "company_key": "company-hash-1",
            "observed_at": "2026-01-10", "status": "unknown", "sources": source(),
            "recorded_at": "2026-01-10", **changes}


def test_outcome_observation_keeps_unknown_and_does_not_create_labels():
    row = OutcomeObservation.model_validate(base_observation())
    assert row.status == "unknown" and row.event_date is None


@pytest.mark.parametrize("changes, message", [
    ({"status": "acquired"}, "require a verified event_date"),
    ({"status": "operational_active", "event_date": "2025-12-01"}, "cannot carry an outcome event_date"),
    ({"status": "right_censored"}, "require a follow_up_due"),
    ({"status": "right_censored", "follow_up_due": "2026-01-10"}, "after observed_at"),
    ({"status": "confirmed_closure", "event_date": "2026-01-11"}, "after observed_at"),
])
def test_outcome_observation_rejects_invalid_temporal_or_event_semantics(changes, message):
    with pytest.raises(ValueError, match=message):
        OutcomeObservation.model_validate(base_observation(**changes))


def test_acquisition_is_an_outcome_category_not_automatically_a_failure_label():
    verified_sources = [{**source()[0], "verification_state": "verified"}]
    row = OutcomeObservation.model_validate(base_observation(status="acquired", event_date="2025-12-01", sources=verified_sources))
    assert row.status == "acquired"
    assert "status" not in ("closed", "failed")


def test_train_only_preprocessing_uses_train_statistics_and_handles_unseen_category():
    train = pd.DataFrame({"revenue": [1.0, 3.0, np.nan], "sector": ["retail", "retail", "software"]})
    held_out = pd.DataFrame({"revenue": [10000.0], "sector": ["new-sector"]})
    validate_feature_frame(train, ["revenue"], ["sector"])
    transformer = make_preprocessor(["revenue"], ["sector"])
    train_values = transformer.fit_transform(train)
    test_values = transformer.transform(held_out)
    numeric_pipe = transformer.named_transformers_["numeric"]
    assert numeric_pipe.named_steps["impute"].statistics_[0] == 2.0
    assert train_values.shape[1] == test_values.shape[1]
    assert np.isfinite(test_values).all()
    assert test_values[0, 0] > 1000  # held-out extreme did not affect the training scaler


def test_preprocessing_validation_rejects_missing_columns_and_infinity():
    with pytest.raises(ValueError, match="Missing feature columns"):
        validate_feature_frame(pd.DataFrame({"revenue": [1.0]}), ["revenue"], ["sector"])
    with pytest.raises(ValueError, match="infinite"):
        validate_feature_frame(pd.DataFrame({"revenue": [float("inf")], "sector": ["retail"]}), ["revenue"], ["sector"])
    with pytest.raises(ValueError, match="no observed training values"):
        validate_feature_frame(pd.DataFrame({"revenue": [np.nan], "sector": ["retail"]}), ["revenue"], ["sector"])
    with pytest.raises(ValueError, match="documented numeric bounds"):
        validate_feature_frame(pd.DataFrame({"revenue": [12.0], "sector": ["retail"]}), ["revenue"], ["sector"], {"revenue": (0, 10)})


def test_provenance_manifest_and_registry_match_current_immutable_artifacts():
    report = build_report()
    assert report["datasets"]["stage1"]["artifacts"]["raw_artifact"]["exists"] is False
    assert report["datasets"]["stage1"]["training_eligible"] is False
    stage2_raw = report["datasets"]["stage2"]["artifacts"]["raw_artifact"]
    if stage2_raw["exists"]:
        assert stage2_raw["matches_manifest"] is True
    else:
        assert stage2_raw["matches_manifest"] is None
        assert report["datasets"]["stage2"]["training_eligible"] is False
    assert report["datasets"]["stage2"]["artifacts"]["processed_artifact"]["matches_manifest"] is True
    assert all(item["artifact_hash_matches_config"] for item in report["models"].values())
    registry = json.loads((ROOT / "data/feature_registry.json").read_text())
    assert all(item["redevelopment_decision"].startswith("exclude") for item in registry["features"])


def test_prospective_outcome_schema_and_contract_parse():
    schema = json.loads((ROOT / "data/outcome_observation.schema.json").read_text())
    contract = json.loads((ROOT / "models/inference_contract_v1.json").read_text())
    assert schema["properties"]["status"]["enum"]
    assert contract["status"] == "legacy_descriptive_only"
    assert contract["output"]["prediction_horizon"] is None


def test_prediction_api_marks_legacy_score_semantics_and_versions(client):
    from conftest import USER_A, headers_for

    body = {"category": "software", "state": "CA", "funding_total_usd": 250000, "funding_rounds": 2,
            "has_VC": False, "has_angel": True, "has_roundA": True, "has_roundB": False,
            "has_roundC": False, "has_roundD": False, "avg_participants": 2.0, "relationships": 5,
            "age_first_funding_year": 1.0, "age_last_funding_year": 2.0}
    response = client.post("/v1/predict/stage2", json=body, headers=headers_for(USER_A))
    assert response.status_code == 200
    result = response.json()
    assert result["inference_status"] == "legacy_descriptive_only"
    assert result["output_semantics"] == "historical_terminal_outcome_association"
    assert result["prediction_horizon"] is None
    assert len(result["model_version"]) == len(result["feature_schema_version"]) == 64
