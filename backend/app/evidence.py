"""Source-linked, extractive research retrieval for selected analysis factors.

OpenAlex supplies article metadata and abstracts. Retrieval uses separate
factor-focused queries, then filters, deduplicates and reranks the candidates
with source metadata and abstract evidence. No generated citations or claims.
"""
from __future__ import annotations

import json
import re
import threading
import time
from datetime import date, timedelta
from urllib.error import URLError
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
        "willingness to pay repeat purchase churn adoption"
    ),
    "Industry": (
        "industry inventory unsold stock trend volatility apparel clothing sizing returns supply chain fulfilment "
        "fulfillment margins seasonality"
    ),
    "Funding": "venture capital financing runway cash burn startup funding rounds",
    "Traction": "customer adoption retention growth engagement repeat purchase product usage",
    "Location": "regional startup ecosystem local policy geographic entrepreneurship venture capital",
}
COUNTRY_NAMES = {"IND": "India", "USA": "United States", "GBR": "United Kingdom", "CAN": "Canada", "AUS": "Australia"}
_CACHE: dict[str, tuple[float, list[dict]]] = {}
_LOCK = threading.Lock()
_TTL = 6 * 60 * 60


def _terms(*values: str | None) -> set[str]:
    return {
        word for value in values if value
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


def _abstract(index: dict | None) -> str:
    if not isinstance(index, dict):
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        if isinstance(positions, list):
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
    """Create two bounded searches from idea context and distinct risk topics.

    Only selected fields and extracted search terms are used. The startup title
    is excluded so the company name is not sent to the research provider.
    """
    context = context or {}
    selected = _focus_for(node, focus)
    private_terms = _terms(startup_name)
    context_terms = _ordered_terms(
        context.get("concept"), context.get("vision"), context.get("customer"), context.get("revenue_model"),
        exclude=private_terms, limit=18,
    )
    field_terms = _terms(*tags)
    risk_terms = _terms(FOCUS_TERMS[selected])
    place_parts = [COUNTRY_NAMES.get(part.upper(), part) for part in (country or "").split() if part.upper() != "OTHER"]
    place = " ".join(place_parts)
    industry = " ".join(tags)
    context_query = " ".join(context_terms[:10])
    risk_query = FOCUS_TERMS[selected]
    # Separate context-rich and category-expanded candidates. Market and
    # Industry therefore do not issue the same query for the same startup.
    queries = [
        " ".join(part for part in (industry, context_query, risk_query) if part).strip(),
        " ".join(part for part in (industry, place, "startup", risk_query) if part).strip(),
    ]
    return selected, list(dict.fromkeys(q for q in queries if q)), field_terms, risk_terms


def _snippet(abstract: str, field_terms: set[str], risk_terms: set[str]) -> tuple[str, bool]:
    """Return a source sentence; the flag is true only when it links field+factor."""
    if not abstract:
        return "", False
    sentences = re.split(r"(?<=[.!?])\s+", abstract)
    parsed = [(s.strip(), _terms(s)) for s in sentences if s.strip()]
    def negates_risk(sentence: str) -> bool:
        return bool(re.search(r"\b(no|not|nothing|without|lack|lacks|neither)\b", sentence.casefold()))

    direct = [(s, words) for s, words in parsed if not negates_risk(s) and words & field_terms and words & risk_terms]
    if direct:
        sentence, _ = max(direct, key=lambda item: len((item[1] & field_terms) | (item[1] & risk_terms)))
        return _clip(sentence), True
    contextual = [(s, words) for s, words in parsed if not negates_risk(s) and words & risk_terms]
    if contextual:
        sentence, _ = max(contextual, key=lambda item: len(item[1] & risk_terms))
        return _clip(sentence), False
    return "", False


def _clip(text: str, length: int = 420) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:length].rstrip() + ("…" if len(text) > length else "")


def _identity(work: dict) -> str:
    doi = (work.get("doi") or "").casefold().strip().rstrip("/")
    if doi:
        return doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    return re.sub(r"[^a-z0-9]+", "", (work.get("title") or "").casefold())


def _candidate(work: dict, field_terms: set[str], risk_terms: set[str], context_terms: set[str], selected: str):
    title = work.get("title") or ""
    abstract = _abstract(work.get("abstract_inverted_index"))
    if not title or not abstract:
        return None
    title_terms, abstract_terms = _terms(title), _terms(abstract)
    field_hits = field_terms & (title_terms | abstract_terms)
    risk_hits = risk_terms & (title_terms | abstract_terms)
    if not field_hits or not risk_hits:
        return None

    excerpt, direct = _snippet(abstract, field_terms, risk_terms)
    if not excerpt:
        return None
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    if source.get("type") != "journal" or not (source.get("is_in_doaj") or source.get("is_core")):
        return None
    url = location.get("landing_page_url") or work.get("doi") or work.get("id")
    if not url or urlparse(url).scheme not in {"http", "https"}:
        return None

    # Field/factor matches outrank recency. Exact title matches and an abstract
    # sentence that connects the field with the selected factor add weight.
    context_hits = context_terms & (title_terms | abstract_terms)
    score = (
        5 * len(field_terms & title_terms) + 2 * len(field_terms & abstract_terms)
        + 4 * len(risk_terms & title_terms) + 1.5 * len(risk_terms & abstract_terms)
        + 1.5 * len(context_terms & title_terms) + 0.5 * len(context_terms & abstract_terms)
        + 5 * int(direct) + 2 * int(bool(source.get("is_in_doaj") or source.get("is_core")))
    )
    date_text = work.get("publication_date") or ""
    year = date_text[:4] if len(date_text) >= 4 else ""
    authors = []
    for authorship in (work.get("authorships") or [])[:6]:
        author = (authorship.get("author") or {}).get("display_name")
        if author and author not in authors:
            authors.append(author)
    doi = work.get("doi") or ""
    return score, date_text, {
        "title": title,
        "publisher": source.get("display_name") or "OpenAlex indexed research",
        "journal": source.get("display_name") or "",
        "authors": authors,
        "doi": doi,
        "url": url,
        "published": date_text,
        "year": year,
        "venue_status": "DOAJ-listed journal" if source.get("is_in_doaj") else "CWTS Core journal",
        "excerpt": excerpt,
        "relation": "direct" if direct else "contextual",
        "focus": selected,
        "matched_terms": sorted(field_hits | risk_hits | context_hits)[:12],
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
    selected, queries, field_terms, risk_terms = build_queries(tags, node, context, country, startup_name, focus)
    if not field_terms or not risk_terms or not queries:
        return []
    place_terms = [COUNTRY_NAMES.get(part.upper(), part) for part in (country or "").split() if part.upper() != "OTHER"]
    context_terms = (
        _terms(*[(context or {}).get(k) for k in ("concept", "vision", "customer", "revenue_model")])
        | _terms(*place_terms)
    ) - _terms(startup_name)
    cache_key = "|".join((selected, *sorted(field_terms), *sorted(context_terms), *queries, (country or "").upper()))
    with _LOCK:
        cached = _CACHE.get(cache_key)
        if cached and time.time() - cached[0] < _TTL:
            return cached[1][:limit]

    today = date.today()
    windows = [today - timedelta(days=183), today - timedelta(days=365 * 7)]
    ranked: dict[str, tuple[float, str, dict]] = {}
    for since in windows:
        for query in queries:
            params = urlencode({
                "search": query,
                "filter": f"from_publication_date:{since.isoformat()},to_publication_date:{today.isoformat()},type:article",
                "per-page": 50,
            })
            request = Request(
                f"https://api.openalex.org/works?{params}",
                headers={"User-Agent": "Fragilee/1.0 (source-linked startup research)"},
            )
            try:
                with urlopen(request, timeout=7) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except (OSError, URLError, TimeoutError, ValueError):
                continue

            for work in payload.get("results", []):
                publication_date = work.get("publication_date") or ""
                if publication_date and publication_date > today.isoformat():
                    continue
                candidate = _candidate(work, field_terms, risk_terms, context_terms, selected)
                identity = _identity(work)
                if candidate and identity:
                    score, pub_date, source = candidate
                    previous = ranked.get(identity)
                    if previous is None or (score, pub_date) > (previous[0], previous[1]):
                        ranked[identity] = (score, pub_date, source)
        if len(ranked) >= 3:
            break

    # Recency breaks close relevance ties; it never rescues a weak match.
    ordered = sorted(ranked.values(), key=lambda item: (-item[0], -int(item[1].replace("-", "")) if item[1] else 0))
    found = [item[2] for item in ordered[:limit]]
    with _LOCK:
        _CACHE[cache_key] = (time.time(), found)
    return found
