"""Conservative, deterministic comparison of saved source excerpts.

This is a candidate generator, not a scientific claim verifier. It uses only
the exact saved passage and linked claim text; bibliographic metadata is used
only for provenance and publication-year comparison.
"""
from __future__ import annotations

import re
from .evidence_contract import EvidenceAssociation

DETECTION_METHOD = "deterministic_excerpt_rules"
_STOP = set("""
a an and are as at be been being by can could did do does for from had has have he her hers him his in into is it its
may might of on or our she should that the their them they this those through to was we were what when where which
who will with would you your study studies paper research evidence result results findings found report reports
""".split())
_POSITIVE = re.compile(r"\b(positive association|positive relationship|positively associated|positively related|increases? (?:with|as|when)|improves? (?:with|as|when)|higher (?:rates? of )?|greater (?:rates? of )?|significant positive)\b", re.I)
_NEGATIVE = re.compile(r"\b(negative association|negative relationship|negatively associated|negatively related|decreases? (?:with|as|when)|reduces? (?:with|as|when)|lower (?:rates? of )?|significant negative|inverse relationship)\b", re.I)
_NULL = re.compile(r"\b(no (?:significant|meaningful|clear|detectable)?\s*(?:association|relationship|effect|impact|difference)|not (?:significantly )?(?:associated|related)|no statistically significant|not statistically significant|null (?:effect|result)|did not (?:increase|improve|reduce|affect))\b", re.I)
_METHODS = ("randomized", "randomised", "survey", "interview", "experiment", "longitudinal", "cross-sectional", "qualitative", "quantitative", "panel data", "case study", "meta-analysis", "systematic review")
_POPULATIONS = ("founders", "entrepreneurs", "consumers", "customers", "students", "adults", "adolescents", "women", "men", "employees", "small businesses", "startups", "start-ups", "retailers", "fashion buyers")
_GEOGRAPHIES = ("india", "indian", "united states", "u.s.", "usa", "american", "united kingdom", "uk", "british", "canada", "canadian", "australia", "europe", "china", "japan", "brazil", "africa", "asia")
_MEASURES = ("customer retention", "retention rate", "repeat purchase", "revenue growth", "sales growth", "profit margin", "customer acquisition cost", "conversion rate", "market share", "churn rate", "customer lifetime value", "lifetime value")
_YEARS = re.compile(r"\b(?:19|20)\d{2}(?:\s*(?:-|–|to)\s*(?:19|20)?\d{2})?\b")


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-z][a-z0-9-]{2,}", text.casefold()) if term not in _STOP}


def _matches(text: str, candidates: tuple[str, ...]) -> set[str]:
    folded = text.casefold()
    return {item for item in candidates if re.search(r"(?<!\w)" + re.escape(item) + r"(?!\w)", folded)}


def _context(left: str, right: str, candidates: tuple[str, ...]) -> list[str]:
    a, b = _matches(left, candidates), _matches(right, candidates)
    return [f"Source A mentions {', '.join(sorted(a))}; Source B mentions {', '.join(sorted(b))}."] if a and b and a.isdisjoint(b) else []


def _periods(text: str) -> set[str]:
    return {re.sub(r"\s+", "", value.casefold()).replace("–", "-").replace("to", "-") for value in _YEARS.findall(text)}


def _period_difference(left: str, right: str) -> list[str]:
    a, b = _periods(left), _periods(right)
    return [f"Source A passage states {', '.join(sorted(a))}; Source B passage states {', '.join(sorted(b))}."] if a and b and a.isdisjoint(b) else []


def _measure_difference(left: str, right: str) -> list[str]:
    a, b = _matches(left, _MEASURES), _matches(right, _MEASURES)
    only_a, only_b = a - b, b - a
    return [f"Source A passage mentions {', '.join(sorted(only_a))}; Source B passage mentions {', '.join(sorted(only_b))}."] if only_a and only_b else []


def _polarity(text: str) -> str:
    if _NULL.search(text):
        return "null"
    positive, negative = bool(_POSITIVE.search(text)), bool(_NEGATIVE.search(text))
    if positive == negative:
        return "mixed" if positive else "unknown"
    return "positive" if positive else "negative"


def compare_saved_passages(left: EvidenceAssociation, right: EvidenceAssociation) -> dict:
    """Return an explainable pending classification using only saved passages.

    Lexical overlap and polarity patterns are intentionally conservative. No
    model score, retrieval rank, title, or keyword metadata determines support.
    """
    a, b = (left, right)
    passage_a, passage_b = a.exact_passage_text or "", b.exact_passage_text or ""
    source_access_limitations = sorted({
        f"Source A is available as {a.source_access.replace('_', ' ')}." if a.source_access == "abstract_excerpt" else "",
        f"Source B is available as {b.source_access.replace('_', ' ')}." if b.source_access == "abstract_excerpt" else "",
    } - {""})
    method_diffs = _context(passage_a, passage_b, _METHODS)
    population_diffs = _context(passage_a, passage_b, _POPULATIONS)
    geography_diffs = _context(passage_a, passage_b, _GEOGRAPHIES)
    period_diffs = _period_difference(passage_a, passage_b)
    measure_diffs = _measure_difference(passage_a, passage_b)
    context_differences = [*method_diffs, *population_diffs, *geography_diffs, *period_diffs, *measure_diffs]

    if not passage_a.strip() or not passage_b.strip() or a.source_access in {"metadata_only", "inaccessible"} or b.source_access in {"metadata_only", "inaccessible"}:
        relationship, nature = "insufficient", "insufficient_information"
        explanation = "At least one saved association lacks an accessible inspected passage, so the source findings cannot be compared."
        uncertainty = "No comparison is inferred from titles, retrieval relevance, or metadata alone."
    else:
        shared = (_terms(passage_a) & _terms(passage_b)) | (_terms(a.claim_text) & _terms(b.claim_text))
        shared_claim_terms = _terms(a.claim_text) & _terms(b.claim_text)
        polarity_a, polarity_b = _polarity(passage_a), _polarity(passage_b)
        enough_topic_overlap = len(shared_claim_terms) >= 2 or len(shared) >= 4
        same_source = a.source_id.casefold() == b.source_id.casefold() or bool(
            a.publication.doi and b.publication.doi and a.publication.doi.casefold() == b.publication.doi.casefold()
        )
        if same_source:
            relationship, nature = "insufficient", "insufficient_information"
            explanation = "Both passages refer to the same identified source, so they are not treated as independent research findings."
            uncertainty = "This rule does not determine whether separate parts of one source are internally inconsistent."
        elif not enough_topic_overlap or polarity_a == "unknown" or polarity_b == "unknown" or "mixed" in {polarity_a, polarity_b}:
            relationship, nature = "insufficient", "insufficient_information"
            explanation = "The saved excerpts do not express comparable directional findings on a sufficiently shared topic."
            uncertainty = "The rule-based excerpt check cannot resolve this pair; human assessment is required."
        elif context_differences and {polarity_a, polarity_b} == {"positive", "negative"}:
            relationship = "contextualizes"
            if geography_diffs:
                nature = "different_geography"
            elif population_diffs:
                nature = "different_population"
            elif period_diffs:
                nature = "different_period"
            elif method_diffs:
                nature = "different_methodology"
            elif measure_diffs:
                nature = "different_definition"
            else:
                nature = "genuine_disagreement"
            explanation = "The excerpts appear to report different directions, while also stating different study contexts. This may explain the difference; it is not treated as a universal contradiction."
            uncertainty = "The excerpt rules do not establish whether context explains the difference or whether the findings truly conflict."
        elif {polarity_a, polarity_b} == {"positive", "negative"}:
            relationship, nature = "contradicts", "genuine_disagreement"
            explanation = "The excerpts contain shared topic language but opposing explicit directional phrases. This is a potential contradiction for human review, not a scientific conclusion."
            uncertainty = "The rule detects phrase-level direction only; it does not assess effect size, statistical validity, study design, or causal strength."
        elif "null" in {polarity_a, polarity_b} and polarity_a != polarity_b:
            relationship = "partially_supports"
            nature = (
                "different_geography" if geography_diffs else
                "different_population" if population_diffs else
                "different_period" if period_diffs else
                "different_methodology" if method_diffs else
                "different_definition" if measure_diffs else
                "genuine_disagreement"
            )
            explanation = "One excerpt contains a directional finding and the other explicitly reports a null or non-significant result. Treat this as partial disagreement pending review."
            if context_differences:
                explanation += " The excerpts also state different contexts, which may help explain the difference."
            uncertainty = "A null or non-significant result does not prove the opposite effect; sample size and methods are not assessed by these rules."
        elif polarity_a == polarity_b:
            relationship, nature = "supports", "complementary"
            explanation = "Both excerpts contain the same explicit directional phrase category on overlapping topic language. This indicates possible agreement, not consensus."
            uncertainty = "The comparison does not assess whether measures or methods are equivalent."
        else:
            relationship, nature = "insufficient", "insufficient_information"
            explanation = "The saved passages do not fit a supported comparison rule."
            uncertainty = "Human assessment is required."

    limitations = [
        "This is a deterministic phrase-level candidate, not a scientific truth assessment.",
        "Do not infer causation, effect size, significance, or consensus from this comparison.",
        "Context is reported only when explicitly stated in the saved passage; missing context remains unknown.",
        *source_access_limitations,
    ]
    return {
        "relationship": relationship,
        "nature": nature,
        "assessment_text": explanation,
        "context_differences": context_differences,
        "methodological_differences": method_diffs,
        "measurement_differences": measure_diffs,
        "population_differences": population_diffs,
        "geographic_differences": geography_diffs,
        "time_period_differences": period_diffs,
        "uncertainty_explanation": uncertainty,
        "source_access_limitations": source_access_limitations,
        "limitations": limitations,
        "detection_method": DETECTION_METHOD,
    }
