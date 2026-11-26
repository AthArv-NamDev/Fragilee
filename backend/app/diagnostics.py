"""Deterministic, founder-profile-only diagnostics (Phase 2B).

This module deliberately has no dependency on scoring, model features, research,
storage, or report code. It emits evidence-aware observations and information
gaps, never a combined risk score or failure probability.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .diagnostic_rules import ENGINE_VERSION, RULES
from .schemas import ProfileMetric, StartupProfile

FindingStatus = Literal[
    "CONFIRMED", "INDICATED", "HYPOTHESIS", "NOT_TRIGGERED",
    "INSUFFICIENT_INFORMATION", "CONFLICTED", "NOT_APPLICABLE",
]
Severity = Literal["Critical", "Major", "Moderate", "Minor"]
EvidenceStrength = Literal["High", "Moderate", "Low", "Insufficient"]
Relationship = Literal["INDEPENDENT", "SUPPORTING", "DERIVED", "OVERLAPPING", "CONTRADICTORY"]


class DiagnosticFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    diagnostic_id: str
    title: str
    category: str
    description: str
    mechanism: str
    startup_stage: str | None
    business_model: str | None
    applicability: Literal["applicable", "unknown", "not_applicable"]
    status: FindingStatus
    severity_if_true: Severity | None = None
    evidence_strength: EvidenceStrength
    supporting_inputs: list[dict[str, Any]] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    formula_or_rule: str
    calculated_values: dict[str, float | int | str | bool | None] = Field(default_factory=dict)
    explanation: str
    limitations: list[str] = Field(default_factory=list)
    related_findings: list[str] = Field(default_factory=list)
    relationship_type: Relationship = "INDEPENDENT"
    evidence_references: list[str] = Field(default_factory=list)
    suggested_validation: str | None = None
    suggested_next_actions: list[str] = Field(default_factory=list)
    diagnostic_version: str
    evaluated_at: datetime


class DiagnosticReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine_version: str
    profile_schema_version: int | None
    profile_available: bool
    evaluated_at: datetime
    findings: list[DiagnosticFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def _now(value: datetime | None) -> datetime:
    result = value or datetime.now(timezone.utc)
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def _metrics(profile: StartupProfile) -> dict[str, tuple[ProfileMetric, str]]:
    groups = (
        ("customer_market", profile.customer_market),
        ("product_traction", profile.product_traction),
        ("economics", profile.economics),
        ("finance", profile.finance),
        ("team_operations", profile.team_operations),
        ("business_model_details", profile.business_model_details),
    )
    result: dict[str, tuple[ProfileMetric, str]] = {}
    for group_name, group in groups:
        if group is None or not hasattr(group, "metrics"):
            continue
        for i, metric in enumerate(group.metrics):
            result[metric.field_id] = (metric, f"profile.{group_name}.metrics[{i}]")
    return result


def _input(path: str, value: Any, provenance: str | None = None) -> dict[str, Any]:
    item = {"field": path, "value": value}
    if provenance is not None:
        item["provenance"] = provenance
    return item


def _metric_input(metric: ProfileMetric, path: str) -> dict[str, Any]:
    return _input(path, metric.model_dump(mode="json", exclude_none=True), metric.provenance)


def _evidence(provenances: list[str]) -> EvidenceStrength:
    if not provenances:
        return "Insufficient"
    if "assumed" in provenances:
        return "Low"
    if "estimated" in provenances:
        return "Moderate"
    if all(value == "measured" for value in provenances):
        return "High"
    return "Insufficient"


def _measured_status(provenances: list[str]) -> tuple[FindingStatus, EvidenceStrength]:
    """Apply the weakest provenance; assumptions never become measured evidence."""
    if not provenances or any(value == "unknown" for value in provenances):
        return "INSUFFICIENT_INFORMATION", "Insufficient"
    if any(value == "not_applicable" for value in provenances):
        return "NOT_APPLICABLE", "Insufficient"
    if any(value == "assumed" for value in provenances):
        return "HYPOTHESIS", "Low"
    if any(value == "estimated" for value in provenances):
        return "INDICATED", "Moderate"
    return "CONFIRMED", "High"


def _bounds(metric: ProfileMetric) -> tuple[float, float] | None:
    """Return explicit value/range bounds; never invent a midpoint."""
    if metric.range_low is not None and metric.range_high is not None:
        return metric.range_low, metric.range_high
    if metric.value is not None:
        return metric.value, metric.value
    return None


def _base(
    diagnostic_id: str,
    profile: StartupProfile,
    evaluated_at: datetime,
    status: FindingStatus,
    explanation: str,
    *,
    applicability: Literal["applicable", "unknown", "not_applicable"] = "applicable",
    evidence_strength: EvidenceStrength = "Insufficient",
    supporting_inputs: list[dict[str, Any]] | None = None,
    missing_inputs: list[str] | None = None,
    assumptions: list[str] | None = None,
    formula: str = "Deterministic rule; no score or threshold is applied.",
    calculated_values: dict[str, float | int | str | bool | None] | None = None,
    suggested_validation: str | None = None,
    next_actions: list[str] | None = None,
    limitations: list[str] | None = None,
    severity: Severity | None = None,
    relationship: Relationship = "INDEPENDENT",
) -> DiagnosticFinding:
    rule = RULES[diagnostic_id]
    identity = profile.identity
    return DiagnosticFinding(
        finding_id=diagnostic_id,
        diagnostic_id=diagnostic_id,
        title=rule["title"],
        category=rule["category"],
        description=explanation,
        mechanism=rule["mechanism"],
        startup_stage=identity.stage if identity else None,
        business_model=identity.business_model if identity else None,
        applicability=applicability,
        status=status,
        severity_if_true=severity,
        evidence_strength=evidence_strength,
        supporting_inputs=supporting_inputs or [],
        missing_inputs=missing_inputs or [],
        assumptions=assumptions or [],
        formula_or_rule=formula,
        calculated_values=calculated_values or {},
        explanation=explanation,
        limitations=limitations or [],
        relationship_type=relationship,
        suggested_validation=suggested_validation,
        suggested_next_actions=next_actions or [],
        diagnostic_version=f"{ENGINE_VERSION}/{rule['version']}",
        evaluated_at=evaluated_at,
    )


def _not_applicable(diagnostic_id: str, profile: StartupProfile, at: datetime, reason: str) -> DiagnosticFinding:
    return _base(diagnostic_id, profile, at, "NOT_APPLICABLE", reason,
                 applicability="not_applicable", limitations=["Applicability is based only on the selected Phase 2A business-model or stage enum."])


def _market_findings(profile: StartupProfile, at: datetime, metrics: dict[str, tuple[ProfileMetric, str]]) -> list[DiagnosticFinding]:
    result = []
    identity = profile.identity
    customer = profile.customer_market
    target = []
    if identity and identity.problem:
        target.append(_input("profile.identity.problem", identity.problem))
    if customer and customer.customer_segment:
        target.append(_input("profile.customer_market.customer_segment", customer.customer_segment))
    if customer and customer.customer_description:
        target.append(_input("profile.customer_market.customer_description", customer.customer_description))
    result.append(_base(
        "market.target_customer_clarity", profile, at,
        "HYPOTHESIS" if target else "INSUFFICIENT_INFORMATION",
        "The profile contains a founder-described problem or target-customer detail; it does not independently verify the segment or problem."
        if target else "No target-customer or problem description is available in the structured profile; this is an information gap, not evidence of market risk.",
        evidence_strength="Low" if target else "Insufficient", supporting_inputs=target,
        missing_inputs=[] if target else ["profile.identity.problem", "profile.customer_market.customer_segment or customer_description"],
        suggested_validation="Interview a narrowly defined customer segment and record the specific problem and current alternative.",
        next_actions=["Define one initial customer segment and a testable problem statement."],
        limitations=["Free-text founder statements are not independently verified."] if target else [],
    ))

    discovery_inputs = []
    if customer and customer.discovery_evidence:
        discovery_inputs.append(_input("profile.customer_market.discovery_evidence", customer.discovery_evidence))
    interviews = metrics.get("customer_interviews")
    if interviews:
        metric, path = interviews
        discovery_inputs.append(_metric_input(metric, path))
    if not discovery_inputs:
        discovery_status, discovery_strength = "INSUFFICIENT_INFORMATION", "Insufficient"
        discovery_text = "No customer-discovery evidence is recorded. Missing evidence is not a negative finding."
        missing = ["profile.customer_market.discovery_evidence", "customer_interviews"]
    elif interviews and interviews[0].provenance in ("unknown", "not_applicable"):
        discovery_status, discovery_strength = _measured_status([interviews[0].provenance])
        discovery_text = "Customer interviews were explicitly marked unavailable or not applicable; no count was inferred."
        missing = []
    else:
        discovery_status = "HYPOTHESIS" if any(i.get("provenance") == "assumed" for i in discovery_inputs) else "CONFIRMED" if interviews and interviews[0].provenance == "measured" else "HYPOTHESIS"
        discovery_strength = _evidence([i["provenance"] for i in discovery_inputs if "provenance" in i]) if interviews else "Low"
        discovery_text = "A founder-reported customer-interview count or discovery note is recorded; the count alone does not establish problem prevalence or demand."
        missing = []
    result.append(_base(
        "market.discovery_activity", profile, at, discovery_status, discovery_text,
        evidence_strength=discovery_strength, supporting_inputs=discovery_inputs, missing_inputs=missing,
        suggested_validation="Record who was interviewed, when, the sampling method, and the repeated problem evidence.",
        next_actions=["Separate interview count from evidence of a repeated, costly customer problem."],
        limitations=["The profile does not capture sampling quality or interview excerpts."] if discovery_inputs else [],
    ))

    wtp_inputs = []
    if customer and customer.willingness_to_pay_evidence:
        wtp_inputs.append(_input("profile.customer_market.willingness_to_pay_evidence", customer.willingness_to_pay_evidence))
    for field in ("paying_customers", "preorders", "signed_contracts"):
        if field in metrics:
            metric, path = metrics[field]
            wtp_inputs.append(_metric_input(metric, path))
    if not wtp_inputs:
        wtp_status, wtp_strength = "INSUFFICIENT_INFORMATION", "Insufficient"
        wtp_text = "No willingness-to-pay evidence or paid commitment is recorded; no demand conclusion is drawn."
        wtp_missing = ["profile.customer_market.willingness_to_pay_evidence", "paying_customers, preorders, or signed_contracts"]
    elif any(item.get("provenance") == "unknown" for item in wtp_inputs):
        wtp_status, wtp_strength = "INSUFFICIENT_INFORMATION", "Insufficient"
        wtp_text = "The available willingness-to-pay metric was marked unknown; it was not treated as zero."
        wtp_missing = []
    elif all(item.get("provenance") == "not_applicable" for item in wtp_inputs if "provenance" in item) and not any("provenance" not in item for item in wtp_inputs):
        wtp_status, wtp_strength = "NOT_APPLICABLE", "Insufficient"
        wtp_text = "The founder explicitly marked the available payment metrics not applicable; no payment or demand value was inferred."
        wtp_missing = []
    else:
        provenances = [item["provenance"] for item in wtp_inputs if "provenance" in item]
        wtp_status = "HYPOTHESIS" if "assumed" in provenances or not provenances else "INDICATED" if "estimated" in provenances else "CONFIRMED"
        wtp_strength = _evidence(provenances) if provenances else "Low"
        wtp_text = "A founder-reported payment measure or willingness-to-pay statement is recorded. This does not establish repeat purchasing, margin, or a representative market."
        wtp_missing = []
    result.append(_base(
        "market.willingness_to_pay", profile, at, wtp_status, wtp_text,
        applicability="not_applicable" if wtp_status == "NOT_APPLICABLE" else "applicable",
        evidence_strength=wtp_strength, supporting_inputs=wtp_inputs, missing_inputs=wtp_missing,
        suggested_validation="Compare observed paid commitments with the intended price and customer segment; distinguish deposits, preorders, and completed sales.",
        next_actions=["Track paid commitments and completed transactions separately from stated interest."],
        limitations=["Repeatability and customer representativeness are not captured by these fields."] if wtp_inputs else [],
    ))

    size_inputs = []
    if customer and customer.market_size_assumption:
        size_inputs.append(_input("profile.customer_market.market_size_assumption", customer.market_size_assumption))
    if "market_size" in metrics:
        metric, path = metrics["market_size"]
        size_inputs.append(_metric_input(metric, path))
    result.append(_base(
        "market.sizing_basis", profile, at,
        "HYPOTHESIS" if size_inputs else "INSUFFICIENT_INFORMATION",
        "A founder-provided market-size statement is present, but the structured profile does not establish its population, reachable share, or calculation basis."
        if size_inputs else "No market-size basis is recorded; no market-size conclusion is inferred.",
        evidence_strength="Low" if size_inputs else "Insufficient", supporting_inputs=size_inputs,
        missing_inputs=[] if size_inputs else ["customer population", "geography", "period", "sizing method"],
        suggested_validation="Document a bottom-up estimate with target population, geography, period, source, and reachable share.",
        next_actions=["Write down the sizing method and assumptions before using a market-size figure."],
        limitations=["No validated market-sizing methodology is represented in Phase 2A fields."] if size_inputs else [],
    ))
    return result


def _economics_findings(profile: StartupProfile, at: datetime, metrics: dict[str, tuple[ProfileMetric, str]]) -> list[DiagnosticFinding]:
    result: list[DiagnosticFinding] = []
    identity = profile.identity
    kind = identity.business_model if identity else None
    pairs = {
        "dtc_ecommerce": ("average_order_value", "fulfilment_cost"),
        "marketplace": ("average_order_value", "fulfilment_cost"),
    }
    pair = pairs.get(kind)
    if pair is None and "revenue_per_delivery_unit" in metrics and "variable_cost_per_unit" in metrics:
        pair = ("revenue_per_delivery_unit", "variable_cost_per_unit")
    if pair is None:
        result.append(_base(
            "economics.contribution_per_transaction", profile, at, "INSUFFICIENT_INFORMATION",
            "Select a business model and provide comparable revenue and variable-cost inputs before this calculation can be evaluated.",
            applicability="unknown" if kind in (None, "not_yet_determined") else "applicable",
            missing_inputs=["business model", "revenue per transaction", "variable cost per transaction"],
            suggested_validation="Record revenue and directly attributable variable cost for the same transaction type and currency.",
        ))
    else:
        revenue_id, cost_id = pair
        revenue = metrics.get(revenue_id)
        cost = metrics.get(cost_id)
        if not revenue or not cost:
            result.append(_base(
                "economics.contribution_per_transaction", profile, at, "INSUFFICIENT_INFORMATION",
                "Contribution per transaction cannot be calculated without both comparable revenue and variable-cost inputs; absent values are not zero.",
                missing_inputs=[name for name, item in ((revenue_id, revenue), (cost_id, cost)) if not item],
                supporting_inputs=[_metric_input(item[0], item[1]) for item in (revenue, cost) if item],
                formula=f"Revenue per transaction - variable costs per transaction; pair {revenue_id} with {cost_id}.",
                suggested_validation="Record both values for the same transaction definition, currency, and measurement context.",
                limitations=["The profile has no explicit customer cohort or transaction sampling fields."],
            ))
        else:
            rev, rev_path = revenue
            cost_metric, cost_path = cost
            inputs = [_metric_input(rev, rev_path), _metric_input(cost_metric, cost_path)]
            conflict = None
            alignment_missing = None
            if rev.currency != cost_metric.currency:
                conflict = "Currency differs between revenue and variable cost; no conversion rate was inferred."
            elif rev.unit != cost_metric.unit:
                conflict = "Transaction units differ between revenue and variable cost; values are not comparable."
            elif rev.period is not None and cost_metric.period is not None and rev.period != cost_metric.period:
                conflict = "Measurement periods differ; values are not compared."
            elif (rev.period is None) != (cost_metric.period is None):
                alignment_missing = "A period is missing for one input; aligned values cannot be established."
            elif rev.period_start is not None and cost_metric.period_start is not None and rev.period_start != cost_metric.period_start:
                conflict = "Measurement period start dates differ; values are not compared."
            elif (rev.period_start is None) != (cost_metric.period_start is None):
                alignment_missing = "A period start date is missing for one input; aligned values cannot be established."
            elif rev.period_end is not None and cost_metric.period_end is not None and rev.period_end != cost_metric.period_end:
                conflict = "Measurement period end dates differ; values are not compared."
            elif (rev.period_end is None) != (cost_metric.period_end is None):
                alignment_missing = "A period end date is missing for one input; aligned values cannot be established."
            elif rev.measurement_date and cost_metric.measurement_date and rev.measurement_date != cost_metric.measurement_date:
                conflict = "Measurement dates differ; values are not compared."
            elif (rev.measurement_date is None) != (cost_metric.measurement_date is None):
                alignment_missing = "A measurement date is missing for one input; aligned values cannot be established."
            if conflict:
                result.append(_base(
                    "economics.contribution_per_transaction", profile, at, "CONFLICTED", conflict,
                    evidence_strength="Insufficient", supporting_inputs=inputs,
                    formula="Revenue per transaction - variable costs per transaction; calculation withheld for incompatible inputs.",
                    suggested_validation="Resolve the currency, unit, period, and measurement-date mismatch and provide aligned values.",
                ))
            elif alignment_missing:
                result.append(_base(
                    "economics.contribution_per_transaction", profile, at, "INSUFFICIENT_INFORMATION", alignment_missing,
                    supporting_inputs=inputs,
                    missing_inputs=["matching measurement context for both values"],
                    formula="Revenue per transaction - variable costs per transaction; calculation withheld because measurement alignment is incomplete.",
                    suggested_validation="Record the same period/date context for both values, or remove period metadata only when both are genuinely per-transaction measures.",
                ))
            else:
                rev_bounds, cost_bounds = _bounds(rev), _bounds(cost_metric)
                if not rev_bounds or not cost_bounds:
                    not_applicable = any(metric.provenance == "not_applicable" for metric in (rev, cost_metric))
                    status, strength = ("NOT_APPLICABLE", "Insufficient") if not_applicable else ("INSUFFICIENT_INFORMATION", "Insufficient")
                    calculated = {}
                    explanation = "At least one selected metric is unknown or not applicable; no zero or midpoint was substituted."
                else:
                    low = rev_bounds[0] - cost_bounds[1]
                    high = rev_bounds[1] - cost_bounds[0]
                    status_inputs = [rev.provenance, cost_metric.provenance]
                    status, strength = _measured_status(status_inputs)
                    calculated = {"contribution_low": low, "contribution_high": high, "currency": rev.currency, "unit": rev.unit}
                    if status not in ("INSUFFICIENT_INFORMATION", "NOT_APPLICABLE") and low <= 0 <= high:
                        status, strength = "HYPOTHESIS", "Low" if "assumed" in status_inputs else "Moderate" if "estimated" in status_inputs else "Moderate"
                        explanation = "The calculated interval spans zero, so the supplied range cannot establish positive or negative contribution; no midpoint was invented."
                    elif high < 0:
                        explanation = "The supplied comparable values imply negative contribution across the stated interval. This is arithmetic on founder inputs, not a forecast; fixed costs and other revenue are excluded."
                    elif low >= 0:
                        status = "NOT_TRIGGERED" if status == "CONFIRMED" else status
                        explanation = "The supplied comparable values do not indicate negative contribution within the stated interval; this does not establish overall profitability."
                    else:
                        explanation = "The contribution calculation could not establish a direction from the available inputs."
                result.append(_base(
                    "economics.contribution_per_transaction", profile, at, status, explanation,
                    applicability="not_applicable" if status == "NOT_APPLICABLE" else "applicable",
                    evidence_strength=strength, supporting_inputs=inputs,
                    missing_inputs=["known numeric revenue and variable-cost values or explicit ranges"] if not calculated else [],
                    assumptions=["The two metrics describe the same transaction and cost allocation."] if not conflict else [],
                    formula="Contribution per transaction = revenue per transaction - variable costs per transaction. For ranges, [revenue_low - cost_high, revenue_high - cost_low]; no midpoint is used.",
                    calculated_values=calculated,
                    suggested_validation="Confirm both values use the same transaction, currency, period, and cost allocation.",
                    next_actions=["Review transaction pricing and directly attributable variable costs."] if calculated.get("contribution_high", 0) < 0 else [],
                    limitations=["This excludes fixed costs, taxes, financing, and other revenue; it is not a profitability or viability assessment."],
                    relationship="SUPPORTING",
                ))

    # The current profile has no attributable acquisition-spend/new-customer
    # pair and no period-aligned contribution profit per customer. Do not
    # convert a founder-entered CAC or payback metric into an audited formula.
    stage = identity.stage if identity else None
    revenue_metric = metrics.get("revenue_amount")
    has_revenue = bool(revenue_metric and _bounds(revenue_metric[0]) and _bounds(revenue_metric[0])[0] > 0)
    if stage == "pre_revenue" and has_revenue:
        result.append(_base(
            "economics.cac_payback", profile, at, "CONFLICTED",
            "The selected pre-revenue stage conflicts with a positive revenue value in the profile. CAC payback is withheld until the stage and revenue period are reconciled.",
            supporting_inputs=[_metric_input(revenue_metric[0], revenue_metric[1])],
            formula="CAC/payback not calculated while founder-entered stage and revenue data conflict.",
            suggested_validation="Confirm whether the startup is pre-revenue and whether the revenue value is current and attributable to this business.",
        ))
    elif stage in ("idea_concept", "validation_customer_discovery", "pre_revenue"):
        result.append(_not_applicable("economics.cac_payback", profile, at, "CAC payback is premature for the selected idea, discovery, or pre-revenue stage; this is not a negative finding."))
    elif stage == "not_sure_yet" or stage is None:
        result.append(_base("economics.cac_payback", profile, at, "INSUFFICIENT_INFORMATION", "Startup stage is not clear enough to determine whether acquisition payback is currently assessable.", applicability="unknown", missing_inputs=["profile.identity.stage"]))
    else:
        cac = metrics.get("customer_acquisition_cost")
        payback = metrics.get("cac_payback_period")
        inputs = [_metric_input(item[0], item[1]) for item in (cac, payback) if item]
        known = [item[0].provenance for item in (cac, payback) if item]
        status, strength = _measured_status(known) if known else ("INSUFFICIENT_INFORMATION", "Insufficient")
        if status != "INSUFFICIENT_INFORMATION":
            status, strength = "HYPOTHESIS", "Low" if "assumed" in known else "Moderate" if "estimated" in known else "Moderate"
        result.append(_base(
            "economics.cac_payback", profile, at, status,
            "The profile does not contain attributable acquisition spend, attributable new-customer count, and contribution profit per customer for aligned periods; a payback calculation is therefore withheld." if not inputs else "A founder-entered CAC/payback value is recorded but cannot be independently recalculated from the available profile fields.",
            evidence_strength=strength, supporting_inputs=inputs,
            missing_inputs=["attributable acquisition expenditure", "attributable new customers", "contribution profit per customer per period"],
            formula="CAC = attributable acquisition expenditure / attributable new customers. Payback = CAC / contribution profit per customer per period. Not calculated because Phase 2A has no aligned inputs for these terms.",
            suggested_validation="Capture acquisition spend and new customers for the same acquisition cohort, then contribution profit for that same customer cohort and period.",
            limitations=["No CAC or payback threshold is applied; the current schema does not capture the formula's required aligned components."],
            relationship="SUPPORTING",
        ))
    return result


def _retention_finding(profile: StartupProfile, at: datetime, metrics: dict[str, tuple[ProfileMetric, str]]) -> DiagnosticFinding:
    identity = profile.identity
    stage = identity.stage if identity else None
    if stage in ("idea_concept", "validation_customer_discovery"):
        return _not_applicable("traction.retention_cohort", profile, at, "Cohort retention is premature before the selected startup has revenue or a defined active customer base; absence is not treated as risk.")
    if stage == "not_sure_yet" or stage is None:
        return _base("traction.retention_cohort", profile, at, "INSUFFICIENT_INFORMATION", "Stage and customer base are not established, so retention applicability is unclear.", applicability="unknown", missing_inputs=["profile.identity.stage"])
    retention_fields = ("retention_rate", "churn_rate", "repeat_purchase_rate", "repeat_transactions")
    found = [(field, *metrics[field]) for field in retention_fields if field in metrics]
    inputs = [_metric_input(metric, path) for _, metric, path in found]
    missing = [field for field in retention_fields if field not in metrics]
    if not found:
        return _base("traction.retention_cohort", profile, at, "INSUFFICIENT_INFORMATION", "No retention, churn, or repeat-use measure is recorded. This is an information gap, not a retention failure.", missing_inputs=["cohort definition", "observation period", "retention or repeat-use measure"])
    if any(metric.provenance == "unknown" for _, metric, _ in found):
        return _base("traction.retention_cohort", profile, at, "INSUFFICIENT_INFORMATION", "A relevant metric was explicitly marked unknown and was not treated as zero.", supporting_inputs=inputs)
    provenances = [metric.provenance for _, metric, _ in found]
    status = "HYPOTHESIS" if "assumed" in provenances else "INDICATED" if "estimated" in provenances else "HYPOTHESIS"
    return _base(
        "traction.retention_cohort", profile, at, status,
        "A founder-reported aggregate retention/repeat metric is present, but Phase 2A does not capture cohort definition, customer denominator, or acquisition cohort; no retention-quality conclusion is drawn.",
        evidence_strength="Low", supporting_inputs=inputs,
        missing_inputs=["cohort definition", "customer denominator", "cohort start and observation end dates"],
        assumptions=["The reported measure refers to the intended customer group; this has not been verified."],
        suggested_validation="Track a defined acquisition cohort and report retained customers against its original customer denominator over a stated period.",
        limitations=["No growth, incentive, or channel attribution fields are available to assess acquisition dependence."],
    )


def _finance_finding(profile: StartupProfile, at: datetime, metrics: dict[str, tuple[ProfileMetric, str]]) -> DiagnosticFinding:
    relevant = [(key, *metrics[key]) for key in ("runway", "cash_balance", "monthly_operating_expense") if key in metrics]
    inputs = [_metric_input(metric, path) for _, metric, path in relevant]
    runway = next(((metric, path) for key, metric, path in relevant if key == "runway"), None)
    if runway:
        metric, _ = runway
        status, strength = _measured_status([metric.provenance])
        if status == "NOT_APPLICABLE":
            explanation = "Runway was explicitly marked not applicable; no value was inferred."
        elif status == "INSUFFICIENT_INFORMATION":
            explanation = "Runway was explicitly marked unknown; it was not treated as zero."
        else:
            explanation = "A founder-reported runway measure is available. This engine cannot verify its burn-rate basis or whether it supports the next milestone."
        return _base(
            "finance.cash_runway", profile, at, status,
            explanation,
            applicability="not_applicable" if status == "NOT_APPLICABLE" else "applicable",
            evidence_strength=strength, supporting_inputs=inputs,
            missing_inputs=["net cash burn calculation", "milestone target date"],
            formula="Use the reported runway as an input only. Cash runway = available cash / net cash burn per period is not calculated because net cash burn is absent.",
            limitations=["Monthly operating expense is not assumed to equal net burn; revenue and other cash flows are not represented."],
        )
    missing = ["cash balance", "net cash burn per period"]
    if any(key == "cash_balance" for key, _, _ in relevant):
        missing = ["net cash burn per period"]
    if any(key == "monthly_operating_expense" for key, _, _ in relevant):
        missing.append("operating cash inflows and other cash flows")
    return _base(
        "finance.cash_runway", profile, at, "INSUFFICIENT_INFORMATION",
        "Cash runway is not calculated: the profile lacks an explicit runway or net cash burn. Operating expense alone is not treated as burn, and missing values are not zero.",
        supporting_inputs=inputs, missing_inputs=missing,
        formula="Cash runway = available cash / net cash burn per period. Not calculated because net cash burn and aligned cash-flow periods are not represented by Phase 2A.",
        suggested_validation="Track cash balance and net cash burn over the same period, including cash inflows and outflows; compare with a dated milestone.",
        limitations=["The current contract cannot assess funding dependency or milestone feasibility."] if not inputs else [],
    )


def _marketplace_finding(profile: StartupProfile, at: datetime, metrics: dict[str, tuple[ProfileMetric, str]]) -> DiagnosticFinding:
    identity = profile.identity
    kind = identity.business_model if identity else None
    if kind != "marketplace":
        if kind in (None, "not_yet_determined"):
            return _base("marketplace.liquidity", profile, at, "INSUFFICIENT_INFORMATION", "Business model is unknown, so marketplace liquidity applicability cannot be determined.", applicability="unknown", missing_inputs=["profile.identity.business_model"])
        return _not_applicable("marketplace.liquidity", profile, at, "Marketplace liquidity applies only to the selected marketplace business model.")
    buyer = metrics.get("active_buyers")
    seller = metrics.get("active_sellers")
    if not buyer or not seller:
        return _base("marketplace.liquidity", profile, at, "INSUFFICIENT_INFORMATION", "Both active-buyer and active-seller observations are needed to describe marketplace participation; missing counts are not zero.", supporting_inputs=[_metric_input(x[0], x[1]) for x in (buyer, seller) if x], missing_inputs=[name for name, item in (("active_buyers", buyer), ("active_sellers", seller)) if not item], suggested_validation="Measure active buyers and sellers in the same geography and period, and define what counts as active.")
    bm, bp = buyer
    sm, sp = seller
    inputs = [_metric_input(bm, bp), _metric_input(sm, sp)]
    if bm.period != sm.period or bm.period_start != sm.period_start or bm.period_end != sm.period_end or (bm.measurement_date and sm.measurement_date and bm.measurement_date != sm.measurement_date):
        return _base("marketplace.liquidity", profile, at, "CONFLICTED", "Buyer and seller observations use different measurement contexts; no ratio or liquidity conclusion is calculated.", supporting_inputs=inputs, suggested_validation="Align buyer and seller definitions, geography, and measurement dates/periods.")
    if not bm.measurement_date and not bm.period_start and not bm.period_end:
        return _base("marketplace.liquidity", profile, at, "INSUFFICIENT_INFORMATION", "Buyer and seller counts have no shared measurement date or bounded period, so they are not compared.", supporting_inputs=inputs, missing_inputs=["shared measurement date or aligned period boundaries", "same-market geography"], suggested_validation="Measure both active counts for the same dated snapshot and geography.")
    provenances = [bm.provenance, sm.provenance]
    if bm.value is None or sm.value is None:
        status, strength, calculated = "INSUFFICIENT_INFORMATION", "Insufficient", {}
        explanation = "Buyer or seller count has no numeric value; no midpoint or zero was substituted."
    elif sm.value == 0:
        status, strength = _measured_status(provenances)
        calculated = {"active_buyers": bm.value, "active_sellers": sm.value, "buyer_to_seller_ratio": None}
        explanation = "The supplied seller count is zero, so a buyer-to-seller ratio is undefined. This records the supplied snapshot only and is not a forecast."
    else:
        status, strength = _measured_status(provenances)
        if status == "CONFIRMED":
            status = "HYPOTHESIS"  # a ratio is not a liquidity or viability finding
            strength = "Moderate"
        calculated = {"active_buyers": bm.value, "active_sellers": sm.value, "buyer_to_seller_ratio": bm.value / sm.value}
        explanation = "A ratio of the supplied active counts is shown as a descriptive observation only. The profile does not establish matching, transaction success, or sufficient liquidity."
    return _base("marketplace.liquidity", profile, at, status, explanation, evidence_strength=strength,
                 supporting_inputs=inputs, calculated_values=calculated,
                 formula="Descriptive ratio only: reported active buyers / reported active sellers. No threshold or viability judgment is applied.",
                 missing_inputs=["same-market geography", "definition of active", "successful match/transaction rate"],
                 suggested_validation="Measure successful matches and time-to-match for the same geography and period, split by buyer/seller cohort.",
                 limitations=["No universal buyer-to-seller ratio is asserted; aggregate counts are not a liquidity measure."],
                 relationship="INDEPENDENT")


def _model_specific_findings(profile: StartupProfile, at: datetime, metrics: dict[str, tuple[ProfileMetric, str]]) -> list[DiagnosticFinding]:
    result = []
    identity = profile.identity
    kind = identity.business_model if identity else None
    if kind == "hardware":
        details = profile.business_model_details
        fields = []
        if details and details.kind == "hardware":
            fields.extend((name, getattr(details, name)) for name in ("manufacturing_readiness", "tooling_and_production", "supply_chain_dependencies") if getattr(details, name))
        if "minimum_order_quantity" in metrics:
            m, path = metrics["minimum_order_quantity"]
            fields.append((path, m))
        if team_dependencies := (profile.team_operations.suppliers_or_distribution if profile.team_operations else None):
            fields.append(("profile.team_operations.suppliers_or_distribution", team_dependencies))
        if fields:
            support = [_metric_input(value, name) if isinstance(value, ProfileMetric) else _input(f"profile.business_model_details.{name}", value) for name, value in fields]
            result.append(_base("hardware.production_readiness", profile, at, "HYPOTHESIS", "Founder-entered production, MOQ, or supplier information is recorded. The profile does not establish supplier concentration, lead time, tooling cost, or ability to fund a production run.", evidence_strength="Low", supporting_inputs=support, missing_inputs=["supplier count and concentration", "manufacturing lead time", "tooling cost", "cash required for minimum order", "validated demand for the production run"], suggested_validation="Document supplier alternatives, quoted lead times and tooling/MOQ commitments, then compare required cash with validated demand.", limitations=["No manufacturing readiness threshold is applied."]))
        else:
            result.append(_base("hardware.production_readiness", profile, at, "INSUFFICIENT_INFORMATION", "Hardware is selected, but no production-readiness or MOQ evidence is recorded; this is not a failure finding.", missing_inputs=["manufacturing readiness", "minimum order quantity", "tooling and supplier dependencies"]))
    elif kind in (None, "not_yet_determined"):
        result.append(_base("hardware.production_readiness", profile, at, "INSUFFICIENT_INFORMATION", "Business model is unclear, so hardware applicability cannot be established.", applicability="unknown", missing_inputs=["profile.identity.business_model"]))
    else:
        result.append(_not_applicable("hardware.production_readiness", profile, at, "Production-readiness checks apply only to the selected hardware business model."))

    team = profile.team_operations
    gap = team.capability_gaps if team else None
    if gap:
        result.append(_base("team.capability_gaps", profile, at, "HYPOTHESIS", "A capability gap was explicitly identified by the founder. Team size is not used to infer gaps, and impact depends on the stated milestones.", evidence_strength="Low", supporting_inputs=[_input("profile.team_operations.capability_gaps", gap)], assumptions=["The founder-entered gap is accurate and relevant to a current milestone."], suggested_validation="Map each stated gap to an upcoming milestone, owner, mitigation, and date.", limitations=["No team-size threshold or capability taxonomy is present."]))
    else:
        result.append(_base("team.capability_gaps", profile, at, "INSUFFICIENT_INFORMATION", "No capability-gap assessment is recorded. A small team or missing team-size value is not treated as a gap.", missing_inputs=["founder-confirmed capability gaps", "milestone requiring the capability"]))

    if kind in ("fintech", "biotech_medtech"):
        pathway = None
        path = None
        if profile.business_model_details and profile.business_model_details.kind == kind:
            if kind == "fintech":
                pathway = profile.business_model_details.licensing_status or profile.business_model_details.product_category
                path = "profile.business_model_details.licensing_status" if profile.business_model_details.licensing_status else "profile.business_model_details.product_category"
            else:
                pathway = profile.business_model_details.regulatory_pathway
                path = "profile.business_model_details.regulatory_pathway"
        pathway = pathway or (team.regulatory_context if team else None)
        path = path if pathway and path else "profile.team_operations.regulatory_context"
        result.append(_base("operations.regulatory_pathway", profile, at, "HYPOTHESIS" if pathway else "INSUFFICIENT_INFORMATION", "Founder-entered regulatory information is recorded but is not a legal determination." if pathway else "The selected model can involve regulated activity, but no regulatory pathway information is recorded; no obligation or violation is inferred.", evidence_strength="Low" if pathway else "Insufficient", supporting_inputs=[_input(path, pathway)] if pathway else [], missing_inputs=[] if pathway else ["product activity", "target jurisdiction", "applicable regulator and pathway"], suggested_validation="Confirm product activity and target jurisdiction with qualified regulatory counsel or the relevant authority.", limitations=["This deterministic engine does not determine legal applicability or provide legal advice."]))
    elif kind in (None, "not_yet_determined"):
        result.append(_base("operations.regulatory_pathway", profile, at, "INSUFFICIENT_INFORMATION", "Business model and jurisdiction are insufficient to determine regulatory applicability; no obligation is inferred.", applicability="unknown", missing_inputs=["business model", "target jurisdiction", "regulated product/activity description"]))
    else:
        result.append(_base("operations.regulatory_pathway", profile, at, "INSUFFICIENT_INFORMATION", "The selected business-model category alone cannot establish whether a specific product activity and jurisdiction create regulatory obligations.", applicability="unknown", missing_inputs=["product activity", "target jurisdiction", "applicable regulator and pathway"], suggested_validation="Describe the product activity and target jurisdiction, then verify obligations with the relevant authority or qualified counsel."))

    dependency = team.critical_dependencies if team else None
    if dependency:
        result.append(_base("operations.critical_dependencies", profile, at, "HYPOTHESIS", "A critical dependency was identified by the founder. Concentration, substitutability, and operational impact are not independently established.", evidence_strength="Low", supporting_inputs=[_input("profile.team_operations.critical_dependencies", dependency)], suggested_validation="For each dependency, document alternatives, substitution time, contractual terms, and the affected operation.", limitations=["The current profile has no dependency inventory or concentration measure."]))
    else:
        result.append(_base("operations.critical_dependencies", profile, at, "INSUFFICIENT_INFORMATION", "No critical dependency information is recorded; absence of a note does not establish that a dependency exists or is absent.", missing_inputs=["critical supplier/platform/infrastructure dependencies", "alternatives and substitution time"]))
    return result


def evaluate_profile(
    profile: StartupProfile | dict[str, Any] | None,
    *,
    evaluated_at: datetime | None = None,
) -> DiagnosticReport:
    """Evaluate a validated Phase 2A profile without reading model inputs.

    Pass a fixed ``evaluated_at`` when byte-for-byte reproducible report payloads
    are needed. Finding logic and values are otherwise deterministic for a fixed
    profile and rule version; the default timestamp records evaluation time.
    Legacy analyses with no profile return an empty, explicitly unavailable report.
    """
    at = _now(evaluated_at)
    if profile is None:
        return DiagnosticReport(
            engine_version=ENGINE_VERSION,
            profile_schema_version=None,
            profile_available=False,
            evaluated_at=at,
            findings=[],
            limitations=["No Phase 2A profile is attached to this analysis. No founder facts or findings were inferred."],
        )
    parsed = profile if isinstance(profile, StartupProfile) else StartupProfile.model_validate(profile)
    metrics = _metrics(parsed)
    findings = [
        *_market_findings(parsed, at, metrics),
        *_economics_findings(parsed, at, metrics),
        _retention_finding(parsed, at, metrics),
        _finance_finding(parsed, at, metrics),
        _marketplace_finding(parsed, at, metrics),
        *_model_specific_findings(parsed, at, metrics),
    ]

    # These findings describe connected mechanisms; links are informational,
    # never summed into a score or treated as independent severity counts.
    by_id = {finding.diagnostic_id: finding for finding in findings}
    contribution = by_id.get("economics.contribution_per_transaction")
    payback = by_id.get("economics.cac_payback")
    if contribution and payback:
        contribution.related_findings.append(payback.finding_id)
        payback.related_findings.append(contribution.finding_id)
        payback.relationship_type = "SUPPORTING"

    return DiagnosticReport(
        engine_version=ENGINE_VERSION,
        profile_schema_version=parsed.profile_schema_version,
        profile_available=True,
        evaluated_at=at,
        findings=findings,
        limitations=[
            "Findings summarize founder-provided profile data and deterministic arithmetic; they are not predictions of startup failure.",
            "No universal benchmarks, aggregate risk score, or statistical-model outputs are used.",
        ],
    )
