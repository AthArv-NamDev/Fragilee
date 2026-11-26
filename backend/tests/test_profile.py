"""Structured founder profile contract and additive saved-snapshot compatibility."""
import json
import uuid
from datetime import date

import httpx
import pytest
from pydantic import ValidationError

from app.schemas import Context, StartupProfile
from app.main import app
from app.storage import StorageError, SupabaseStore
from conftest import USER_A, USER_B, headers_for


def test_profile_can_be_sparse_and_has_version():
    profile = StartupProfile()
    assert profile.profile_schema_version == 1
    assert profile.identity is None


@pytest.mark.parametrize("provenance,applicability", [("unknown", "unknown"), ("not_applicable", "not_applicable")])
def test_unknown_states_are_preserved_without_becoming_zero(provenance, applicability):
    profile = StartupProfile.model_validate({"team_operations": {"metrics": [{
        "field_id": "team_size", "provenance": provenance, "confirmed_by_user": True,
        "applicability": applicability,
    }]}})
    metric = profile.team_operations.metrics[0]
    assert metric.value is None and metric.provenance == provenance and metric.applicability == applicability


def test_measured_and_estimated_values_keep_distinct_provenance_and_units():
    base = {"field_id": "revenue_amount", "value": 1200, "unit": "currency", "currency": "INR",
            "period": "month", "confirmed_by_user": True, "applicability": "applicable"}
    measured = StartupProfile.model_validate({"economics": {"metrics": [{**base, "provenance": "measured"}]}})
    estimated = StartupProfile.model_validate({"economics": {"metrics": [{**base, "provenance": "estimated"}]}})
    assert measured.economics.metrics[0].provenance == "measured"
    assert estimated.economics.metrics[0].provenance == "estimated"
    assert measured.economics.metrics[0].currency == "INR"


@pytest.mark.parametrize("metric", [
    {"field_id": "revenue_amount", "value": 100, "unit": "currency", "provenance": "measured", "confirmed_by_user": True, "applicability": "applicable"},
    {"field_id": "retention_rate", "value": 20, "unit": "percent", "period": "point_in_time", "provenance": "measured", "confirmed_by_user": True, "applicability": "applicable"},
    {"field_id": "team_size", "range_low": 5, "range_high": 2, "unit": "people", "provenance": "estimated", "confirmed_by_user": True, "applicability": "applicable"},
    {"field_id": "gross_margin", "value": 120, "unit": "percent", "provenance": "measured", "confirmed_by_user": True, "applicability": "applicable"},
])
def test_invalid_metric_data_is_rejected(metric):
    with pytest.raises(ValidationError):
        StartupProfile.model_validate({"economics": {"metrics": [metric]}})


def test_idea_stage_does_not_require_revenue_or_retention():
    profile = StartupProfile.model_validate({"identity": {"stage": "idea_concept", "business_model": "not_yet_determined"}})
    assert profile.economics is None and profile.product_traction is None


def test_model_specific_details_must_match_selected_model():
    with pytest.raises(ValidationError):
        StartupProfile.model_validate({"identity": {"business_model": "hardware"}, "business_model_details": {"kind": "marketplace"}})


@pytest.mark.parametrize("kind,details", [
    ("b2b_saas", {"kind": "b2b_saas", "sales_cycle_notes": "Founder-led sales"}),
    ("marketplace", {"kind": "marketplace", "buyer_group": "Readers", "seller_group": "Authors"}),
    ("hardware", {"kind": "hardware", "manufacturing_readiness": "Prototype"}),
    ("fintech", {"kind": "fintech", "regulatory_jurisdiction": "India"}),
    ("biotech_medtech", {"kind": "biotech_medtech", "regulatory_pathway": "Not yet assessed"}),
])
def test_supported_model_details_are_accepted(kind, details):
    profile = StartupProfile.model_validate({"identity": {"business_model": kind}, "business_model_details": details})
    assert profile.business_model_details.kind == kind


def test_duplicate_metrics_are_rejected_instead_of_silently_resolved():
    metric = {"field_id": "paying_customers", "value": 4, "unit": "customers", "provenance": "measured", "confirmed_by_user": True, "applicability": "applicable"}
    with pytest.raises(ValidationError):
        StartupProfile.model_validate({"customer_market": {"metrics": [metric]}, "product_traction": {"metrics": [metric]}})


def test_context_size_is_bounded_below_existing_storage_limit():
    with pytest.raises(ValidationError):
        Context(concept="x" * 800, profile={
            "identity": {"problem": "p" * 800, "proposed_solution": "s" * 800},
            "customer_market": {"customer_description": "c" * 800, "discovery_evidence": "d" * 800,
                                "willingness_to_pay_evidence": "w" * 800, "existing_alternatives": "a" * 800,
                                "market_size_assumption": "m" * 800},
            "product_traction": {"customer_validation": "v" * 800},
            "finance": {"upcoming_milestones": "f" * 800},
            "team_operations": {"team_capabilities": "t" * 800, "capability_gaps": "g" * 800,
                                "critical_dependencies": "z" * 800, "suppliers_or_distribution": "q" * 800,
                                "technology_constraints": "h" * 800, "regulatory_context": "r" * 800},
        })


def test_analysis_endpoint_round_trips_profile_and_legacy_context(anon_client):
    profile = {"profile_schema_version": 1, "identity": {"business_model": "marketplace", "stage": "pre_revenue"},
               "business_model_details": {"kind": "marketplace", "buyer_group": "Readers", "seller_group": "Authors"},
               "economics": {"metrics": [{"field_id": "revenue_amount", "value": 1200, "unit": "currency", "currency": "INR", "period": "month", "provenance": "estimated", "confirmed_by_user": True, "applicability": "applicable"}]},
               "team_operations": {"metrics": [{"field_id": "team_size", "provenance": "unknown", "confirmed_by_user": True, "applicability": "unknown"}]}}
    response = anon_client.post("/v1/analyses", headers=headers_for(USER_A), json={
        "title": "Books marketplace", "stage": "stage1", "input": {"country": "USA", "state": "CA", "tags": ["Software"]},
        "context": {"concept": "A marketplace connecting readers and independent authors.", "customer": "Readers", "profile": profile},
    })
    assert response.status_code == 201, response.text
    saved = anon_client.get(f"/v1/analyses/{response.json()['id']}", headers=headers_for(USER_A)).json()
    assert saved["context"]["concept"].startswith("A marketplace")
    assert saved["context"]["profile"]["business_model_details"]["kind"] == "marketplace"
    metrics = saved["context"]["profile"]["economics"]["metrics"]
    assert metrics[0]["provenance"] == "estimated" and metrics[0]["currency"] == "INR" and metrics[0]["period"] == "month"
    unknown_team = saved["context"]["profile"]["team_operations"]["metrics"][0]
    assert unknown_team["provenance"] == "unknown" and unknown_team["applicability"] == "unknown"
    assert "value" not in unknown_team
    assert anon_client.get(f"/v1/analyses/{response.json()['id']}", headers=headers_for(USER_B)).status_code == 404


@pytest.mark.parametrize("stage,inputs", [
    ("stage1", {"country": "USA", "state": "CA", "tags": ["Software"]}),
    ("stage2", {"category": "software", "state": "CA", "funding_total_usd": 250000, "funding_rounds": 2,
                "has_VC": False, "has_angel": True, "has_roundA": True, "has_roundB": False,
                "has_roundC": False, "has_roundD": False, "avg_participants": 2.0, "relationships": 5,
                "age_first_funding_year": 1.0, "age_last_funding_year": 2.0}),
])
def test_profile_and_provenance_do_not_change_model_inputs_or_result(anon_client, stage, inputs):
    headers = headers_for(USER_A)
    notes = {"concept": "A product for local bookstores.", "customer": "Independent bookstores", "team_size": 3}
    baseline = anon_client.post("/v1/analyses", headers=headers, json={
        "title": "Book tool baseline", "stage": stage, "input": inputs, "context": notes,
    })
    profiled = anon_client.post("/v1/analyses", headers=headers, json={
        "title": "Book tool profiled", "stage": stage, "input": inputs,
        "context": {**notes, "profile": {
            "profile_schema_version": 1,
            "identity": {"business_model": "b2b_saas", "stage": "scaling"},
            "economics": {"metrics": [{"field_id": "revenue_amount", "value": 9_000_000_000_000, "unit": "currency", "currency": "INR", "period": "month", "provenance": "assumed", "confirmed_by_user": True, "applicability": "applicable"}]},
            "team_operations": {"metrics": [{"field_id": "team_size", "provenance": "not_applicable", "confirmed_by_user": True, "applicability": "not_applicable"}]},
        }},
    })
    assert baseline.status_code == profiled.status_code == 201
    plain, with_profile = baseline.json(), profiled.json()
    assert plain["input"] == with_profile["input"] == inputs
    assert plain["result"] == with_profile["result"]
    assert with_profile["context"]["concept"] == plain["context"]["concept"]
    assert with_profile["context"]["team_size"] == 3
    assert with_profile["context"]["profile"]["economics"]["metrics"][0]["provenance"] == "assumed"


def test_saved_legacy_context_without_profile_is_still_returned(anon_client):
    response = anon_client.post("/v1/analyses", headers=headers_for(USER_A), json={
        "title": "Legacy context", "stage": "stage1", "input": {"country": "USA", "state": "CA", "tags": ["Software"]},
        "context": {"concept": "Founder note from an older client.", "team_size": 2},
    })
    assert response.status_code == 201
    saved = anon_client.get(f"/v1/analyses/{response.json()['id']}", headers=headers_for(USER_A)).json()
    assert saved["context"]["concept"] == "Founder note from an older client."
    assert saved["context"]["team_size"] == 2
    assert "profile" not in saved["context"]


@pytest.mark.parametrize("stage,inputs", [
    ("stage1", {"country": "USA", "state": "CA", "tags": ["Software"]}),
    ("stage2", {"category": "software", "state": "CA", "funding_total_usd": 250000, "funding_rounds": 2,
                "has_VC": False, "has_angel": True, "has_roundA": True, "has_roundB": False,
                "has_roundC": False, "has_roundD": False, "avg_participants": 2.0, "relationships": 5,
                "age_first_funding_year": 1.0, "age_last_funding_year": 2.0}),
])
def test_profile_cannot_be_submitted_as_a_model_feature(anon_client, stage, inputs):
    response = anon_client.post("/v1/analyses", headers=headers_for(USER_A), json={
        "title": "Profile not a feature", "stage": stage,
        "input": {**inputs, "profile": {"cash_balance": 9_000_000}},
    })
    assert response.status_code == 422
    assert any("profile" in str(error["loc"]) for error in response.json()["detail"])


def test_analysis_creation_json_serializes_and_reloads_complete_profile(anon_client):
    analysis_id = str(uuid.uuid4())
    persisted = {}
    record_time = "2025-05-04T12:30:00Z"

    def postgrest(request):
        if request.method == "POST":
            payload = json.loads(request.content)
            persisted.update(payload)
            returned = {**payload, "id": analysis_id, "created_at": record_time}
            return httpx.Response(201, json=[returned])
        if request.method == "GET":
            assert request.url.params["id"] == f"eq.{analysis_id}"
            return httpx.Response(200, json=[{**persisted, "id": analysis_id, "created_at": record_time}])
        raise AssertionError(f"unexpected PostgREST method: {request.method}")

    client = httpx.Client(
        base_url="https://mock.supabase.test/rest/v1",
        transport=httpx.MockTransport(postgrest),
    )
    store = SupabaseStore("https://mock.supabase.test", "public-anon-key", client)
    original_store = app.state.analyses
    app.state.analyses = store
    body = {
        "title": "EcoCart",
        "stage": "stage1",
        "input": {"country": "USA", "state": "CA", "tags": ["Software"]},
        "context": {
            "concept": "A reusable packaging marketplace.",
            "customer": "B2C / urban eco-conscious consumers",
            "revenue_model": "Transaction fee",
            "startup_stage": "idea",
            "team_size": 3,
            "biggest_worry": "Adoption, seller trust and acquisition cost",
            "profile": {
                "profile_schema_version": 1,
                "last_updated_at": "2025-05-04",
                "identity": {"business_model": "marketplace", "stage": "pre_revenue"},
                "economics": {"metrics": [{
                    "field_id": "revenue_amount", "value": 1200,
                    "range_low": 1000, "range_high": 1400,
                    "unit": "currency", "currency": "INR", "period": "month",
                    "measurement_date": "2025-05-02",
                    "period_start": "2025-05-01", "period_end": "2025-05-31",
                    "source_reference": "Founder estimate",
                    "provenance": "estimated", "confirmed_by_user": True,
                    "applicability": "applicable",
                }]},
                "team_operations": {"metrics": [{
                    "field_id": "team_size", "provenance": "unknown",
                    "confirmed_by_user": True, "applicability": "unknown",
                }, {
                    "field_id": "utilization", "provenance": "not_applicable",
                    "confirmed_by_user": True, "applicability": "not_applicable",
                }]},
            },
        },
    }

    try:
        created = anon_client.post("/v1/analyses", headers=headers_for(USER_A), json=body)
        assert created.status_code == 201, created.text
        assert created.json()["id"] == analysis_id
        validated_context = Context.model_validate(body["context"])
        assert isinstance(validated_context.profile.last_updated_at, date)
        assert persisted["context"] == validated_context.model_dump(mode="json", exclude_none=True)
        assert persisted["context"]["profile"]["last_updated_at"] == "2025-05-04"
        assert persisted["context"]["profile"]["economics"]["metrics"][0]["measurement_date"] == "2025-05-02"
        assert persisted["context"]["profile"]["economics"]["metrics"][0]["period_start"] == "2025-05-01"
        assert persisted["context"]["profile"]["economics"]["metrics"][0]["range_high"] == 1400
        assert persisted["context"]["profile"]["economics"]["metrics"][0]["provenance"] == "estimated"
        assert "value" not in persisted["context"]["profile"]["team_operations"]["metrics"][0]
        assert "value" not in persisted["context"]["profile"]["team_operations"]["metrics"][1]
        assert persisted["context"]["concept"] == body["context"]["concept"]
        assert persisted["context"]["team_size"] == 3

        reopened = anon_client.get(f"/v1/analyses/{analysis_id}", headers=headers_for(USER_A))
        assert reopened.status_code == 200
        assert reopened.json()["created_at"] == record_time
        saved_context = reopened.json()["context"]
        assert saved_context["profile"]["last_updated_at"] == "2025-05-04"
        assert saved_context["profile"]["economics"]["metrics"][0]["source_reference"] == "Founder estimate"
        assert saved_context["profile"]["economics"]["metrics"][0]["currency"] == "INR"
        assert saved_context["profile"]["team_operations"]["metrics"][0]["provenance"] == "unknown"
        assert saved_context["revenue_model"] == "Transaction fee"
    finally:
        store.close()
        app.state.analyses = original_store


def test_storage_failure_returns_sanitized_retryable_api_error(anon_client):
    class UnavailableStore:
        def create(self, user, record):
            raise StorageError("private database diagnostics")

    original_store = app.state.analyses
    app.state.analyses = UnavailableStore()
    try:
        response = anon_client.post("/v1/analyses", headers=headers_for(USER_A), json={
            "title": "EcoCart", "stage": "stage1",
            "input": {"country": "USA", "state": "CA", "tags": ["Software"]},
            "context": {"profile": {"profile_schema_version": 1, "last_updated_at": "2025-05-04"}},
        })
        assert response.status_code == 503
        assert response.json()["detail"] == "Saved analyses are temporarily unavailable"
        assert "private database diagnostics" not in response.text
    finally:
        app.state.analyses = original_store
