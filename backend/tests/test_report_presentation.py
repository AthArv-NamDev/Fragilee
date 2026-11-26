"""Source-level regression checks for the founder-facing report contract.

This repository has no frontend component test runner yet. These checks guard
the most important presentation boundary without requiring an external service.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = (ROOT / "components/AnalysisView.tsx").read_text()
TREE_VIEW = (ROOT / "components/tree/PlexTree.tsx").read_text()
TREE_MODEL = (ROOT / "lib/tree.ts").read_text()
CASES = (ROOT / "components/CasesPanel.tsx").read_text()


def test_report_does_not_render_probability_band_or_failure_share():
    for forbidden in ("result.probability", "result.band", "similar_startups_failure_rate"):
        assert forbidden not in ANALYSIS
    assert "No individual failure probability, risk band, or overall risk score is presented here." in ANALYSIS


def test_historical_model_context_explains_terminal_outcomes_and_no_horizon():
    assert "companies with recorded final outcomes" in ANALYSIS
    assert "do not establish a consistent prediction time horizon" in ANALYSIS
    assert "No individual failure probability" in ANALYSIS


def test_model_trace_is_secondary_and_explicitly_non_causal():
    tree = ANALYSIS.index("<PlexTree result={result}")
    research = ANALYSIS.index("<section id=\"evidence-examples\"")
    founder_toggle = ANALYSIS.index("Founder-submitted information, structured profile &amp; historical model context")
    assert tree < research < founder_toggle
    assert 'label: "Historical model attribution"' in TREE_MODEL
    assert "not percentage points, a failure probability, or a measurement of business health" in TREE_MODEL
    assert "not a startup-specific diagnosis, cause, or forecast" in TREE_MODEL


def test_founder_context_and_not_provided_fields_are_explicit():
    assert "Founder-submitted information" in ANALYSIS
    assert "Not provided" in ANALYSIS
    assert "not a risk signal" in ANALYSIS
    assert "have not been independently verified" in ANALYSIS


def test_research_cases_and_model_are_separate_sections():
    assert "External research · separate from model and cases" in CASES
    assert "Historical company cases" in CASES
    assert "Historical model context" in ANALYSIS
    assert "TreeSHAP context · not a diagnosis" in TREE_VIEW
    assert "do not predict this startup&apos;s outcome" in CASES
    assert "apiFetch" not in TREE_VIEW


def test_empty_research_and_case_results_have_independent_fallbacks():
    assert "researchState === \"unavailable\"" in CASES
    assert "No source records were returned" in CASES
    assert "Case examples are unavailable." in CASES
    assert "data.cases.length === 0" in CASES


def test_phase3_research_provenance_and_empty_states_remain_explicit():
    assert "retrieval status and coverage" in CASES.lower()
    assert "researchStateLabel(research.state)" in CASES
    results = (ROOT / "components/EvidenceResults.tsx").read_text()
    assert "Abstract excerpt (source text)" in results
    assert "metadata_status" in results
    assert "open_access_url" in results
    helper = (ROOT / "lib/research-presentation.mjs").read_text()
    for state in ("partial", "no_results", "filtered_out", "weak_relevance", "provider_unavailable", "provider_error"):
        assert state in helper


def test_historical_matches_explain_basis_outcome_differences_and_library_limits():
    assert "Why this case was selected" in CASES
    assert "Differences and comparison limits" in CASES
    assert "Recorded outcome" in CASES
    assert "failure examples and no matched survivor set" in CASES
    assert "not representative" in CASES


def test_optional_and_legacy_tree_data_are_tolerated():
    assert "?.tree?.children" in TREE_MODEL
    assert "Array.isArray(b.factors) ? b.factors : []" in TREE_MODEL
    assert "displayBranchLabel" in TREE_MODEL
    assert "market[\\s_-]?industry" in TREE_MODEL
    assert "This older saved report does not contain a per-input attribution." in TREE_MODEL
    assert "no compatible historical model trace" in TREE_MODEL


def test_tree_keyboard_controls_remain_available():
    assert "tabIndex={0} role=\"button\"" in TREE_VIEW
    assert "e.key === \"Enter\" || e.key === \" \"" in TREE_VIEW
    assert "e.key === \"Home\"" in TREE_VIEW


def test_profile_presentation_has_safe_legacy_and_markup_fallbacks():
    assert "const context = analysis.context ?? {};" in ANALYSIS
    assert "!hasContext && !displayProfile" in ANALYSIS
    assert "displayProfile && <ProfileSection" in ANALYSIS
    assert "dtclassName" not in ANALYSIS
    assert "md:pt-10xl:px-12" not in ANALYSIS
    assert '<dt className="py-2 text-muted">' in ANALYSIS


def test_legacy_revenue_note_is_labeled_separately_from_monthly_revenue():
    assert '"revenue_model", "Revenue model (founder note)"' in ANALYSIS
    assert 'revenue_amount: "Monthly revenue"' in ANALYSIS
