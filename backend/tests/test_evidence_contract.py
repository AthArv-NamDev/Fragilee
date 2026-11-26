import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.evidence_contract import (
    EvidenceAssociation,
    EvidenceAssociationValidationError,
    SourcePublicationMetadata,
    validate_evidence_association,
)


ANALYSIS_ID = uuid.uuid4()
SNAPSHOT_ID = uuid.uuid4()
SOURCE = {
    "title": "Startup market research",
    "publisher": "Example Journal",
    "journal": "Example Journal",
    "authors": ["A. Researcher"],
    "doi": "https://doi.org/10.1234/example",
    "openalex_id": "https://openalex.org/W123",
    "url": "https://example.org/article",
    "published": "2026-03-10",
    "year": "2026",
    "access_status": "abstract_only",
    "excerpt": "Customer retention varies across early-stage firms.",
    "retrieved_at": "2026-11-16",
}


def snapshot(source=None, analysis_id=ANALYSIS_ID, snapshot_id=SNAPSHOT_ID):
    return {
        "id": str(snapshot_id),
        "analysis_id": str(analysis_id),
        "payload": {"sources": [source or SOURCE]},
    }


def association(**overrides):
    values = {
        "analysis_id": ANALYSIS_ID,
        "snapshot_id": SNAPSHOT_ID,
        "claim_text": "Customer retention varies across early-stage firms.",
        "claim_category": "general_research_finding",
        "source_id": SOURCE["openalex_id"],
        "source_access": "abstract_excerpt",
        "exact_passage_text": SOURCE["excerpt"],
        "source_url": SOURCE["url"],
        "publication": SourcePublicationMetadata.model_validate({
            key: SOURCE.get(key)
            for key in ("title", "url", "publisher", "journal", "authors", "doi", "published", "year")
        }),
        "relationship": "supports",
        "verification_state": "pending_review",
        "verification_method": "ai_assisted",
        "retrieved_at": datetime(2026, 11, 16, tzinfo=timezone.utc),
        "limitations": ["Abstract excerpt only; startup-specific applicability was not assessed."],
    }
    values.update(overrides)
    return EvidenceAssociation.model_validate(values)


def test_valid_association_matches_snapshot_and_exact_abstract_excerpt():
    item = association()
    assert validate_evidence_association(item, snapshot()) is item
    assert item.contract_version == "1.0"
    assert item.record_id


def test_abstract_passage_must_match_snapshot_exactly():
    item = association(exact_passage_text="Customer retention may vary across firms.")
    with pytest.raises(EvidenceAssociationValidationError, match="exactly match"):
        validate_evidence_association(item, snapshot())


def test_unknown_source_identifier_is_rejected():
    item = association(source_id="https://openalex.org/W-does-not-exist")
    with pytest.raises(EvidenceAssociationValidationError, match="does not exist"):
        validate_evidence_association(item, snapshot())


def test_snapshot_must_belong_to_same_analysis():
    item = association()
    with pytest.raises(EvidenceAssociationValidationError, match="does not belong"):
        validate_evidence_association(item, snapshot(analysis_id=uuid.uuid4()))


def test_association_snapshot_id_must_match_row():
    item = association(snapshot_id=uuid.uuid4())
    with pytest.raises(EvidenceAssociationValidationError, match="does not match"):
        validate_evidence_association(item, snapshot())


def test_pending_review_is_valid_and_ai_never_marks_verified():
    pending = association(verification_state="pending_review", verification_method="ai_assisted")
    assert pending.verification_state == "pending_review"
    with pytest.raises(ValidationError, match="human review"):
        association(
            verification_state="verified", verification_method="ai_assisted",
            reviewer_id="reviewer-1", verified_at=datetime.now(timezone.utc),
        )


def test_correction_is_a_new_record_that_references_the_prior_record():
    prior = association()
    correction = association(supersedes_record_id=prior.record_id)
    assert correction.record_id != prior.record_id
    assert correction.supersedes_record_id == prior.record_id
    with pytest.raises(ValidationError, match="cannot supersede itself"):
        association(supersedes_record_id=uuid.UUID(int=0), record_id=uuid.UUID(int=0))


def test_metadata_only_source_cannot_be_verified_as_passage_support():
    metadata_source = {**SOURCE, "access_status": "metadata_only", "excerpt": ""}
    with pytest.raises(ValidationError, match="requires an inspected source passage"):
        item = association(
            source_access="metadata_only", exact_passage_text=None,
            relationship="supports", verification_state="verified",
            verification_method="human_review", reviewer_id="reviewer-1",
            verified_at=datetime.now(timezone.utc),
        )
        validate_evidence_association(item, snapshot(metadata_source))


def test_metadata_only_insufficient_assessment_is_allowed_without_invented_passage():
    metadata_source = {**SOURCE, "access_status": "metadata_only", "excerpt": ""}
    item = association(
        source_access="metadata_only", exact_passage_text=None,
        relationship="insufficient", verification_state="not_assessed",
        verification_method="none", retrieved_at=None,
    )
    assert validate_evidence_association(item, snapshot(metadata_source)).exact_passage_text is None


def test_insufficient_relationship_does_not_assert_support():
    item = association(
        relationship="insufficient", source_access="metadata_only",
        exact_passage_text=None, verification_state="not_assessed",
        verification_method="none", retrieved_at=None,
    )
    assert item.relationship == "insufficient"
    assert item.verification_state == "not_assessed"


def test_contradictory_relation_requires_exact_inspected_passage():
    item = association(
        relationship="contradicts", verification_state="pending_review",
        verification_method="ai_assisted",
    )
    assert validate_evidence_association(item, snapshot()).relationship == "contradicts"
    with pytest.raises(ValidationError, match="requires an inspected source passage"):
        association(relationship="contradicts", exact_passage_text=None)


def test_verified_relationship_requires_human_review_metadata():
    with pytest.raises(ValidationError, match="human review"):
        association(verification_state="verified", verification_method="system_validation")


def test_full_text_requires_a_snapshot_passage_and_known_location():
    with pytest.raises(ValidationError, match="known location"):
        association(source_access="full_text_passage", passage_location=None)
    full_text_source = {
        **SOURCE,
        "access_status": "full_text_reviewed",
        "full_text_passages": [{"text": "Inspected full text passage.", "location": "Section 2, paragraph 3"}],
    }
    item = association(
        source_access="full_text_passage", exact_passage_text="Inspected full text passage.",
        passage_location="Section 2, paragraph 3",
    )
    assert validate_evidence_association(item, snapshot(full_text_source)).source_access == "full_text_passage"


def test_retrieval_relevance_cannot_replace_source_claim_or_verification():
    item = association(relationship="insufficient", verification_state="not_assessed", verification_method="none")
    assert validate_evidence_association(item, snapshot()).verification_state == "not_assessed"
