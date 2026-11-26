"""Behavioral tests for the standalone deterministic Phase 2B engine."""
from datetime import datetime, timezone
from datetime import date

import pytest
from pydantic import ValidationError

from app.diagnostics import ENGINE_VERSION, evaluate_profile
from app.schemas import StartupProfile

AT = datetime(2025, 6, 1, tzinfo=timezone.utc)


def metric(field, value=None, *, provenance="measured", unit=None, currency=None,
           period=None, range_low=None, range_high=None, applicability="applicable", measurement_date=None):
    units = {
        "average_order_value": "currency/order", "fulfilment_cost": "currency/order",
        "average_selling_price": "currency/customer", "variable_cost_per_unit": "currency/unit",
        "revenue_amount": "currency",
        "customer_acquisition_cost": "currency/customer", "cac_payback_period": "months",
        "cash_balance": "currency", "monthly_operating_expense": "currency/month", "runway": "months",
        "active_buyers": "buyers", "active_sellers": "sellers", "paying_customers": "customers",
        "customer_interviews": "interviews", "retention_rate": "percent", "market_size": "currency",
        "minimum_order_quantity": "units",
    }
    money = {"average_order_value", "fulfilment_cost", "average_selling_price", "variable_cost_per_unit",
             "customer_acquisition_cost", "cash_balance", "monthly_operating_expense", "market_size", "revenue_amount"}
    if provenance in ("unknown", "not_applicable"):
        return {"field_id": field, "provenance": provenance, "confirmed_by_user": True,
                "applicability": "unknown" if provenance == "unknown" else "not_applicable"}
    data = {"field_id": field, "unit": unit or units[field], "provenance": provenance,
            "confirmed_by_user": True, "applicability": applicability}
    if value is not None:
        data["value"] = value
    if range_low is not None:
        data["range_low"] = range_low
        data["range_high"] = range_high
    if field in money:
        data["currency"] = currency or "USD"
    if period:
        data["period"] = period
    if measurement_date:
        data["measurement_date"] = measurement_date.isoformat()
    return data


def dtc_profile(revenue, cost, *, stage="early_revenue", kind="dtc_ecommerce"):
    return StartupProfile.model_validate({
        "identity": {"business_model": kind, "stage": stage},
        "business_model_details": {"kind": kind, "metrics": [revenue, cost]},
    })


def finding(report, diagnostic_id):
    return next(item for item in report.findings if item.diagnostic_id == diagnostic_id)


def test_missing_profile_is_safe_for_legacy_records():
    report = evaluate_profile(None, evaluated_at=AT)
    assert report.profile_available is False
    assert report.profile_schema_version is None
    assert report.findings == []
    assert "No founder facts" in report.limitations[0]


@pytest.mark.parametrize("name,profile", [
    ("idea sparse", {"identity": {"stage": "idea_concept", "business_model": "not_yet_determined"}}),
    ("EcoCart-like marketplace", {"identity": {"stage": "pre_revenue", "business_model": "marketplace"}, "business_model_details": {"kind": "marketplace", "buyer_group": "Shoppers", "seller_group": "Local stores"}}),
    ("early SaaS", {"identity": {"stage": "early_revenue", "business_model": "b2b_saas"}, "customer_market": {"customer_segment": "Small clinics"}}),
    ("DTC", {"identity": {"stage": "early_revenue", "business_model": "dtc_ecommerce"}, "business_model_details": {"kind": "dtc_ecommerce"}}),
    ("hardware", {"identity": {"stage": "mvp_product_development", "business_model": "hardware"}, "business_model_details": {"kind": "hardware", "tooling_and_production": "Prototype tooling quoted"}}),
    ("services", {"identity": {"stage": "early_revenue", "business_model": "services_consulting"}, "business_model_details": {"kind": "services_consulting"}}),
])
def test_requested_business_model_fixtures_are_deterministic_and_scored_separately(name, profile):
    parsed = StartupProfile.model_validate(profile)
    a = evaluate_profile(parsed, evaluated_at=AT).model_dump(mode="json")
    b = evaluate_profile(parsed, evaluated_at=AT).model_dump(mode="json")
    assert a == b, name
    assert a["engine_version"] == ENGINE_VERSION
    assert a["profile_available"] is True
    assert "probability" not in a and "risk_score" not in a
    assert len({f["finding_id"] for f in a["findings"]}) == len(a["findings"])


def test_evaluation_does_not_mutate_the_saved_profile_object():
    profile = StartupProfile.model_validate({"identity": {"stage": "early_revenue", "business_model": "b2b_saas"},
                                             "customer_market": {"customer_segment": "Small clinics"}})
    before = profile.model_dump(mode="json", exclude_none=True)
    evaluate_profile(profile, evaluated_at=AT)
    assert profile.model_dump(mode="json", exclude_none=True) == before


def test_ecocart_sparse_marketplace_does_not_get_invented_financial_findings():
    report = evaluate_profile({"identity": {"stage": "pre_revenue", "business_model": "marketplace"},
                               "business_model_details": {"kind": "marketplace"}}, evaluated_at=AT)
    assert finding(report, "marketplace.liquidity").status == "INSUFFICIENT_INFORMATION"
    assert finding(report, "economics.contribution_per_transaction").status == "INSUFFICIENT_INFORMATION"
    assert finding(report, "economics.cac_payback").status == "NOT_APPLICABLE"
    assert finding(report, "finance.cash_runway").status == "INSUFFICIENT_INFORMATION"
    assert all(not item.calculated_values for item in report.findings if item.diagnostic_id.startswith(("economics.", "finance.")))


@pytest.mark.parametrize("provenance,expected", [
    ("measured", "CONFIRMED"), ("estimated", "INDICATED"), ("assumed", "HYPOTHESIS"),
])
def test_negative_contribution_finding_respects_weakest_input_provenance(provenance, expected):
    profile = dtc_profile(metric("average_order_value", 10, provenance=provenance, period="month"),
                          metric("fulfilment_cost", 14, provenance="measured", period="month"))
    result = finding(evaluate_profile(profile, evaluated_at=AT), "economics.contribution_per_transaction")
    assert result.status == expected
    assert result.calculated_values["contribution_low"] == -4
    assert result.calculated_values["contribution_high"] == -4
    assert result.formula_or_rule.startswith("Contribution per transaction = revenue per transaction - variable costs")
    assert "profile.business_model_details.metrics" in result.supporting_inputs[0]["field"]


def test_positive_measured_contribution_is_not_triggered_not_a_profitability_claim():
    profile = dtc_profile(metric("average_order_value", 25, period="month"), metric("fulfilment_cost", 8, period="month"))
    result = finding(evaluate_profile(profile, evaluated_at=AT), "economics.contribution_per_transaction")
    assert result.status == "NOT_TRIGGERED"
    assert result.calculated_values["contribution_low"] == 17
    assert "does not establish overall profitability" in result.explanation


def test_partial_ranges_use_interval_arithmetic_without_midpoint():
    profile = dtc_profile(metric("average_order_value", range_low=20, range_high=40, period="month"),
                          metric("fulfilment_cost", range_low=15, range_high=25, period="month"))
    result = finding(evaluate_profile(profile, evaluated_at=AT), "economics.contribution_per_transaction")
    assert result.status == "HYPOTHESIS"
    assert result.calculated_values["contribution_low"] == -5
    assert result.calculated_values["contribution_high"] == 25
    assert "midpoint" in result.explanation


@pytest.mark.parametrize("right,expected", [
    (metric("fulfilment_cost", 8, currency="EUR", period="month"), "Currency differs"),
    (metric("fulfilment_cost", 8, period="quarter"), "Measurement periods differ"),
])
def test_incompatible_currency_or_period_is_conflicted_not_converted(right, expected):
    profile = dtc_profile(metric("average_order_value", 25, period="month"), right)
    result = finding(evaluate_profile(profile, evaluated_at=AT), "economics.contribution_per_transaction")
    assert result.status == "CONFLICTED"
    assert expected in result.explanation
    assert result.calculated_values == {}


def test_unknown_metric_is_not_zero_and_not_applicable_model_rule_is_explicit():
    profile = StartupProfile.model_validate({
        "identity": {"stage": "early_revenue", "business_model": "services_consulting"},
        "economics": {"metrics": [metric("average_selling_price", provenance="unknown")]},
        "business_model_details": {"kind": "services_consulting"},
    })
    contribution = finding(evaluate_profile(profile, evaluated_at=AT), "economics.contribution_per_transaction")
    hardware = finding(evaluate_profile(profile, evaluated_at=AT), "hardware.production_readiness")
    assert contribution.status == "INSUFFICIENT_INFORMATION"
    assert contribution.calculated_values == {}
    assert hardware.status == "NOT_APPLICABLE"
    assert hardware.applicability == "not_applicable"


def test_explicit_not_applicable_metric_remains_not_applicable():
    profile = StartupProfile.model_validate({
        "identity": {"stage": "early_revenue", "business_model": "b2b_saas"},
        "customer_market": {"metrics": [metric("paying_customers", provenance="not_applicable")]},
    })
    result = finding(evaluate_profile(profile, evaluated_at=AT), "market.willingness_to_pay")
    assert result.status == "NOT_APPLICABLE"
    assert result.applicability == "not_applicable"


def test_conflicting_pre_revenue_stage_and_revenue_are_not_silently_resolved():
    profile = StartupProfile.model_validate({
        "identity": {"stage": "pre_revenue", "business_model": "b2b_saas"},
        "economics": {"metrics": [metric("revenue_amount", 1000, period="month")]},
    })
    result = finding(evaluate_profile(profile, evaluated_at=AT), "economics.cac_payback")
    assert result.status == "CONFLICTED"


def test_cac_payback_is_withheld_without_attributable_numerator_and_denominator():
    profile = StartupProfile.model_validate({
        "identity": {"stage": "early_revenue", "business_model": "b2b_saas"},
        "economics": {"metrics": [metric("customer_acquisition_cost", 0, currency="USD")]},
    })
    result = finding(evaluate_profile(profile, evaluated_at=AT), "economics.cac_payback")
    assert result.status == "HYPOTHESIS"
    assert result.calculated_values == {}
    assert "attributable new customers" in result.missing_inputs
    assert "Not calculated" in result.formula_or_rule


def test_operating_expense_is_not_used_as_burn_and_runway_is_not_invented():
    profile = StartupProfile.model_validate({
        "identity": {"stage": "early_revenue", "business_model": "b2b_saas"},
        "finance": {"metrics": [metric("cash_balance", 50_000), metric("monthly_operating_expense", 10_000, period="month")]},
    })
    result = finding(evaluate_profile(profile, evaluated_at=AT), "finance.cash_runway")
    assert result.status == "INSUFFICIENT_INFORMATION"
    assert result.calculated_values == {}
    assert "net cash burn per period" in result.missing_inputs
    assert "not treated as burn" in result.explanation


def test_marketplace_zero_seller_denominator_is_explicit_and_never_divides_by_zero():
    profile = StartupProfile.model_validate({
        "identity": {"stage": "early_revenue", "business_model": "marketplace"},
        "business_model_details": {"kind": "marketplace", "metrics": [metric("active_buyers", 5, measurement_date=date(2025, 5, 1)), metric("active_sellers", 0, measurement_date=date(2025, 5, 1))]},
    })
    result = finding(evaluate_profile(profile, evaluated_at=AT), "marketplace.liquidity")
    assert result.status == "CONFIRMED"
    assert result.calculated_values["buyer_to_seller_ratio"] is None
    assert "undefined" in result.explanation


def test_marketplace_counts_without_a_shared_date_are_not_compared():
    profile = StartupProfile.model_validate({
        "identity": {"stage": "early_revenue", "business_model": "marketplace"},
        "business_model_details": {"kind": "marketplace", "metrics": [metric("active_buyers", 5), metric("active_sellers", 2)]},
    })
    result = finding(evaluate_profile(profile, evaluated_at=AT), "marketplace.liquidity")
    assert result.status == "INSUFFICIENT_INFORMATION"
    assert "buyer_to_seller_ratio" not in result.calculated_values


def test_mismatched_presence_of_measurement_date_withholds_contribution_calculation():
    profile = dtc_profile(metric("average_order_value", 25, period="month", measurement_date=date(2025, 5, 1)),
                          metric("fulfilment_cost", 8, period="month"))
    result = finding(evaluate_profile(profile, evaluated_at=AT), "economics.contribution_per_transaction")
    assert result.status == "INSUFFICIENT_INFORMATION"
    assert result.calculated_values == {}
    assert "measurement date is missing" in result.explanation


def test_missing_period_metadata_withholds_contribution_calculation():
    profile = dtc_profile(metric("average_order_value", 25, period="month"), metric("fulfilment_cost", 8))
    result = finding(evaluate_profile(profile, evaluated_at=AT), "economics.contribution_per_transaction")
    assert result.status == "INSUFFICIENT_INFORMATION"
    assert result.calculated_values == {}
    assert "period is missing" in result.explanation


def test_related_unit_economics_findings_are_linked_not_aggregated():
    profile = dtc_profile(metric("average_order_value", 10, period="month"), metric("fulfilment_cost", 14, period="month"))
    report = evaluate_profile(profile, evaluated_at=AT)
    contribution = finding(report, "economics.contribution_per_transaction")
    payback = finding(report, "economics.cac_payback")
    assert payback.finding_id in contribution.related_findings
    assert contribution.finding_id in payback.related_findings
    assert payback.relationship_type == "SUPPORTING"
    assert not hasattr(report, "overall_score")


@pytest.mark.parametrize("profile", [
    {"identity": {"business_model": "hardware"}, "business_model_details": {"kind": "hardware", "tooling_and_production": "Prototype"}},
    {"identity": {"business_model": "fintech"}, "business_model_details": {"kind": "fintech", "licensing_status": "Under review"}},
    {"identity": {"business_model": "b2b_saas"}, "team_operations": {"capability_gaps": "No security lead"}},
])
def test_qualitative_profile_text_is_a_hypothesis_not_a_confirmed_diagnosis(profile):
    report = evaluate_profile(profile, evaluated_at=AT)
    assert any(item.status == "HYPOTHESIS" for item in report.findings)
    assert all(item.evidence_strength != "High" for item in report.findings if item.status == "HYPOTHESIS")


def test_profile_validation_rejects_incompatible_units_before_evaluation():
    with pytest.raises(ValidationError):
        StartupProfile.model_validate({"economics": {"metrics": [metric("average_order_value", 40, unit="customers")]}})


def test_profile_validation_rejects_negative_count_that_could_be_a_denominator():
    with pytest.raises(ValidationError):
        StartupProfile.model_validate({"business_model_details": {"kind": "marketplace", "metrics": [metric("active_sellers", -1)]},
                                       "identity": {"business_model": "marketplace"}})
