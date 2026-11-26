"""Validation primitives for a prospective, append-only outcome observation programme.

This module does not create observations or assign model labels. An outcome record
is an evidence-backed status observation; label construction needs a separately
specified index date and horizon.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator


OutcomeStatus = Literal[
    "operational_active", "inactive_dormant", "confirmed_closure", "acquired",
    "ipo", "merged", "bankruptcy_insolvency", "unknown", "right_censored",
]


class OutcomeSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1, max_length=200)
    source_url: AnyHttpUrl
    retrieved_at: date
    evidence_note: str = Field(min_length=1, max_length=1000)
    verification_state: Literal["pending", "verified", "rejected"] = "pending"


class OutcomeObservation(BaseModel):
    """One time-stamped status record. Corrections append and reference this record."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    observation_id: str = Field(pattern=r"^[0-9a-fA-F-]{36}$")
    company_key: str = Field(min_length=1, max_length=128, description="Stable pseudonymous identifier; no company name or personal data.")
    observed_at: date
    status: OutcomeStatus
    event_date: date | None = None
    follow_up_due: date | None = None
    sources: list[OutcomeSource] = Field(min_length=1, max_length=20)
    supersedes_observation_id: str | None = Field(default=None, pattern=r"^[0-9a-fA-F-]{36}$")
    recorded_at: date

    @model_validator(mode="after")
    def validate_temporal_semantics(self):
        if self.event_date and self.event_date > self.observed_at:
            raise ValueError("event_date cannot be after observed_at")
        terminal = {"confirmed_closure", "acquired", "ipo", "merged", "bankruptcy_insolvency"}
        if self.status in terminal and self.event_date is None:
            raise ValueError("terminal outcome observations require a verified event_date")
        if self.status in terminal and not any(source.verification_state == "verified" for source in self.sources):
            raise ValueError("terminal outcome labels require at least one verified source")
        if self.status not in terminal and self.event_date is not None:
            raise ValueError("non-terminal status observations cannot carry an outcome event_date")
        if self.status == "right_censored":
            if self.follow_up_due is None or self.follow_up_due <= self.observed_at:
                raise ValueError("right-censored records require a follow_up_due after observed_at")
        elif self.follow_up_due is not None:
            raise ValueError("follow_up_due is only valid for right-censored observations")
        if self.recorded_at < self.observed_at:
            raise ValueError("recorded_at cannot be before observed_at")
        return self
