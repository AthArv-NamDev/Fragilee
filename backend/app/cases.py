"""Deterministic, provenance-aware matching over the existing curated case library.

The current records are failure examples with sparse structured metadata. This
module only compares values actually present in the founder context and case
record; it does not infer missing outcome, geography, stage, or business model.
"""
import json
import logging
import re
from pathlib import Path

LIBRARY = Path(__file__).resolve().parent.parent / "data" / "cases.json"
log = logging.getLogger("fragilee.cases")
STOP = set("this that with from have your will they them their about into more most some what when where which while would could should there these those been being also just like only over such than then very make made using used startup startups company companies business businesses the and are for its their our your".split())
MECHANISMS = {
    "cash runway": {"cash", "runway", "funding", "burn", "burned", "capital", "money", "finance", "cost", "costs"},
    "customer retention": {"retention", "repeat", "return", "churn", "loyalty", "booking"},
    # Keep this mechanism specific. Generic customer/user/growth language is
    # common in almost every startup account and is not evidence of acquisition
    # costs or channel performance. In particular, the curated Homejoy and
    # Everpix narratives do not document acquisition as a failure mechanism.
    "customer acquisition": {"acquisition", "marketing", "advertising", "conversion", "cac"},
    "competition and differentiation": {"competition", "competitors", "crowded", "differentiation", "alternatives", "outcompeted"},
    "marketplace participation": {"marketplace", "liquidity", "seller", "sellers", "buyer", "buyers", "supply", "demand", "workers"},
    "unit economics and margins": {"margin", "margins", "economics", "revenue", "profit", "profitable", "hosting", "salary", "salaries"},
    "regulatory and legal exposure": {"legal", "lawsuit", "lawsuits", "regulatory", "regulation", "classification"},
    "expansion and operations": {"expansion", "international", "warehouse", "warehouses", "inventory", "operations", "supply"},
}
MODEL_TERMS = {
    "marketplace": {"marketplace", "two-sided marketplace"},
    "dtc_ecommerce": {"ecommerce", "e-commerce", "online store", "retail"},
    "b2b_saas": {"b2b saas", "business software", "enterprise software"},
    "b2c_saas": {"b2c saas", "consumer software", "subscription app"},
    "hardware": {"hardware", "device", "manufacturing"},
    "fintech": {"fintech", "financial technology", "payments"},
    "biotech_medtech": {"biotech", "medical device", "therapeutics"},
    "services_consulting": {"consulting", "professional services", "service business"},
}
CONTEXT_ANCHORS = {
    "hardware", "gadget", "assistant", "photo", "storage", "fashion", "ecommerce", "marketplace",
    "marketplaces", "seller", "sellers", "buyer", "buyers", "sustainable", "sustainability", "green",
    "consumer", "consumers", "software", "retail", "inventory", "supply", "medical", "health", "fintech",
    "subscription", "agriculture", "farm", "food", "delivery", "commerce", "trust", "claims", "verification",
}


def load(path: Path = LIBRARY) -> list[dict]:
    try:
        library = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        log.warning("case library unavailable reason=read_or_parse_error")
        return []
    if not isinstance(library, dict) or not isinstance(library.get("cases"), list):
        log.warning("case library unavailable reason=invalid_structure")
        return []
    scope = "failure_examples" if "failure" in str(library.get("_about", "")).casefold() else "unknown"
    return [dict(case, _collection_scope=scope) for case in library.get("cases", []) if isinstance(case, dict)]


def _words(*texts: str | None) -> set[str]:
    return {
        word for text in texts if isinstance(text, str)
        for word in re.findall(r"[a-z][a-z0-9+\-]{2,}", text.casefold())
        if word not in STOP
    }


def _profile_text(context: dict) -> list[str]:
    profile = context.get("profile") if isinstance(context.get("profile"), dict) else {}
    values = [context.get(key) for key in ("concept", "vision", "customer", "revenue_model", "biggest_worry")]
    identity = profile.get("identity") if isinstance(profile.get("identity"), dict) else {}
    values.extend(identity.get(key) for key in ("problem", "proposed_solution", "operating_geography", "target_market_geography"))
    for section_name, fields in {
        "customer_market": ("customer_segment", "customer_description", "discovery_evidence", "willingness_to_pay_evidence", "existing_alternatives", "market_size_assumption"),
        "product_traction": ("customer_validation", "acquisition_channel"),
        "economics": ("revenue_model", "pricing_model", "acquisition_channel"),
        "finance": ("funding_status", "funding_sources", "upcoming_milestones"),
        "team_operations": ("team_capabilities", "capability_gaps", "critical_dependencies", "suppliers_or_distribution", "technology_constraints", "regulatory_context"),
        "business_model_details": ("buyer_group", "seller_group", "liquidity_notes", "fulfilment_notes", "sales_cycle_notes", "renewal_notes", "service_type", "delivery_capacity_notes", "supply_chain_dependencies", "product_category", "regulatory_jurisdiction", "regulatory_pathway", "licensing_status", "infrastructure_dependencies"),
    }.items():
        section = profile.get(section_name)
        if isinstance(section, dict):
            values.extend(section.get(key) for key in fields)
    return [value for value in values if isinstance(value, str) and value.strip()]


def _mechanism_matches(context: dict, case: dict) -> list[str]:
    founder_words = _words(*_profile_text(context))
    reasons = case.get("reasons") if isinstance(case.get("reasons"), list) else []
    case_words = _words(" ".join(value for value in reasons if isinstance(value, str)), case.get("how_it_failed"))
    matches = []
    for label, terms in MECHANISMS.items():
        if len(founder_words & terms) >= 2 and len(case_words & terms) >= 2:
            matches.append(label)
    return matches


def _explicit_model_match(context: dict, case: dict) -> bool:
    profile = context.get("profile") if isinstance(context.get("profile"), dict) else {}
    identity = profile.get("identity") if isinstance(profile.get("identity"), dict) else {}
    model = identity.get("business_model")
    terms = MODEL_TERMS.get(model) if isinstance(model, str) else None
    if not terms:
        return False
    # Only explicit words in the case's curated description count. Case tags
    # and generated guesses are not treated as business-model evidence.
    description = " ".join(value for value in (case.get("what"), case.get("sector")) if isinstance(value, str)).casefold()
    return any(term in description for term in terms)


def retrieve(cases: list[dict], tags: list[str], context: dict | None = None, limit: int = 3) -> tuple[list[dict], bool]:
    """Return a small ranked set with explicit match type and data limitations."""
    context = context or {}
    profile_words = _words(*_profile_text(context))
    scored: list[tuple[int, int, str, dict, dict]] = []
    normalized_tags = {tag.casefold().strip() for tag in tags if isinstance(tag, str)}
    seen_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or case["id"] in seen_ids:
            continue
        seen_ids.add(case["id"])
        industries = case.get("industries") if isinstance(case.get("industries"), list) else []
        case_industries = {tag.casefold().strip() for tag in industries if isinstance(tag, str)}
        shared_industries = sorted(tag for tag in normalized_tags & case_industries)
        keywords = case.get("keywords") if isinstance(case.get("keywords"), list) else []
        case_words = _words(case.get("sector"), case.get("what"), case.get("how_it_failed"), " ".join(value for value in keywords if isinstance(value, str)))
        shared_terms = sorted(profile_words & case_words)
        mechanisms = _mechanism_matches(context, case)
        explicit_model = _explicit_model_match(context, case)

        if explicit_model:
            category, rank = "direct_business_model", 4
        elif mechanisms:
            category, rank = "mechanism_based", 3
        elif shared_industries and len(shared_terms) >= 2 and (len(shared_industries) >= 2 or len(shared_terms) >= 3):
            category, rank = "industry_adjacent", 2
        elif len(shared_terms) >= 3 and len(set(shared_terms) & CONTEXT_ANCHORS) >= 2:
            category, rank = "contextual", 1
        else:
            continue

        # Shared labels and terms are explanation inputs, never confidence or
        # predictive scores. Industry alone is deliberately insufficient.
        shared: list[str] = []
        if explicit_model:
            shared.append("The case description explicitly uses language associated with the supplied business-model type.")
        if shared_industries:
            shared.append("Industry tag overlap: " + ", ".join(shared_industries))
        if mechanisms:
            shared.append("Related documented mechanism labels: " + ", ".join(mechanisms))
        if shared_terms:
            shared.append("Shared profile/case terms: " + ", ".join(shared_terms[:5]))

        identity = (context.get("profile") or {}).get("identity", {}) if isinstance(context.get("profile"), dict) else {}
        unrecorded = [label for key, label in (
            ("operating_geography", "geography"), ("stage", "stage"),
        ) if identity.get(key) and not case.get(key)]
        if context.get("startup_stage") and not case.get("stage"):
            unrecorded.append("stage")
        if context.get("customer") or (isinstance(context.get("profile"), dict) and context["profile"].get("customer_market")):
            if not case.get("target_customer"):
                unrecorded.append("target customer")
        profile = context.get("profile") if isinstance(context.get("profile"), dict) else {}
        if context.get("revenue_model") or isinstance(profile.get("economics"), dict):
            if not case.get("revenue_model"):
                unrecorded.append("revenue model")
        if not case.get("business_model") and not explicit_model:
            unrecorded.append("business model")
        differences = [f"The case library does not record {', '.join(dict.fromkeys(unrecorded))}; those dimensions cannot be compared."] if unrecorded else []
        outcome_status = case.get("outcome_status") if isinstance(case.get("outcome_status"), str) else None
        if outcome_status not in {"acquired", "operating", "ipo", "closed", "failed", "unknown", "failure_example_in_curated_failure_only_collection"}:
            outcome_status = None
        if not outcome_status and case.get("_collection_scope") == "failure_examples":
            outcome_status = "failure_example_in_curated_failure_only_collection"
        if outcome_status in {None, "unknown"}:
            outcome_status = "unknown"
        outcome_text = {
            "failure_example_in_curated_failure_only_collection": "This record is in Fragilee's curated failure-only collection; check the linked reporting for the specific outcome and dates.",
            "acquired": "The case record labels the company as acquired; acquisition is not treated as equivalent to every form of success.",
            "operating": "The case record labels the company as operating; this is not a prediction for another startup.",
            "ipo": "The case record labels the company as public/IPO; this is not a prediction for another startup.",
            "closed": "The case record labels the company as closed; check linked reporting for the specific events.",
            "failed": "The case record labels the company as failed; check linked reporting for the specific events.",
            "unknown": "The saved case record does not establish the company's outcome.",
        }.get(outcome_status, "The saved case record does not establish the company's outcome.")
        rationale = {
            "match_category": category,
            "shared_characteristics": shared,
            "important_differences": differences,
            "outcome_status": outcome_status,
            "historical_outcome": outcome_text,
            "documented_lesson": case.get("how_it_failed", ""),
            "comparison_limitations": ["The library contains a small, failure-only sample and is not representative.", "Similarity does not establish the same cause or predict this startup's outcome."],
        }
        reasons = [f"Match category: {category}"]
        reasons.extend(f"Industry: {tag}" for tag in shared_industries)
        reasons.extend(f"Mechanism: {mechanism}" for mechanism in mechanisms)
        reasons.extend(f"Profile term: {term}" for term in shared_terms[:3])
        sources = case.get("sources") if isinstance(case.get("sources"), list) else []
        newest = max((source.get("published", "") for source in sources if isinstance(source, dict) and isinstance(source.get("published"), str)), default="")
        scored.append((rank, len(shared_industries) + len(mechanisms) + len(shared_terms), newest, case, rationale | {"matched_on": reasons}))

    scored.sort(key=lambda row: (-row[0], -row[1], row[2], row[3].get("id", "")))
    picks = scored[:max(0, min(limit, 5))]
    return [public(case, details) for _, _, _, case, details in picks], bool(picks)


def public(case: dict, details: dict) -> dict:
    """Expose only curated public fields and grounded matching explanations."""
    output = {key: case[key] for key in ("id", "name", "years", "sector", "what", "how_it_failed", "reasons", "sources", "verified_on") if key in case}
    output.update(details)
    return output
