"""Versioned contract and validation for claim-to-source evidence associations.

This module is deliberately independent of retrieval, scoring, diagnostics,
storage, and API code. Retrieval relevance is never treated as claim support.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


EVIDENCE_ASSOCIATION_VERSION = "1.0"

ClaimCategory = Literal[
    "historical_case_fact",
    "general_research_finding",
    "startup_specific_interpretation",
    "recommendation",
]
EvidenceRelationship = Literal[
    "supports", "partially_supports", "contextualizes", "contradicts", "insufficient",
]
VerificationState = Literal["pending_review", "verified", "rejected", "not_assessed"]
SourceAccess = Literal["abstract_excerpt", "full_text_passage", "metadata_only", "inaccessible"]
VerificationMethod = Literal["human_review", "ai_assisted", "system_validation", "none"]
ContradictionNature = Literal[
    "genuine_disagreement", "different_population", "different_geography",
    "different_period", "different_definition", "different_methodology",
    "complementary", "insufficient_information",
]

PASSAGE_RELATIONSHIPS = {"supports", "partially_supports", "contradicts"}


class SourcePublicationMetadata(BaseModel):
    """Snapshot of bibliographic fields; these fields do not verify a source."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=2000)
    url: str = Field(min_length=1, max_length=4000)
    publisher: str | None = Field(default=None, max_length=1000)
    journal: str | None = Field(default=None, max_length=1000)
    authors: list[str] = Field(default_factory=list, max_length=100)
    doi: str | None = Field(default=None, max_length=500)
    published: str | None = Field(default=None, max_length=100)
    year: str | None = Field(default=None, max_length=20)


class EvidenceAssociation(BaseModel):
    """Proposed or reviewed link between a report claim and a snapshot source."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1.0"] = EVIDENCE_ASSOCIATION_VERSION
    record_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    analysis_id: uuid.UUID
    snapshot_id: uuid.UUID
    claim_text: str = Field(min_length=1, max_length=10000)
    claim_category: ClaimCategory
    source_id: str = Field(min_length=1, max_length=2000)
    source_access: SourceAccess
    exact_passage_text: str | None = Field(default=None, max_length=20000)
    passage_location: str | None = Field(default=None, max_length=2000)
    source_url: str = Field(min_length=1, max_length=4000)
    publication: SourcePublicationMetadata
    relationship: EvidenceRelationship
    verification_state: VerificationState = "not_assessed"
    verification_method: VerificationMethod = "none"
    reviewer_id: str | None = Field(default=None, max_length=200)
    supersedes_record_id: uuid.UUID | None = None
    limitations: list[str] = Field(default_factory=list, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retrieved_at: datetime | None = None
    reviewed_at: datetime | None = None
    verified_at: datetime | None = None

    @model_validator(mode="after")
    def validate_assessment(self) -> "EvidenceAssociation":
        passage_required = self.relationship in PASSAGE_RELATIONSHIPS

        if self.source_access in {"metadata_only", "inaccessible"} and self.exact_passage_text:
            raise ValueError("metadata-only or inaccessible sources cannot include a passage")
        if passage_required and not self.exact_passage_text:
            raise ValueError("this relationship requires an inspected source passage")
        if self.source_access == "full_text_passage" and (not self.exact_passage_text or not self.passage_location):
            raise ValueError("full-text passages require inspected text and a known location")
        if self.verification_state == "verified":
            if self.verification_method != "human_review" or not self.reviewer_id or not self.verified_at:
                raise ValueError("verified associations require human review, reviewer identity, and verification time")
            if passage_required and self.source_access not in {"abstract_excerpt", "full_text_passage"}:
                raise ValueError("metadata-only or inaccessible sources cannot verify passage support")
        if self.verification_state == "rejected" and (
            self.verification_method != "human_review" or not self.reviewer_id or not self.reviewed_at
        ):
            raise ValueError("rejected associations require human review, reviewer identity, and review time")
        if self.verification_method == "ai_assisted" and self.verification_state in {"verified", "rejected"}:
            raise ValueError("AI-assisted assessments must remain pending human review")
        if self.supersedes_record_id == self.record_id:
            raise ValueError("a correction cannot supersede itself")
        return self


class EvidenceAssociationSubmission(BaseModel):
    """Founder-submitted proposal; trusted IDs and review state are server-owned."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: uuid.UUID
    claim_text: str = Field(min_length=1, max_length=10000)
    claim_category: ClaimCategory
    source_id: str = Field(min_length=1, max_length=2000)
    source_access: SourceAccess
    exact_passage_text: str | None = Field(default=None, max_length=20000)
    passage_location: str | None = Field(default=None, max_length=2000)
    source_url: str = Field(min_length=1, max_length=4000)
    publication: SourcePublicationMetadata
    relationship: EvidenceRelationship
    limitations: list[str] = Field(default_factory=list, max_length=100)


class EvidenceReviewRequest(BaseModel):
    """Human review decision; reviewer identity is always taken from auth."""

    model_config = ConfigDict(extra="forbid")

    relationship: EvidenceRelationship
    verification_state: Literal["verified", "rejected"]
    limitations: list[str] = Field(default_factory=list, max_length=100)


class ContradictionEvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    association_id: uuid.UUID
    snapshot_id: uuid.UUID
    source_id: str = Field(min_length=1, max_length=2000)
    claim_text: str = Field(min_length=1, max_length=10000)
    exact_passage_text: str = Field(min_length=1, max_length=20000)
    passage_location: str | None = Field(default=None, max_length=2000)
    source_access: Literal["abstract_excerpt", "full_text_passage"]
    source_url: str = Field(min_length=1, max_length=4000)
    publication: SourcePublicationMetadata


class ContradictionAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1.0"] = EVIDENCE_ASSOCIATION_VERSION
    record_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    analysis_id: uuid.UUID
    association_ids: list[uuid.UUID] = Field(min_length=2, max_length=2)
    compared_evidence: list[ContradictionEvidenceReference] = Field(min_length=2, max_length=2)
    nature: ContradictionNature
    assessment_text: str = Field(min_length=1, max_length=5000)
    relationship: EvidenceRelationship | None = None
    context_differences: list[str] = Field(default_factory=list, max_length=20)
    methodological_differences: list[str] = Field(default_factory=list, max_length=20)
    measurement_differences: list[str] = Field(default_factory=list, max_length=20)
    population_differences: list[str] = Field(default_factory=list, max_length=20)
    geographic_differences: list[str] = Field(default_factory=list, max_length=20)
    time_period_differences: list[str] = Field(default_factory=list, max_length=20)
    uncertainty_explanation: str = Field(default="", max_length=2000)
    source_access_limitations: list[str] = Field(default_factory=list, max_length=20)
    detection_method: Literal["deterministic_excerpt_rules", "manual_review"] = "manual_review"
    reviewer_explanation: str | None = Field(default=None, max_length=5000)
    verification_state: Literal["pending_review", "verified", "rejected", "not_assessed"] = "pending_review"
    verification_method: VerificationMethod = "none"
    reviewer_id: str | None = Field(default=None, max_length=200)
    limitations: list[str] = Field(default_factory=list, max_length=100)
    supersedes_record_id: uuid.UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_review(self) -> "ContradictionAssessment":
        if self.association_ids[0] == self.association_ids[1]:
            raise ValueError("a contradiction assessment requires two different associations")
        if {item.association_id for item in self.compared_evidence} != set(self.association_ids):
            raise ValueError("compared passages must correspond to the referenced associations")
        if self.verification_state in {"verified", "rejected"} and (
            self.verification_method != "human_review" or not self.reviewer_id or not self.reviewed_at
        ):
            raise ValueError("reviewed contradiction assessments require human reviewer provenance")
        if self.detection_method == "deterministic_excerpt_rules" and self.verification_state != "pending_review":
            if self.verification_method != "human_review":
                raise ValueError("automatically classified comparisons require human review before verification")
        if self.verification_method == "ai_assisted" and self.verification_state in {"verified", "rejected"}:
            raise ValueError("AI contradiction candidates must remain pending human review")
        if self.supersedes_record_id == self.record_id:
            raise ValueError("a correction cannot supersede itself")
        return self


class ContradictionSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    association_ids: list[uuid.UUID] = Field(min_length=2, max_length=2)
    nature: ContradictionNature
    assessment_text: str = Field(min_length=1, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=100)


class ContradictionCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    association_ids: list[uuid.UUID] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def distinct_associations(self) -> "ContradictionCompareRequest":
        if self.association_ids[0] == self.association_ids[1]:
            raise ValueError("a comparison requires two different evidence associations")
        return self


class ContradictionDetectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: uuid.UUID
    offset: int = Field(default=0, ge=0, le=100000)


class ContradictionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification_state: Literal["verified", "rejected"]
    nature: ContradictionNature
    relationship: EvidenceRelationship | None = None
    assessment_text: str = Field(min_length=1, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=100)
    reviewer_explanation: str | None = Field(default=None, max_length=5000)


class EvidenceAssociationValidationError(ValueError):
    """Raised when an association cannot be proven to reference its snapshot."""


def _source_identifiers(source: dict[str, Any]) -> set[str]:
    return {
        value.strip().casefold()
        for key in ("openalex_id", "doi", "url")
        if isinstance((value := source.get(key)), str) and value.strip()
    }


def _publication(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": source.get("title", ""),
        "url": source.get("url", ""),
        "publisher": source.get("publisher"),
        "journal": source.get("journal"),
        "authors": source.get("authors") or [],
        "doi": source.get("doi"),
        "published": source.get("published"),
        "year": source.get("year"),
    }


def find_snapshot_source(snapshot: dict[str, Any], source_id: str) -> dict[str, Any] | None:
    payload = snapshot.get("payload") if isinstance(snapshot, dict) else None
    sources = payload.get("sources") if isinstance(payload, dict) else None
    if not isinstance(sources, list):
        return None
    return next((item for item in sources if isinstance(item, dict)
                 and source_id.casefold() in _source_identifiers(item)), None)


def validate_evidence_association(
    association: EvidenceAssociation,
    snapshot: dict[str, Any],
) -> EvidenceAssociation:
    """Validate IDs, source metadata, access state, and exact text against a snapshot.

    This establishes identity and quotation integrity only. It does not assess
    whether a passage semantically supports or contradicts the claim.
    """
    try:
        snapshot_id = uuid.UUID(str(snapshot.get("id")))
        analysis_id = uuid.UUID(str(snapshot.get("analysis_id")))
    except (AttributeError, TypeError, ValueError) as error:
        raise EvidenceAssociationValidationError("snapshot identity is invalid") from error

    if snapshot_id != association.snapshot_id:
        raise EvidenceAssociationValidationError("association snapshot_id does not match the supplied snapshot")
    if analysis_id != association.analysis_id:
        raise EvidenceAssociationValidationError("snapshot does not belong to the referenced analysis")

    source = find_snapshot_source(snapshot, association.source_id)
    if source is None:
        raise EvidenceAssociationValidationError("source_id does not exist in the referenced snapshot")

    if association.source_url != source.get("url"):
        raise EvidenceAssociationValidationError("source_url does not match the saved source")
    try:
        expected_publication = SourcePublicationMetadata.model_validate(_publication(source))
    except Exception as error:
        raise EvidenceAssociationValidationError("saved source publication metadata is invalid") from error
    if association.publication != expected_publication:
        raise EvidenceAssociationValidationError("publication metadata does not match the saved source")
    if association.retrieved_at and source.get("retrieved_at"):
        if association.retrieved_at.date().isoformat() != source["retrieved_at"]:
            raise EvidenceAssociationValidationError("retrieved_at does not match the saved source")

    saved_access = source.get("access_status")
    if association.source_access == "abstract_excerpt":
        if saved_access != "abstract_only":
            raise EvidenceAssociationValidationError("snapshot source is not marked abstract_only")
        if association.exact_passage_text != source.get("excerpt"):
            raise EvidenceAssociationValidationError("abstract passage must exactly match the saved excerpt")
    elif association.source_access == "metadata_only":
        if saved_access != "metadata_only":
            raise EvidenceAssociationValidationError("snapshot source is not metadata_only")
    elif association.source_access == "inaccessible":
        if saved_access not in {"metadata_only", "inaccessible"}:
            raise EvidenceAssociationValidationError("snapshot does not establish inaccessible source status")
    elif association.source_access == "full_text_passage":
        # Current snapshots do not contain inspected full-text passages/locators.
        # An OA URL or abstract excerpt is not sufficient to assert full text.
        passages = source.get("full_text_passages")
        match = next((item for item in passages if isinstance(item, dict)
                      and item.get("text") == association.exact_passage_text
                      and item.get("location") == association.passage_location), None) if isinstance(passages, list) else None
        if saved_access != "full_text_reviewed" or match is None:
            raise EvidenceAssociationValidationError("snapshot has no inspected full-text passage with this location")

    return association
