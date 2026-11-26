"""Source-linked, extractive research retrieval for selected analysis factors.

OpenAlex supplies article metadata and abstracts. Retrieval uses separate
factor-focused queries, then filters, deduplicates and reranks the candidates
with source metadata and abstract evidence. No generated citations or claims.
"""
from __future__ import annotations

import json
import re
import socket
import threading
import time
from datetime import date, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

_STOP = set("""
startup startups business businesses failure failed failures risk risks study studies research evidence the a an and or
to for of in on by from with its their your this that into across about may can how why what where when which does
effect effects impact factors factor company companies venture ventures entrepreneurial entrepreneurship idea
research source sources recent journal articles article using based new
different among within without through have has had are was were been being their these those them they we our you
""".split())

FOCUS_TERMS = {
    "Market": (
        "market demand customer acquisition customer retention competition competitors product differentiation "
        "willingness to pay repeat purchase purchasing churn adoption trust product claims seller verification"
    ),
    "Industry": (
        "industry inventory unsold stock trend volatility apparel clothing sizing returns supply chain fulfilment "
        "fulfillment margins seasonality logistics packaging replenishment sourcing"
    ),
    "Funding": "venture capital financing runway cash burn startup funding rounds",
    "Traction": "customer adoption retention growth engagement repeat purchase product usage",
    "Location": "regional startup ecosystem local policy geographic entrepreneurship venture capital",
}
FOCUS_QUERY_TERMS = {
    # These are deliberately shorter than the matching vocabularies above.
    # Sending every possible keyword in one OpenAlex search over-constrained
    # the provider request for otherwise searchable startup profiles.
    "Market": "demand acquisition retention competition purchase adoption",
    "Industry": "inventory unsold stock returns sizing supply chain margins seasonality",
    "Funding": "financing runway cash burn venture capital",
    "Traction": "adoption retention engagement repeat purchase",
    "Location": "regional ecosystem local policy geographic entrepreneurship",
}
FOCUS_ANCHORS = {
    "Market": {"demand", "acquisition", "retention", "competition", "differentiation", "willingness", "purchase", "purchasing", "churn", "adoption", "trust", "claims", "verification", "liquidity", "seller", "repeat"},
    "Industry": {"inventory", "unsold", "stock", "trend", "volatility", "apparel", "clothing", "sizing", "returns", "supply", "chain", "fulfilment", "fulfillment", "margins", "seasonality", "logistics", "packaging", "replenishment", "sourcing", "seller", "verification", "liquidity"},
    "Funding": {"financing", "runway", "cash", "burn", "capital", "funding", "liquidity"},
    "Traction": {"adoption", "retention", "engagement", "repeat", "purchase", "purchasing", "usage"},
    "Location": {"regional", "ecosystem", "policy", "geographic", "capital", "local"},
}
GENERIC_INDUSTRY_TERMS = {"clean", "technology"}
SPECIFIC_PROFILE_TERMS = {
    "marketplace", "marketplaces", "liquidity", "seller", "sellers", "buyer", "buyers",
    "sustainable", "sustainability", "green", "trust", "claims", "verification",
    "consumer", "consumers", "purchasing", "purchase",
}
# Words that describe many unrelated businesses are useful in a query, but
# cannot establish that a paper concerns this founder's actual product.
GENERIC_TOPIC_TERMS = {
    "business", "businesses", "company", "companies", "customer", "customers", "consumer", "consumers",
    "product", "products", "startup", "startups", "online", "purchase", "purchasing", "market", "markets",
    "delivery", "delivered", "service", "services", "platform", "platforms", "model", "models", "using",
    "local", "simple", "users", "user", "urban", "young", "households", "repeat", "repeats", "retention",
    "cost", "costs", "viable", "concern", "concerns", "problem", "problems", "challenge", "challenges",
    "acquisition", "revenue", "growth", "refillable",
}
STRONG_FACTOR_ANCHORS = {
    "Market": {"acquisition", "retention", "competition", "differentiation", "willingness", "churn", "trust", "claims", "verification", "liquidity", "seller"},
    "Industry": {"inventory", "unsold", "stock", "trend", "volatility", "apparel", "clothing", "sizing", "returns", "supply", "chain", "fulfilment", "fulfillment", "margins", "seasonality", "logistics", "packaging", "replenishment", "sourcing"},
    "Funding": {"financing", "runway", "cash", "burn", "capital", "funding"},
    "Traction": {"retention", "engagement", "usage"},
    "Location": {"regional", "ecosystem", "policy", "geographic", "capital", "local"},
}
COUNTRY_NAMES = {"IND": "India", "USA": "United States", "GBR": "United Kingdom", "CAN": "Canada", "AUS": "Australia"}
_CACHE: dict[str, tuple[float, dict]] = {}
_LOCK = threading.Lock()
_TTL = 6 * 60 * 60
_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.I)


def _terms(*values: str | None) -> set[str]:
    return {
        word for value in values if isinstance(value, str) and value
        for word in re.findall(r"[a-z][a-z0-9-]{2,}", value.casefold())
        if word not in _STOP
    }


def _ordered_terms(*values: str | None, exclude: set[str] | None = None, limit: int = 18) -> list[str]:
    blocked = _STOP | (exclude or set())
    found: list[str] = []
    seen: set[str] = set()
    for value in values:
        for raw in re.findall(r"[a-z][a-z0-9-]{2,}", (value or "").casefold()):
            if raw not in blocked and raw not in seen:
                seen.add(raw)
                found.append(raw)
                if len(found) == limit:
                    return found
    return found


def _profile_text(context: dict | None) -> list[str]:
    """Flatten only known, text-valued profile fields; metric provenance stays out."""
    context = context or {}
    profile = context.get("profile") if isinstance(context.get("profile"), dict) else {}
    identity = profile.get("identity") if isinstance(profile.get("identity"), dict) else {}
    details = profile.get("business_model_details") if isinstance(profile.get("business_model_details"), dict) else {}
    aliases = {
        "marketplace": "two-sided marketplace platform", "dtc_ecommerce": "direct-to-consumer ecommerce",
        "b2b_saas": "business software subscription", "b2c_saas": "consumer software subscription",
        "hardware": "hardware manufacturing product", "fintech": "financial technology services",
        "biotech_medtech": "biotechnology medical device development", "services_consulting": "professional services delivery",
        "consumer_application": "consumer digital application", "platform_developer_tools": "developer platform software",
    }
    model = identity.get("business_model")
    values = [aliases.get(model, "") if isinstance(model, str) else ""]
    values.extend(identity.get(key) for key in ("problem", "proposed_solution", "operating_geography", "target_market_geography"))
    values.extend(details.get(key) for key in (
        "buyer_group", "seller_group", "liquidity_notes", "fulfilment_notes", "sales_cycle_notes", "renewal_notes",
        "service_type", "delivery_capacity_notes", "supply_chain_dependencies", "product_category",
        "regulatory_jurisdiction", "regulatory_pathway", "technology_constraints", "critical_dependencies",
        "suppliers_or_distribution", "acquisition_channel",
    ))
    for section_name in ("customer_market", "product_traction", "economics", "finance", "team_operations"):
        section = profile.get(section_name)
        if isinstance(section, dict):
            values.extend(value for key, value in section.items() if key != "metrics" and isinstance(value, str))
    values.extend(context.get(key) for key in ("concept", "vision", "customer", "revenue_model", "biggest_worry"))
    return [value for value in values if isinstance(value, str) and value.strip()]


def _profile_topic_terms(context: dict | None) -> set[str]:
    """Return only founder-supplied topic terms suitable for a relevance gate."""
    context = context or {}
    values = [context.get(key) for key in ("concept", "customer", "revenue_model")]
    profile = context.get("profile") if isinstance(context.get("profile"), dict) else {}
    identity = profile.get("identity") if isinstance(profile.get("identity"), dict) else {}
    values.extend(identity.get(key) for key in ("problem", "proposed_solution"))
    return _terms(*values) - GENERIC_TOPIC_TERMS


def _profile_topic_query(context: dict | None, focus: str) -> str:
    """Build one short search around the actual product and its selected lens."""
    terms = _ordered_terms(*_profile_text(context), exclude=GENERIC_TOPIC_TERMS, limit=18)
    product_terms = [term for term in terms if term in {
        "refill", "refills", "refillable", "concentrate", "concentrated", "cleaning", "cleaner",
        "cleaners", "household", "reusable", "reuse", "packaging", "bottle", "bottles", "fashion", "apparel",
        "clothing", "software", "marketplace", "marketplaces", "fintech", "biotech", "hardware",
    }]
    if not product_terms:
        product_terms = terms[:3]
    topic = _ordered_terms(
        *(term for term in ("refill", "household", "cleaning", "concentrate", "reusable", "packaging", "bottle", "fashion", "apparel", "clothing", "software", "marketplace", "fintech", "biotech", "hardware") if term in product_terms),
        limit=2,
    )
    if not topic:
        return ""
    if focus == "Market":
        lens = "consumer purchase willingness" if {"refill", "refills", "refillable", "reusable", "packaging"} & set(topic) else "demand purchase retention"
    elif focus == "Industry":
        lens = "packaging supply chain logistics" if {"refill", "refills", "refillable", "reusable", "packaging"} & set(topic) else "inventory supply chain returns"
    else:
        lens = " ".join(_ordered_terms(FOCUS_QUERY_TERMS.get(focus, ""), limit=2))
    profile = (context or {}).get("profile") if isinstance((context or {}).get("profile"), dict) else {}
    operations = profile.get("team_operations") if isinstance(profile.get("team_operations"), dict) else {}
    operational_terms = _ordered_terms(*(operations.get(key) for key in (
        "critical_dependencies", "suppliers_or_distribution", "technology_constraints",
    )), limit=2)
    return " ".join(part for part in (" ".join(topic + operational_terms), lens) if part)


def _business_model_research_terms(context: dict | None, focus: str) -> str:
    profile = (context or {}).get("profile")
    identity = profile.get("identity") if isinstance(profile, dict) and isinstance(profile.get("identity"), dict) else {}
    model = identity.get("business_model")
    expansions = {
        ("marketplace", "Market"): "two-sided marketplace liquidity seller onboarding participation",
        ("marketplace", "Industry"): "marketplace seller verification fulfilment platform operations",
        ("dtc_ecommerce", "Market"): "ecommerce consumer demand acquisition conversion repeat purchase",
        ("dtc_ecommerce", "Industry"): "ecommerce inventory returns fulfilment logistics margins",
        ("b2b_saas", "Market"): "business software buying adoption sales cycle customer retention",
        ("b2b_saas", "Industry"): "software onboarding implementation support infrastructure operations",
        ("b2c_saas", "Market"): "consumer software adoption engagement retention subscription",
        ("hardware", "Industry"): "hardware manufacturing sourcing supply chain quality warranty",
        ("fintech", "Industry"): "financial technology trust payments compliance regulation",
        ("biotech_medtech", "Industry"): "clinical validation development regulatory pathway",
        ("services_consulting", "Industry"): "service delivery capacity utilization margins operations",
    }
    terms = expansions.get((model, focus), "")
    submitted_terms = _terms(*_profile_text(context))
    if focus == "Market" and submitted_terms & {"sustainable", "sustainability", "green", "eco-conscious"}:
        terms += " consumer sustainability purchasing trust claims"
    return terms.strip()


def _abstract(index: dict | None) -> str:
    if not isinstance(index, dict):
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        if isinstance(word, str) and isinstance(positions, list):
            words.extend((pos, word) for pos in positions if isinstance(pos, int))
    return " ".join(word for _, word in sorted(words))


def _focus_for(node: str, focus: str | None) -> str:
    if focus in FOCUS_TERMS:
        return focus
    text = node.casefold()
    # The model's category/tag features are Industry. Market is a separate
    # research lens, not a score the current training data can support.
    for name in ("Industry", "Funding", "Traction", "Location", "Market"):
        if name.casefold() in text:
            return name
    return "Industry"


def build_queries(
    tags: list[str], node: str, context: dict | None = None,
    country: str | None = None, startup_name: str | None = None,
    focus: str | None = None,
) -> tuple[str, list[str], set[str], set[str]]:
    """Create a small set of bounded searches from context and distinct topics.

    Only selected fields and extracted search terms are used. The startup title
    is excluded so the company name is not sent to the research provider.
    """
    context = context or {}
    selected = _focus_for(node, focus)
    private_terms = _terms(startup_name)
    context_terms = _ordered_terms(
        *_profile_text(context), exclude=private_terms, limit=18,
    )
    field_terms = _terms(*tags)
    risk_terms = _terms(FOCUS_TERMS[selected])
    place_parts = [COUNTRY_NAMES.get(part.upper(), part) for part in (country or "").split() if part.upper() != "OTHER"]
    place = " ".join(place_parts)
    context_query = context_terms[:4]
    focus_query = _ordered_terms(FOCUS_QUERY_TERMS[selected], limit=4)
    model_query = _ordered_terms(_business_model_research_terms(context, selected), limit=4)
    # Keep each provider query concise and topical. Market and Industry have
    # separate mechanism vocabularies; relevant profile terms are distributed
    # across bounded variants instead of appended as a long keyword dump.
    profile_terms = _terms(*_profile_text(context))
    domain_query = _ordered_terms(
        "consumer sustainability purchasing trust claims"
        if selected == "Market" and profile_terms & {"sustainable", "sustainability", "green", "eco-conscious"}
        else "seller verification fulfilment supply chain margins",
        limit=4,
    )
    queries = [
        " ".join(part for part in (" ".join(tags[:2]), place, " ".join(context_query), " ".join(focus_query)) if part).strip(),
        " ".join(part for part in (" ".join(tags[:2]), place, " ".join(model_query), " ".join(domain_query), " ".join(focus_query[:2])) if part).strip(),
    ]
    customer = (context or {}).get("customer") or ""
    profile = (context or {}).get("profile")
    if isinstance(profile, dict) and isinstance(profile.get("customer_market"), dict):
        customer = " ".join(value for key, value in profile["customer_market"].items() if key != "metrics" and isinstance(value, str))
    if customer.strip():
        queries.append(" ".join(part for part in (
            " ".join(tags[:2]), place, "consumer behaviour", " ".join(_ordered_terms(customer, limit=3)),
            " ".join(domain_query), " ".join(focus_query[:2]),
        ) if part).strip())
    topic_query = _profile_topic_query(context, selected)
    if topic_query:
        # Keep product-specific retrieval separate from broad category searches:
        # OpenAlex can otherwise rank generic tag matches above the submitted idea.
        queries.append(topic_query)
    team = profile.get("team_operations") if isinstance(profile, dict) and isinstance(profile.get("team_operations"), dict) else {}
    operations = " ".join(_ordered_terms(*(team.get(key) for key in ("critical_dependencies", "suppliers_or_distribution", "technology_constraints")), limit=5))
    if operations and not topic_query:
        queries.append(" ".join(part for part in (
            " ".join(tags[:2]), place, " ".join(_ordered_terms(operations, limit=4)), " ".join(focus_query[:3]),
        ) if part).strip())
    return selected, list(dict.fromkeys(q for q in queries if q))[:4], field_terms, risk_terms


def _snippet(
    abstract: str, field_terms: set[str], risk_terms: set[str], topic_terms: set[str] | None = None,
    strong_factor_terms: set[str] | None = None,
) -> tuple[str, bool]:
    """Return an extractive sentence that links the topic to a factor mechanism."""
    if not abstract:
        return "", False
    sentences = re.split(r"(?<=[.!?])\s+", abstract)
    parsed = [(s.strip(), _terms(s)) for s in sentences if s.strip()]
    strong_factor_terms = strong_factor_terms or risk_terms
    topic_terms = topic_terms or set()
    # Preserve negative and null findings: negation is substantive evidence,
    # not a reason to discard an otherwise relevant source passage.
    direct = [(s, words) for s, words in parsed if words & field_terms and words & strong_factor_terms and (not topic_terms or words & topic_terms)]
    if direct:
        sentence, _ = max(direct, key=lambda item: len((item[1] & field_terms) | (item[1] & risk_terms)))
        return _clip(sentence), True
    contextual = [(s, words) for s, words in parsed if words & strong_factor_terms and (not topic_terms or words & topic_terms)]
    if contextual:
        sentence, _ = max(contextual, key=lambda item: len(item[1] & risk_terms))
        return _clip(sentence), False
    return "", False


def _clip(text: str, length: int = 420) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:length].rstrip() + ("…" if len(text) > length else "")


def _safe_web_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlparse(value.strip())
        return value.strip() if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password else None
    except ValueError:
        return None


def _identity(work: dict) -> str:
    doi = _valid_doi(work.get("doi"))
    if doi:
        return doi.casefold()
    title = work.get("title") if isinstance(work.get("title"), str) else ""
    return re.sub(r"[^a-z0-9]+", "", title.casefold())


def _valid_doi(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    try:
        parsed = urlparse(raw)
        if parsed.scheme in {"http", "https"}:
            if parsed.hostname not in {"doi.org", "www.doi.org", "dx.doi.org"}:
                return None
            raw = parsed.path.lstrip("/")
        elif "://" in raw:
            return None
    except ValueError:
        return None
    return raw if _DOI_PATTERN.fullmatch(raw) else None


def _candidate(work: dict, field_terms: set[str], business_terms: set[str], risk_terms: set[str], context_terms: set[str], topic_terms: set[str], selected: str):
    title = work.get("title") if isinstance(work.get("title"), str) else ""
    abstract = _abstract(work.get("abstract_inverted_index"))
    if not title or not abstract:
        return None
    title_terms, abstract_terms = _terms(title), _terms(abstract)
    # A broad tag such as "technology" cannot make an unrelated paper relevant
    # to an e-commerce startup. Keep specific industry words in the acceptance
    # gate; generic submitted tags remain available as supporting metadata.
    field_hits = (field_terms - GENERIC_INDUSTRY_TERMS) & (title_terms | abstract_terms)
    business_hits = business_terms & (title_terms | abstract_terms)
    profile_hits = field_hits | business_hits
    risk_hits = risk_terms & (title_terms | abstract_terms)
    topic_hits = topic_terms & (title_terms | abstract_terms)
    strong_factor_hits = STRONG_FACTOR_ANCHORS[selected] & (title_terms | abstract_terms)
    if not profile_hits or not risk_hits:
        return None
    if topic_terms and not topic_hits:
        return None
    if not strong_factor_hits:
        return None
    if not field_hits and len(business_hits & SPECIFIC_PROFILE_TERMS) < 2:
        return None

    # A single broad word ("market", "customer", "industry") is too weak to
    # support a startup-specific match. Require two factor-mechanism anchors
    # in the actual title/abstract before ranking or displaying a record.
    anchor_hits = FOCUS_ANCHORS[selected] & (title_terms | abstract_terms)
    if len(anchor_hits) < 2:
        return None

    excerpt, direct = _snippet(abstract, field_hits | business_terms, risk_terms, topic_terms, STRONG_FACTOR_ANCHORS[selected])
    if not excerpt:
        return None
    location = work.get("primary_location") if isinstance(work.get("primary_location"), dict) else {}
    source = location.get("source") if isinstance(location.get("source"), dict) else {}
    source_type = source.get("type")
    peer_review_screened = source_type == "journal" and bool(source.get("is_in_doaj") or source.get("is_core"))
    repository_record = source_type == "repository"
    if not (peer_review_screened or repository_record):
        return None
    url = _safe_web_url(location.get("landing_page_url")) or _safe_web_url(work.get("doi")) or _safe_web_url(work.get("id"))
    if not url:
        return None

    # Field/factor matches outrank recency. Exact title matches and an abstract
    # sentence that connects the field with the selected factor add weight.
    context_hits = (context_terms - business_terms) & (title_terms | abstract_terms)
    score = (
        5 * len(field_hits & title_terms) + 2 * len(field_hits & abstract_terms)
        + 4 * len(business_terms & title_terms) + 1.5 * len(business_terms & abstract_terms)
        + 4 * len(risk_terms & title_terms) + 1.5 * len(risk_terms & abstract_terms)
        + 1.5 * len(context_terms & title_terms) + 0.5 * len(context_terms & abstract_terms)
        + 1.5 * len(topic_hits) + 5 * int(direct) + 2 * int(bool(source.get("is_in_doaj") or source.get("is_core")))
    )
    date_text = work.get("publication_date") if isinstance(work.get("publication_date"), str) else ""
    year = date_text[:4] if len(date_text) >= 4 else ""
    authors = []
    authorships = work.get("authorships") if isinstance(work.get("authorships"), list) else []
    for authorship in authorships[:6]:
        if not isinstance(authorship, dict):
            continue
        author_record = authorship.get("author")
        author = author_record.get("display_name") if isinstance(author_record, dict) else None
        if author and author not in authors:
            authors.append(author)
    doi = _valid_doi(work.get("doi"))
    doi_url = f"https://doi.org/{doi}" if doi else None
    openalex_id = work.get("id") if isinstance(work.get("id"), str) and work.get("id", "").startswith("https://openalex.org/") else None
    oa = work.get("open_access") if isinstance(work.get("open_access"), dict) else {}
    best_location = work.get("best_oa_location") if isinstance(work.get("best_oa_location"), dict) else {}
    return score, date_text, {
        "title": title,
        "publisher": source.get("display_name") if isinstance(source.get("display_name"), str) else "",
        "journal": source.get("display_name") if isinstance(source.get("display_name"), str) else "",
        "authors": authors,
        "doi": doi_url,
        "openalex_id": openalex_id,
        "url": doi_url or url,
        "published": date_text,
        "year": year,
        "venue_status": "Repository record; peer-review status unknown" if repository_record else "DOAJ-listed by OpenAlex" if source.get("is_in_doaj") else "CWTS Core-listed by OpenAlex",
        "source_type": source_type or "unknown",
        "publication_type": work.get("type_crossref") if isinstance(work.get("type_crossref"), str) else work.get("type") if isinstance(work.get("type"), str) else "unknown",
        "metadata_status": "OpenAlex record; bibliographic metadata not independently verified",
        "access_status": "abstract_only" if abstract else "metadata_only",
        "open_access_url": _safe_web_url(best_location.get("landing_page_url")) or _safe_web_url(oa.get("oa_url")),
        "retrieved_at": date.today().isoformat(),
        "excerpt": excerpt,
        "relation": "direct" if direct else "contextual",
        "relevance_dimensions": sorted(((["industry"] if field_hits else []) + (["business model / operating mechanism"] if business_hits else []) + (["factor mechanism"] if risk_hits else []) + (["founder context"] if context_hits else []))),
        "focus": selected,
        "matched_terms": sorted(profile_hits | risk_hits | context_hits | topic_hits)[:12],
    }


def retrieve(
    tags: list[str], node: str, context: dict | None = None, country: str | None = None,
    startup_name: str | None = None, focus: str | None = None, limit: int = 8,
) -> list[dict]:
    """Return distinct, recent OpenAlex works supported by their abstracts.

    Candidate retrieval is lexical because this application has no embedding
    index. Abstract/title and source metadata are used for reranking; weak
    candidates are discarded rather than filled with generic works.
    """
    return retrieve_detailed(tags, node, context, country, startup_name, focus, limit)["sources"]


def retrieve_detailed(
    tags: list[str], node: str, context: dict | None = None, country: str | None = None,
    startup_name: str | None = None, focus: str | None = None, limit: int = 8,
) -> dict:
    """Return bounded retrieval outcomes and distinguish weak results from provider failure."""
    selected, queries, field_terms, risk_terms = build_queries(tags, node, context, country, startup_name, focus)
    if not field_terms or not risk_terms or not queries:
        return {"sources": [], "state": "insufficient_query_context", "queries_attempted": 0, "query_results": [], "records_retrieved": 0, "candidates_filtered": 0, "weak_candidates": 0, "retrieved_at": date.today().isoformat()}
    place_terms = [COUNTRY_NAMES.get(part.upper(), part) for part in (country or "").split() if part.upper() != "OTHER"]
    business_terms = _terms(_business_model_research_terms(context, selected))
    context_terms = (_terms(*_profile_text(context)) | _terms(*place_terms) | business_terms) - _terms(startup_name)
    topic_terms = _profile_topic_terms(context)
    cache_key = "|".join((selected, *sorted(field_terms), *sorted(context_terms), *queries, (country or "").upper()))
    with _LOCK:
        cached = _CACHE.get(cache_key)
        if cached and time.time() - cached[0] < _TTL:
            return cached[1] | {"sources": cached[1]["sources"][:limit]}

    today = date.today()
    windows = [today - timedelta(days=183), today - timedelta(days=365 * 7)]
    ranked: dict[str, tuple[float, str, dict]] = {}
    records_retrieved = 0
    filtered = 0
    errors: list[str] = []
    queries_attempted = 0
    query_results: list[dict] = []
    weak_candidates = 0
    for window_index, since in enumerate(windows):
        window_queries = queries if window_index == 0 else queries[:1]
        for query_index, query in enumerate(window_queries):
            queries_attempted += 1
            params = urlencode({
                "search": query,
                "filter": f"from_publication_date:{since.isoformat()},to_publication_date:{today.isoformat()},type:article",
                "per-page": 50,
                "cursor": "*",
            })
            request = Request(
                f"https://api.openalex.org/works?{params}",
                headers={"User-Agent": "Fragilee/1.0 (source-linked startup research)"},
            )
            payload = None
            final_error = None
            for attempt in range(2):
                try:
                    with urlopen(request, timeout=7) as response:
                        payload = json.loads(response.read().decode("utf-8"))
                    break
                except HTTPError as error:
                    if attempt == 0 and error.code in {429, 500, 502, 503, 504}:
                        retry_after = 0.1
                        if error.code == 429:
                            try:
                                retry_after = min(2.0, max(0.1, float(error.headers.get("Retry-After", "0.1"))))
                            except (TypeError, ValueError, AttributeError):
                                retry_after = 0.1
                        time.sleep(retry_after)
                        continue
                    final_error = "rate_limited" if error.code == 429 else f"http_{error.code}"
                    break
                except (TimeoutError, socket.timeout):
                    if attempt == 0:
                        time.sleep(0.05)
                        continue
                    final_error = "provider_timeout"
                    break
                except URLError as error:
                    if attempt == 0:
                        time.sleep(0.05)
                        continue
                    final_error = "provider_timeout" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "provider_request_failed"
                    break
                except (OSError, ValueError):
                    if attempt == 0:
                        time.sleep(0.05)
                        continue
                    final_error = "provider_request_failed"
                    break
            if final_error:
                errors.append(final_error)
            if not isinstance(payload, dict):
                if final_error is None:
                    errors.append("invalid_provider_payload")
                query_results.append({"query_index": queries_attempted, "state": final_error or "provider_error", "records": 0, "accepted": 0})
                continue

            records = payload.get("results", [])
            if not isinstance(records, list):
                errors.append("invalid_provider_payload")
                query_results.append({"query_index": queries_attempted, "state": "invalid_payload", "records": 0, "accepted": 0})
                continue
            query_ranked_before = len(ranked)
            records_retrieved += len(records)
            for work in records:
                if not isinstance(work, dict):
                    filtered += 1
                    continue
                publication_date = work.get("publication_date") if isinstance(work.get("publication_date"), str) else ""
                if publication_date and publication_date > today.isoformat():
                    filtered += 1
                    continue
                candidate = _candidate(work, field_terms, business_terms, risk_terms, context_terms, topic_terms, selected)
                identity = _identity(work)
                if candidate and identity:
                    score, pub_date, source = candidate
                    previous = ranked.get(identity)
                    if previous is None or (score, pub_date) > (previous[0], previous[1]):
                        ranked[identity] = (score, pub_date, source)
                else:
                    filtered += 1
                    title = work.get("title") if isinstance(work.get("title"), str) else ""
                    abstract = _abstract(work.get("abstract_inverted_index"))
                    words = _terms(title, abstract)
                    if (words & field_terms) or (words & risk_terms):
                        weak_candidates += 1
            query_results.append({"query_index": queries_attempted, "state": "results" if records else "no_results", "records": len(records), "accepted": max(0, len(ranked) - query_ranked_before)})
            meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
            if window_index == 0 and query_index == 0 and len(ranked) < 3 and meta.get("next_cursor"):
                page_params = urlencode({
                    "search": query,
                    "filter": f"from_publication_date:{since.isoformat()},to_publication_date:{today.isoformat()},type:article",
                    "per-page": 50,
                    "cursor": payload["meta"]["next_cursor"],
                })
                page_request = Request(f"https://api.openalex.org/works?{page_params}", headers={"User-Agent": "Fragilee/1.0 (source-linked startup research)"})
                try:
                    with urlopen(page_request, timeout=7) as response:
                        page_payload = json.loads(response.read().decode("utf-8"))
                    page_records = page_payload.get("results", []) if isinstance(page_payload, dict) else []
                    records_retrieved += len(page_records) if isinstance(page_records, list) else 0
                    page_ranked_before = len(ranked)
                    for work in page_records if isinstance(page_records, list) else []:
                        if not isinstance(work, dict):
                            filtered += 1
                            continue
                        candidate = _candidate(work, field_terms, business_terms, risk_terms, context_terms, topic_terms, selected)
                        identity = _identity(work)
                        if candidate and identity:
                            score, pub_date, source = candidate
                            previous = ranked.get(identity)
                            if previous is None or (score, pub_date) > (previous[0], previous[1]):
                                ranked[identity] = (score, pub_date, source)
                        else:
                            filtered += 1
                            title = work.get("title") if isinstance(work.get("title"), str) else ""
                            abstract = _abstract(work.get("abstract_inverted_index"))
                            words = _terms(title, abstract)
                            if (words & field_terms) or (words & risk_terms):
                                weak_candidates += 1
                    query_results.append({"query_index": queries_attempted, "page": 2, "state": "results" if page_records else "no_results", "records": len(page_records) if isinstance(page_records, list) else 0, "accepted": max(0, len(ranked) - page_ranked_before)})
                except (HTTPError, OSError, URLError, TimeoutError, ValueError):
                    errors.append("pagination_failed")
        if len(ranked) >= 3:
            break

    # Recency breaks close relevance ties; it never rescues a weak match.
    ordered = sorted(ranked.values(), key=lambda item: (-item[0], -int(item[1].replace("-", "")) if item[1] else 0))
    found = [item[2] for item in ordered[:limit]]
    if found:
        state = "partial" if errors else "relevant_results"
    elif errors and records_retrieved > 0:
        state = "partial"
    elif errors and records_retrieved == 0:
        error_states = set(errors)
        if error_states == {"provider_request_failed"}:
            state = "provider_unavailable"
        elif error_states == {"provider_timeout"}:
            state = "provider_timeout"
        elif error_states == {"rate_limited"}:
            state = "rate_limited"
        else:
            state = "provider_error"
    elif records_retrieved == 0:
        state = "no_results"
    else:
        state = "weak_relevance" if weak_candidates else "filtered_out"
    result = {"sources": found, "state": state, "queries_attempted": queries_attempted, "query_results": query_results, "records_retrieved": records_retrieved, "candidates_filtered": filtered, "weak_candidates": weak_candidates, "retrieved_at": date.today().isoformat()}
    if not errors:
        with _LOCK:
            _CACHE[cache_key] = (time.time(), result)
    return result
