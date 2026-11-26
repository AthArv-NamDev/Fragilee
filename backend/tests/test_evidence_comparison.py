from datetime import datetime, timezone
import uuid

import pytest

from app.evidence_contract import EvidenceAssociation
from app.evidence_comparison import compare_saved_passages


def association(passage, *, claim="Customer retention and revenue growth", source="https://openalex.org/W1", access="abstract_excerpt", title="Study", year="2024", relationship="contextualizes"):
    return EvidenceAssociation(
        analysis_id=uuid.uuid4(), snapshot_id=uuid.uuid4(), claim_text=claim,
        claim_category="general_research_finding", source_id=source, source_access=access,
        exact_passage_text=passage, passage_location="Abstract" if passage else None,
        source_url=f"https://example.org/{source.rsplit('/', 1)[-1]}",
        publication={"title": title, "url": f"https://example.org/{source.rsplit('/', 1)[-1]}", "year": year},
        relationship=relationship, verification_state="pending_review",
        verification_method="none", created_at=datetime.now(timezone.utc),
    )


def compare(a, b):
    return compare_saved_passages(a, b)


def test_explicit_opposite_directions_are_only_a_pending_potential_contradiction():
    positive = association("Customer retention has a positive relationship with revenue growth among fashion sellers.")
    negative = association("Customer retention has a negative relationship with revenue growth among fashion sellers.", source="https://openalex.org/W2")
    for first, second in ((positive, negative), (negative, positive)):
        result = compare(first, second)
        assert result["relationship"] == "contradicts"
        assert result["nature"] == "genuine_disagreement"
        assert "potential contradiction" in result["assessment_text"].lower()
        assert "effect size" in result["uncertainty_explanation"]
        assert any("abstract excerpt" in text for text in result["source_access_limitations"])


def test_directional_and_null_findings_are_partial_disagreement_not_opposite_truth():
    result = compare(
        association("Customer retention has a positive relationship with revenue growth among fashion sellers."),
        association("No significant relationship was observed between customer retention and revenue growth among fashion sellers.", source="https://openalex.org/W2"),
    )
    assert result["relationship"] == "partially_supports"
    assert "non-significant" in result["assessment_text"]


@pytest.mark.parametrize(("a", "b", "nature", "field"), [
    ("Customer retention has a positive relationship with revenue growth among Indian fashion sellers.", "Customer retention has a negative relationship with revenue growth among U.S. fashion sellers.", "different_geography", "geographic_differences"),
    ("Customer retention has a positive relationship with revenue growth among adults.", "Customer retention has a negative relationship with revenue growth among students.", "different_population", "population_differences"),
    ("A survey found a positive relationship between customer retention and revenue growth.", "An experiment found a negative relationship between customer retention and revenue growth.", "different_methodology", "methodological_differences"),
    ("Customer retention has a positive relationship with repeat purchase.", "Customer retention has a negative relationship with revenue growth.", "different_definition", "measurement_differences"),
    ("From 2018 to 2020, customer retention had a positive relationship with revenue growth.", "From 2022 to 2024, customer retention had a negative relationship with revenue growth.", "different_period", "time_period_differences"),
])
def test_context_differences_explain_opposite_directions(a, b, nature, field):
    result = compare(association(a), association(b, source="https://openalex.org/W2"))
    assert result["relationship"] == "contextualizes"
    assert result["nature"] == nature
    assert result[field]


def test_same_direction_with_different_wording_is_possible_support_not_consensus():
    result = compare(
        association("Customer retention has a positive relationship with revenue growth among fashion sellers."),
        association("Customer retention is positively associated with revenue growth among fashion sellers.", source="https://openalex.org/W2"),
    )
    assert result["relationship"] == "supports"
    assert result["nature"] == "complementary"
    assert "not consensus" in result["assessment_text"]


def test_unrelated_or_non_directional_passages_are_insufficient():
    result = compare(
        association("This paper describes a sample of retail companies."),
        association("The abstract reports a discussion of market practices.", source="https://openalex.org/W2"),
    )
    assert result["relationship"] == "insufficient"
    assert result["nature"] == "insufficient_information"


def test_metadata_only_and_missing_passages_never_receive_support_classification():
    metadata = association(None, access="metadata_only")
    full = association("Customer retention has a positive relationship with revenue growth among fashion sellers.", source="https://openalex.org/W2")
    assert compare(metadata, full)["relationship"] == "insufficient"
    with pytest.raises(ValueError, match="requires an inspected source passage"):
        association(None, access="abstract_excerpt", relationship="supports")


def test_titles_and_publication_years_are_not_used_to_infer_findings_or_study_period():
    result = compare(
        association("Customer behavior is discussed.", title="Positive retention increases growth, 2010", year="2020"),
        association("Retail operations are discussed.", source="https://openalex.org/W2", title="Negative retention lowers growth, 2025", year="2025"),
    )
    assert result["relationship"] == "insufficient"
    assert result["time_period_differences"] == []


def test_same_source_is_not_counted_as_two_independent_findings():
    result = compare(
        association("Customer retention has a positive relationship with revenue growth among fashion sellers."),
        association("Customer retention has a negative relationship with revenue growth among fashion sellers."),
    )
    assert result["relationship"] == "insufficient"
    assert "same identified source" in result["assessment_text"]
