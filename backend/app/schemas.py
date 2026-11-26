"""Request and response shapes. Pydantic checks types and ranges before any model code runs."""
import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, field_validator, model_validator

Band = Literal["Low", "Medium", "High", "Critical"]
Short = Annotated[str, Field(min_length=1, max_length=60)]


class Stage1Request(BaseModel):
    """Idea stage: where it is and what industry it is in."""
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True,
        json_schema_extra={"examples": [{"country": "USA", "state": "CA", "tags": ["Software", "Mobile"]}]})

    country: str = Field(pattern=r"^[A-Za-z]{3}$", description="ISO 3-letter code, e.g. USA, IND, GBR")
    state: str | None = Field(default=None, pattern=r"^[A-Za-z]{2,4}$", description="US state code. Only for USA.")
    tags: list[Short] = Field(min_length=1, max_length=5, description="1 to 5 industry tags from /v1/meta")

    @field_validator("country", "state")
    @classmethod
    def upper(cls, v):
        return v.upper() if v else v

    @model_validator(mode="after")
    def state_rules(self):
        if self.country == "USA" and not self.state:
            raise ValueError("state is required when country is USA")
        if self.country != "USA" and self.state:
            raise ValueError("state is only used when country is USA")
        return self


class Stage2Request(BaseModel):
    """Running startup: adds funding and traction."""
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True,
        json_schema_extra={"examples": [{
            "category": "software", "state": "CA", "funding_total_usd": 250000, "funding_rounds": 2,
            "has_VC": False, "has_angel": True, "has_roundA": True, "has_roundB": False,
            "has_roundC": False, "has_roundD": False, "avg_participants": 2.0, "relationships": 5,
            "age_first_funding_year": 1.0, "age_last_funding_year": 2.0}]})

    category: str = Field(pattern=r"^[A-Za-z0-9_ &-]{1,40}$", description="industry from /v1/meta")
    state: str | None = Field(
        default=None, pattern=r"^[A-Za-z]{2,5}$", validate_default=True,
        description="US state code, or leave out / send OTHER for a startup outside the US or in an unlisted state")
    funding_total_usd: float = Field(ge=0, le=1e11)
    funding_rounds: int = Field(ge=1, le=30)
    has_VC: StrictBool
    has_angel: StrictBool
    has_roundA: StrictBool
    has_roundB: StrictBool
    has_roundC: StrictBool
    has_roundD: StrictBool
    avg_participants: float = Field(ge=0, le=50, description="average investors per funding round")
    relationships: int = Field(ge=0, le=500, description="people linked to the company")
    age_first_funding_year: float = Field(ge=-10, le=60, description="years from founding to first funding")
    age_last_funding_year: float = Field(ge=-10, le=60, description="years from founding to latest funding")

    @field_validator("state")
    @classmethod
    def state_or_other(cls, v):
        v = v.upper() if v else "OTHER"                  # missing means "not a listed US state"
        if len(v) == 5 and v != "OTHER":                 # the pattern allows 5 letters only so OTHER fits
            raise ValueError("state must be a 2 to 4 letter US state code, or OTHER")
        return v

    @model_validator(mode="after")
    def order(self):
        if self.age_last_funding_year < self.age_first_funding_year:
            raise ValueError("age_last_funding_year cannot be earlier than age_first_funding_year")
        return self


class Factor(BaseModel):
    feature: str
    label: str
    value: str | int | float
    contribution: float = Field(description="signed TreeSHAP contribution to the model's raw log-odds score, not a percent probability")
    effect: Literal["raises risk", "lowers risk"]
    impact: float = Field(description="share of total absolute SHAP attribution for this run; related features may share attribution")


class Branch(BaseModel):
    group: str
    label: str
    band: Band | None = Field(default=None, description="Not assigned: the model has no validated branch severity bands")
    effect: Literal["raises", "lowers", "neutral"]
    net_shap: float
    factors: list[Factor]


class Tree(BaseModel):
    label: str
    band: Band
    probability: float
    children: list[Branch]


class CohortSlice(BaseModel):
    key: str
    label: str
    detail: str
    n: int
    enough: bool = Field(description="false when there are too few startups to show a percentage")
    closed_share: float | None
    low: float | None = Field(description="lower end of a 95% range for the share")
    high: float | None


class Cohort(BaseModel):
    basis: str
    overall: dict[str, float | int]
    slices: list[CohortSlice]
    note: str


class CaseSource(BaseModel):
    title: str
    publisher: str
    url: str
    published: str
    kind: str


class CaseOut(BaseModel):
    id: str
    name: str
    years: str
    sector: str
    what: str
    how_it_failed: str
    reasons: list[str]
    sources: list[CaseSource]
    verified_on: str
    matched_on: list[str]
    match_category: Literal["direct_business_model", "industry_adjacent", "mechanism_based", "contextual"] = "contextual"
    shared_characteristics: list[str] = Field(default_factory=list)
    important_differences: list[str] = Field(default_factory=list)
    outcome_status: str = "unknown"
    historical_outcome: str = ""
    documented_lesson: str = ""
    comparison_limitations: list[str] = Field(default_factory=list)


class CasesResponse(BaseModel):
    matched: bool = Field(description="false when no case meets the minimum profile-overlap criteria")
    cases: list[CaseOut]
    note: str
    library_status: Literal["available", "limited", "unavailable"] = "limited"
    library_count: int = 0


class EvidenceSource(BaseModel):
    title: str
    publisher: str
    journal: str = ""
    authors: list[str] = Field(default_factory=list)
    doi: str | None = None
    url: str
    published: str
    year: str = ""
    venue_status: str = Field(description="Provider-reported source screening, not an independent quality or peer-review determination")
    excerpt: str
    matched_terms: list[str]
    relation: Literal["direct", "contextual"] = "contextual"
    focus: str = ""
    openalex_id: str | None = None
    publication_type: str = "unknown"
    metadata_status: str = "OpenAlex record; bibliographic metadata not independently verified"
    access_status: Literal["abstract_only", "metadata_only", "full_text_reviewed"] = "abstract_only"
    open_access_url: str | None = None
    retrieved_at: str = ""
    relevance_dimensions: list[str] = Field(default_factory=list)
    source_type: str = "unknown"


class EvidenceResponse(BaseModel):
    provider: str
    node: str
    sources: list[EvidenceSource]
    note: str
    state: Literal["relevant_results", "partial", "no_results", "filtered_out", "weak_relevance", "provider_unavailable", "provider_timeout", "rate_limited", "provider_error", "insufficient_query_context"] = "no_results"
    queries_attempted: int = 0
    query_results: list[dict[str, Any]] = Field(default_factory=list)
    records_retrieved: int = 0
    candidates_filtered: int = 0
    weak_candidates: int = 0
    retrieved_at: str = ""
    snapshot_id: str | None = None
    snapshot_saved: bool = False
    snapshot_persistence_note: str = ""


class EvidenceSnapshotSummary(BaseModel):
    id: str
    retrieved_at: str = ""
    created_at: str
    state: str


class EvidenceSnapshotHistory(BaseModel):
    snapshots: list[EvidenceSnapshotSummary]


class PredictionResponse(BaseModel):
    stage: Literal["stage1", "stage2"]
    probability: float = Field(description="Legacy calibrated classifier score for the dataset's terminal-outcome label; not an individual startup failure probability")
    band: Band = Field(description="Legacy descriptive band of the historical classifier score; not a prospective startup risk band")
    similar_startups_failure_rate: float = Field(description="Legacy training-sample closed share within this score band; not an individual startup probability")
    inference_status: Literal["legacy_descriptive_only"] = "legacy_descriptive_only"
    model_version: str = Field(description="SHA-256 identifier of the loaded model artifact")
    feature_schema_version: str = Field(description="SHA-256 identifier of the ordered model feature list")
    prediction_horizon: None = Field(default=None, description="No prediction horizon is established by the current outcome data")
    output_semantics: Literal["historical_terminal_outcome_association"] = "historical_terminal_outcome_association"
    confidence: Literal["limited", "moderate", "low"] | None = Field(default=None, description="No confidence category is emitted because the current validation does not calibrate one")
    benchmark: str = Field(description="who the comparison is made against, e.g. 'US benchmark'")
    cohort: Cohort | None = Field(default=None, description="real counts for similar startups (Stage 1 only)")
    tree: Tree
    notes: list[str]
    limitations: list[str]
    disclaimer: str


# ---- saved analyses ------------------------------------------------------------
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80,
                                         pattern=r"^[^\x00-\x1f\x7f]+$")]   # no control characters


_NO_CONTROL = r"^[^\x00-\x08\x0b-\x1f\x7f]*$"   # no control characters (newlines are fine)
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=800, pattern=_NO_CONTROL)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200, pattern=_NO_CONTROL)]

ProfileStage = Literal[
    "idea_concept", "validation_customer_discovery", "mvp_product_development", "pre_revenue",
    "early_revenue", "early_growth", "scaling", "mature_established", "not_sure_yet",
]
BusinessModelType = Literal[
    "b2b_saas", "b2c_saas", "marketplace", "dtc_ecommerce", "hardware", "fintech",
    "biotech_medtech", "services_consulting", "consumer_application", "platform_developer_tools",
    "other", "not_yet_determined",
]
Provenance = Literal["measured", "estimated", "assumed", "unknown", "not_applicable"]
Applicability = Literal["applicable", "unknown", "not_applicable"]
MetricField = Literal[
    "customer_interviews", "market_size", "paying_customers", "active_users", "revenue_amount",
    "growth_rate", "retention_rate", "churn_rate", "signed_contracts", "preorders", "pilots",
    "average_selling_price", "variable_cost_per_unit", "gross_margin", "contribution_margin",
    "customer_acquisition_cost", "cac_payback_period", "cash_balance", "monthly_operating_expense",
    "runway", "team_size", "average_contract_value", "sales_cycle", "transaction_volume", "take_rate",
    "active_buyers", "active_sellers", "repeat_transactions", "orders", "average_order_value",
    "repeat_purchase_rate", "fulfilment_cost", "bill_of_materials", "minimum_order_quantity",
    "utilization", "revenue_per_delivery_unit",
]

METRIC_UNITS = {
    "customer_interviews": "interviews", "market_size": "currency", "paying_customers": "customers",
    "active_users": "users", "revenue_amount": "currency", "growth_rate": "percent",
    "retention_rate": "percent", "churn_rate": "percent", "signed_contracts": "contracts",
    "preorders": "orders", "pilots": "pilots", "average_selling_price": "currency/customer",
    "variable_cost_per_unit": "currency/unit", "gross_margin": "percent", "contribution_margin": "percent",
    "customer_acquisition_cost": "currency/customer", "cac_payback_period": "months",
    "cash_balance": "currency", "monthly_operating_expense": "currency/month", "runway": "months",
    "team_size": "people", "average_contract_value": "currency/year", "sales_cycle": "days",
    "transaction_volume": "currency", "take_rate": "percent", "active_buyers": "buyers",
    "active_sellers": "sellers", "repeat_transactions": "percent", "orders": "orders",
    "average_order_value": "currency/order", "repeat_purchase_rate": "percent",
    "fulfilment_cost": "currency/order", "bill_of_materials": "currency/unit",
    "minimum_order_quantity": "units", "utilization": "percent", "revenue_per_delivery_unit": "currency/unit",
}
MONEY_METRICS = {
    "market_size", "revenue_amount", "average_selling_price", "variable_cost_per_unit",
    "customer_acquisition_cost", "cash_balance", "monthly_operating_expense", "average_contract_value",
    "transaction_volume", "average_order_value", "fulfilment_cost", "bill_of_materials", "revenue_per_delivery_unit",
}
PERIOD_METRICS = {"revenue_amount", "growth_rate", "retention_rate", "churn_rate"}
PERCENT_METRICS = {"retention_rate", "churn_rate", "gross_margin", "contribution_margin", "take_rate", "repeat_transactions", "repeat_purchase_rate", "utilization"}


class ProfileMetric(BaseModel):
    """A numeric founder input with explicit provenance and its original measurement context."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    field_id: MetricField
    value: float | None = Field(default=None, allow_inf_nan=False)
    unit: str | None = Field(default=None, max_length=32)
    currency: str | None = Field(default=None, pattern=r"^[A-Za-z]{3}$")
    provenance: Provenance
    measurement_date: date | None = None
    period: Literal["day", "week", "month", "quarter", "year", "lifetime", "custom", "point_in_time"] | None = None
    period_start: date | None = None
    period_end: date | None = None
    source_reference: ShortText | None = None
    range_low: float | None = Field(default=None, allow_inf_nan=False)
    range_high: float | None = Field(default=None, allow_inf_nan=False)
    confirmed_by_user: StrictBool
    applicability: Applicability

    @model_validator(mode="after")
    def check_provenance_units_and_ranges(self):
        if self.provenance in ("unknown", "not_applicable"):
            expected = "unknown" if self.provenance == "unknown" else "not_applicable"
            if self.applicability != expected or any(v is not None for v in (self.value, self.range_low, self.range_high)):
                raise ValueError(f"{self.provenance} values must be explicitly selected without a numeric value or range")
            if self.unit or self.currency or self.period or self.period_start or self.period_end:
                raise ValueError("unknown and not-applicable values cannot include measurement units, currency, or periods")
            if not self.confirmed_by_user:
                raise ValueError("unknown and not-applicable selections must be confirmed by the founder")
            return self

        if self.applicability != "applicable" or not self.confirmed_by_user:
            raise ValueError("provided values must be applicable and confirmed by the founder")
        if self.value is None and self.range_low is None and self.range_high is None:
            raise ValueError("provide a value or a range, or select unknown/not applicable")
        if (self.range_low is None) != (self.range_high is None):
            raise ValueError("a range requires both lower and upper bounds")
        if self.range_low is not None and self.range_high is not None and self.range_low > self.range_high:
            raise ValueError("range lower bound cannot exceed its upper bound")
        if self.value is not None and self.range_low is not None and not self.range_low <= self.value <= self.range_high:
            raise ValueError("value must fall within the supplied range")
        values = [value for value in (self.value, self.range_low, self.range_high) if value is not None]
        signed_metrics = {"growth_rate", "gross_margin", "contribution_margin"}
        if self.field_id not in signed_metrics and any(value < 0 for value in values):
            raise ValueError("this metric cannot be negative")
        if self.field_id in PERCENT_METRICS and any(value > 100 for value in values):
            raise ValueError("percentage values must be between 0 and 100")
        expected_unit = METRIC_UNITS[self.field_id]
        if self.unit != expected_unit:
            raise ValueError(f"{self.field_id} must use the {expected_unit} unit")
        if self.field_id in MONEY_METRICS:
            if not self.currency or self.currency != self.currency.upper():
                raise ValueError("currency is required for monetary values and must use a three-letter code")
        elif self.currency is not None:
            raise ValueError("currency is only valid for monetary fields")
        if self.field_id in PERIOD_METRICS and self.period in (None, "point_in_time"):
            raise ValueError("this metric needs a measurement period, not a point-in-time value")
        if self.period == "custom" and (self.period_start is None or self.period_end is None):
            raise ValueError("a custom period requires both start and end dates")
        if (self.period_start is None) != (self.period_end is None):
            raise ValueError("a date range requires both period start and end")
        if self.period_start and self.period_end and self.period_start > self.period_end:
            raise ValueError("period start cannot be after period end")
        return self


class ProfileIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    business_model: BusinessModelType | None = None
    stage: ProfileStage | None = None
    problem: LongText | None = None
    proposed_solution: LongText | None = None
    operating_geography: ShortText | None = None
    target_market_geography: ShortText | None = None


class CustomerMarketProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    customer_type: Literal["b2b", "b2c", "b2b2c", "other", "not_sure_yet"] | None = None
    customer_segment: ShortText | None = None
    customer_description: LongText | None = None
    discovery_evidence: LongText | None = None
    willingness_to_pay_evidence: LongText | None = None
    existing_alternatives: LongText | None = None
    market_size_assumption: LongText | None = None
    metrics: list[ProfileMetric] = Field(default_factory=list, max_length=4)


class ProductTractionProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    product_status: Literal["concept", "prototype", "mvp", "beta", "launched", "not_sure_yet"] | None = None
    customer_validation: LongText | None = None
    acquisition_channel: ShortText | None = None
    metrics: list[ProfileMetric] = Field(default_factory=list, max_length=10)


class EconomicsProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    revenue_model: ShortText | None = None
    pricing_model: ShortText | None = None
    acquisition_channel: ShortText | None = None
    metrics: list[ProfileMetric] = Field(default_factory=list, max_length=7)


class FinanceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    funding_status: Literal["bootstrapped", "grants", "angel", "venture", "debt", "mixed", "not_funded", "not_sure_yet"] | None = None
    funding_sources: ShortText | None = None
    upcoming_milestones: LongText | None = None
    metrics: list[ProfileMetric] = Field(default_factory=list, max_length=5)


class TeamOperationsProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    team_capabilities: LongText | None = None
    capability_gaps: LongText | None = None
    critical_dependencies: LongText | None = None
    suppliers_or_distribution: LongText | None = None
    technology_constraints: LongText | None = None
    regulatory_context: LongText | None = None
    metrics: list[ProfileMetric] = Field(default_factory=list, max_length=2)


class B2BSaaSDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["b2b_saas"]
    sales_cycle_notes: ShortText | None = None
    renewal_notes: ShortText | None = None


class MarketplaceDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["marketplace"]
    buyer_group: ShortText | None = None
    seller_group: ShortText | None = None
    liquidity_notes: LongText | None = None
    metrics: list[ProfileMetric] = Field(default_factory=list, max_length=5)


class DTCDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["dtc_ecommerce"]
    fulfilment_notes: ShortText | None = None
    metrics: list[ProfileMetric] = Field(default_factory=list, max_length=5)


class HardwareDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["hardware"]
    manufacturing_readiness: ShortText | None = None
    tooling_and_production: LongText | None = None
    supply_chain_dependencies: LongText | None = None
    metrics: list[ProfileMetric] = Field(default_factory=list, max_length=2)


class FintechDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["fintech"]
    product_category: ShortText | None = None
    regulatory_jurisdiction: ShortText | None = None
    licensing_status: ShortText | None = None
    infrastructure_dependencies: LongText | None = None


class BiotechMedtechDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["biotech_medtech"]
    development_or_validation_stage: ShortText | None = None
    regulatory_pathway: ShortText | None = None
    capital_and_development_milestones: LongText | None = None


class ServicesDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["services_consulting"]
    service_type: ShortText | None = None
    delivery_capacity_notes: ShortText | None = None
    metrics: list[ProfileMetric] = Field(default_factory=list, max_length=2)


BusinessModelDetails = Annotated[
    Union[B2BSaaSDetails, MarketplaceDetails, DTCDetails, HardwareDetails, FintechDetails, BiotechMedtechDetails, ServicesDetails],
    Field(discriminator="kind"),
]


class StartupProfile(BaseModel):
    """Versioned founder-supplied profile. It is descriptive input, never a risk score."""
    model_config = ConfigDict(extra="forbid")

    profile_schema_version: Literal[1] = 1
    last_updated_at: date = Field(default_factory=date.today)
    identity: ProfileIdentity | None = None
    customer_market: CustomerMarketProfile | None = None
    product_traction: ProductTractionProfile | None = None
    economics: EconomicsProfile | None = None
    finance: FinanceProfile | None = None
    team_operations: TeamOperationsProfile | None = None
    business_model_details: BusinessModelDetails | None = None

    @model_validator(mode="after")
    def check_profile_coherence_and_duplicate_metrics(self):
        details = self.business_model_details
        selected = self.identity.business_model if self.identity else None
        if details and selected != details.kind:
            raise ValueError("business-model-specific details must match the selected business model")
        groups = [self.customer_market, self.product_traction, self.economics, self.finance, self.team_operations]
        if details and hasattr(details, "metrics"):
            groups.append(details)
        seen: set[str] = set()
        for group in groups:
            if not group:
                continue
            for metric in getattr(group, "metrics", []):
                if metric.field_id in seen:
                    raise ValueError(f"conflicting duplicate metric '{metric.field_id}' appears more than once")
                seen.add(metric.field_id)
        return self


class Context(BaseModel):
    """What the founder tells us about the startup. Saved with the analysis for context only: the risk models
    never see it, so it cannot change the band."""
    model_config = ConfigDict(extra="forbid")

    concept: LongText | None = Field(default=None, description="what the startup does")
    vision: LongText | None = Field(default=None, description="where it is going")
    customer: ShortText | None = None
    revenue_model: ShortText | None = Field(default=None, description="how it makes money")
    startup_stage: Literal["idea", "prototype", "launched", "earning"] | None = None
    team_size: int | None = Field(default=None, ge=1, le=500)
    biggest_worry: ShortText | None = None
    profile: StartupProfile | None = None

    @field_validator("*", mode="after")
    @classmethod
    def blank_means_missing(cls, v):
        return None if isinstance(v, str) and not v else v

    @model_validator(mode="after")
    def limit_serialized_context_size(self):
        # Existing PostgreSQL context JSONB is capped below 16 KiB. Leave room
        # for JSONB overhead and the rest of POST /v1/analyses under its 16 KiB cap.
        if len(self.model_dump_json(exclude_none=True).encode("utf-8")) > 12_500:
            raise ValueError("profile and notes are too large to save together; shorten text or remove optional detail")
        return self


class AnalysisCreate(BaseModel):
    """Run a prediction and save it. 'input' must match the chosen stage's request."""
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{
        "title": "My first idea", "stage": "stage1", "parent_id": None,
        "input": {"country": "USA", "state": "CA", "tags": ["Software", "Mobile"]}}]})

    title: Title
    stage: Literal["stage1", "stage2"]
    parent_id: uuid.UUID | None = Field(default=None, description="set when this is a new version of an earlier analysis")
    input: dict[str, Any]
    context: Context | None = None


class AnalysisSummary(BaseModel):
    id: uuid.UUID
    stage: Literal["stage1", "stage2"]
    title: str
    band: Band
    probability: float
    parent_id: uuid.UUID | None
    created_at: datetime


class AnalysisOut(AnalysisSummary):
    input: dict[str, Any]
    result: dict[str, Any]   # a snapshot of what the user saw, so old analyses never change
    context: dict[str, Any] | None = None   # what the founder wrote. Missing on analyses saved before this existed.
    # Additive report-time computation; never persisted with the analysis row.
    diagnostics: dict[str, Any] | None = None
    diagnostics_state: Literal["available", "no_profile", "unavailable"] | None = None
