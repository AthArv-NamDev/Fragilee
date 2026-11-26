"""Saved-analysis diagnostics are additive, per-user, transient, and failure-safe."""
from datetime import datetime

from app import main
from app.diagnostics import evaluate_profile
from app.main import app
from app.schemas import StartupProfile
from conftest import USER_A, USER_B, headers_for


INPUT = {"country": "IND", "tags": ["Software"]}
PROFILE = {
    "profile_schema_version": 1,
    "last_updated_at": "2025-06-01",
    "identity": {"business_model": "marketplace", "stage": "pre_revenue", "operating_geography": "India"},
    "business_model_details": {"kind": "marketplace", "buyer_group": "Environmentally conscious shoppers", "seller_group": "Sustainable product sellers", "liquidity_notes": "Seller verification and customer trust need validation."},
    "team_operations": {"metrics": [{"field_id": "team_size", "value": 3, "unit": "people", "provenance": "measured", "confirmed_by_user": True, "applicability": "applicable"}]},
}
CONTEXT = {
    "concept": "A sustainable-products marketplace.",
    "customer": "Environmentally conscious shoppers.",
    "revenue_model": "Commission on sales.",
    "biggest_worry": "Adoption, seller trust, and acquisition cost.",
    "profile": PROFILE,
}


def create_analysis(client, *, context=CONTEXT, user=USER_A):
    response = client.post("/v1/analyses", headers=headers_for(user), json={
        "title": "EcoCart", "stage": "stage1", "input": INPUT, "context": context,
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_retrieval_adds_exact_engine_findings_without_persisting_or_mutating(anon_client):
    created = create_analysis(anon_client)
    before = created["result"]
    response = anon_client.get(f"/v1/analyses/{created['id']}", headers=headers_for(USER_A))
    assert response.status_code == 200
    body = response.json()
    assert body["diagnostics_state"] == "available"
    instant = datetime.fromisoformat(body["diagnostics"]["evaluated_at"].replace("Z", "+00:00"))
    expected = evaluate_profile(StartupProfile.model_validate(PROFILE), evaluated_at=instant).model_dump(mode="json")
    assert body["diagnostics"] == expected
    assert body["context"]["concept"] == CONTEXT["concept"]
    assert body["context"]["revenue_model"] == CONTEXT["revenue_model"]
    team_metric = body["context"]["profile"]["team_operations"]["metrics"][0]
    assert team_metric["field_id"] == "team_size" and team_metric["value"] == 3
    assert team_metric["provenance"] == "measured"
    assert body["result"] == before

    stored = app.state.analyses._rows[created["id"]]
    assert stored["result"] == before
    assert "diagnostics" not in stored
    assert stored["context"] == created["context"]

    # No EcoCart financial/count inputs were supplied, so they cannot appear as findings.
    by_id = {item["diagnostic_id"]: item for item in body["diagnostics"]["findings"]}
    assert by_id["economics.contribution_per_transaction"]["status"] == "INSUFFICIENT_INFORMATION"
    assert by_id["economics.cac_payback"]["status"] == "NOT_APPLICABLE"
    assert by_id["finance.cash_runway"]["status"] == "INSUFFICIENT_INFORMATION"
    assert by_id["marketplace.liquidity"]["status"] == "INSUFFICIENT_INFORMATION"
    assert by_id["team.capability_gaps"]["status"] == "INSUFFICIENT_INFORMATION"


def test_legacy_analysis_returns_explicit_no_profile_state(anon_client):
    created = create_analysis(anon_client, context=None)
    response = anon_client.get(f"/v1/analyses/{created['id']}", headers=headers_for(USER_A))
    assert response.status_code == 200
    body = response.json()
    assert body["diagnostics_state"] == "no_profile"
    assert body["diagnostics"]["profile_available"] is False
    assert body["diagnostics"]["findings"] == []
    assert body["context"] is None


def test_malformed_saved_profile_does_not_break_founder_notes_or_model_report(anon_client):
    created = create_analysis(anon_client)
    row = app.state.analyses._rows[created["id"]]
    row["context"]["profile"] = {"profile_schema_version": 99, "identity": "not-an-object"}

    response = anon_client.get(f"/v1/analyses/{created['id']}", headers=headers_for(USER_A))
    assert response.status_code == 200
    body = response.json()
    assert body["diagnostics_state"] == "unavailable"
    assert body["diagnostics"] is None
    assert body["context"]["concept"] == CONTEXT["concept"]
    assert body["result"] == created["result"]


def test_engine_exception_does_not_break_report_retrieval(anon_client, monkeypatch):
    created = create_analysis(anon_client)

    def fail(*_args, **_kwargs):
        raise RuntimeError("diagnostic rule error")

    monkeypatch.setattr(main, "evaluate_profile", fail)
    response = anon_client.get(f"/v1/analyses/{created['id']}", headers=headers_for(USER_A))
    assert response.status_code == 200
    body = response.json()
    assert body["diagnostics_state"] == "unavailable"
    assert body["diagnostics"] is None
    assert body["context"]["concept"] == CONTEXT["concept"]
    assert body["result"] == created["result"]


def test_diagnostics_are_never_returned_for_another_users_analysis(anon_client):
    created = create_analysis(anon_client, user=USER_A)
    response = anon_client.get(f"/v1/analyses/{created['id']}", headers=headers_for(USER_B))
    assert response.status_code == 404
