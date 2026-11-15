"""Request and response shapes. Pydantic checks types and ranges before any model code runs."""
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

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


class CasesResponse(BaseModel):
    matched: bool = Field(description="false when the library has no direct industry or idea-text match")
    cases: list[CaseOut]
    note: str


class EvidenceSource(BaseModel):
    title: str
    publisher: str
    journal: str = ""
    authors: list[str] = Field(default_factory=list)
    doi: str | None = None
    url: str
    published: str
    year: str = ""
    venue_status: str
    excerpt: str
    matched_terms: list[str]
    relation: Literal["direct", "contextual"] = "contextual"
    focus: str = ""


class EvidenceResponse(BaseModel):
    provider: str
    node: str
    sources: list[EvidenceSource]
    note: str


class PredictionResponse(BaseModel):
    stage: Literal["stage1", "stage2"]
    probability: float = Field(description="calibrated chance of closing, among startups like those in the data")
    band: Band
    similar_startups_failure_rate: float = Field(description="share of training startups in this band that closed")
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

    @field_validator("*", mode="after")
    @classmethod
    def blank_means_missing(cls, v):
        return None if isinstance(v, str) and not v else v


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
