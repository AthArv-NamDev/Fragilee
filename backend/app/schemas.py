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
    state: str = Field(pattern=r"^[A-Za-z]{2,4}$", description="US state code")
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
    def upper(cls, v):
        return v.upper()

    @model_validator(mode="after")
    def order(self):
        if self.age_last_funding_year < self.age_first_funding_year:
            raise ValueError("age_last_funding_year cannot be earlier than age_first_funding_year")
        return self


class Factor(BaseModel):
    feature: str
    label: str
    value: str | float
    effect: Literal["raises risk", "lowers risk"]
    impact: float = Field(description="share of the total push on this prediction, 0 to 1")


class Branch(BaseModel):
    group: str
    label: str
    band: Band = Field(description="how strongly this branch pushes risk up. Low = no push or lowers risk")
    effect: Literal["raises", "lowers", "neutral"]
    net_shap: float
    factors: list[Factor]


class Tree(BaseModel):
    label: str
    band: Band
    probability: float
    children: list[Branch]


class PredictionResponse(BaseModel):
    stage: Literal["stage1", "stage2"]
    probability: float = Field(description="calibrated chance of closing, among startups like those in the data")
    band: Band
    similar_startups_failure_rate: float = Field(description="share of training startups in this band that closed")
    base_failure_rate: float
    confidence: Literal["limited", "moderate", "low"]
    tree: Tree
    notes: list[str]
    limitations: list[str]
    disclaimer: str


# ---- saved analyses ------------------------------------------------------------
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80,
                                         pattern=r"^[^\x00-\x1f\x7f]+$")]   # no control characters


class AnalysisCreate(BaseModel):
    """Run a prediction and save it. 'input' must match the chosen stage's request."""
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{
        "title": "My first idea", "stage": "stage1", "parent_id": None,
        "input": {"country": "USA", "state": "CA", "tags": ["Software", "Mobile"]}}]})

    title: Title
    stage: Literal["stage1", "stage2"]
    parent_id: uuid.UUID | None = Field(default=None, description="set when this is a new version of an earlier analysis")
    input: dict[str, Any]


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
