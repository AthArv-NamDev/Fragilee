import json
from urllib.parse import parse_qs, urlparse

from app import evidence
from conftest import USER_A, USER_B, headers_for


class Response:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.value


def work(abstract, *, title="Market competition and software startups", doi="https://doi.org/10.1234/demo", date="2026-10-01", source_type="journal", listed=True):
    index = {}
    for position, word in enumerate(abstract.split()):
        index.setdefault(word.strip(".,;:").lower(), []).append(position)
    return {
        "title": title,
        "doi": doi,
        "publication_date": date,
        "abstract_inverted_index": index,
        "authorships": [{"author": {"display_name": "A. Researcher"}}],
        "primary_location": {
            "landing_page_url": f"https://example.org/{doi.rsplit('/', 1)[-1]}",
            "source": {"display_name": "Journal of Startup Research", "type": source_type, "is_in_doaj": listed},
        },
    }


def install_payload(monkeypatch, payload_or_fn):
    requests = []

    def fake(request, timeout):
        requests.append((request, timeout))
        payload = payload_or_fn(request) if callable(payload_or_fn) else payload_or_fn
        return Response(json.dumps(payload).encode())

    monkeypatch.setattr(evidence, "urlopen", fake)
    evidence._CACHE.clear()
    return requests


def test_retrieval_returns_recent_relevant_abstract_excerpt_and_metadata(monkeypatch):
    article = work("Software startups face market competition and survival challenges.")
    requests = install_payload(monkeypatch, {"results": [article]})

    found = evidence.retrieve(["Software"], "Market")

    assert len(found) == 1
    assert found[0]["published"] == "2026-10-01"
    assert found[0]["year"] == "2026"
    assert found[0]["doi"] == article["doi"]
    assert found[0]["authors"] == ["A. Researcher"]
    assert found[0]["relation"] == "direct"
    assert "market" in found[0]["matched_terms"]
    assert "software" in found[0]["excerpt"].lower()
    assert len(requests) == 4  # two query variants, then a wider date window for fewer than three sources
    assert all(parse_qs(urlparse(req.full_url).query)["filter"][0].endswith("type:article") for req, _ in requests)


def test_market_and_industry_query_expansion_are_distinct_and_startup_name_is_not_sent():
    context = {
        "concept": "Fashion e-commerce for Gen Z shoppers in India",
        "customer": "Gen Z women",
        "revenue_model": "Direct to consumer",
    }
    market, market_queries, _, market_terms = evidence.build_queries(
        ["Fashion", "E-Commerce"], "Market", context, "IND", "Zara", "Market")
    industry, industry_queries, _, industry_terms = evidence.build_queries(
        ["Fashion", "E-Commerce"], "Industry", context, "IND", "Zara", "Industry")

    assert market == "Market" and industry == "Industry"
    assert market_queries != industry_queries
    assert all("zara" not in query.casefold() for query in market_queries + industry_queries)
    assert all("fashion" in query.casefold() and "india" in query.casefold() for query in market_queries + industry_queries)
    assert {"competition", "retention", "differentiation"} <= market_terms
    assert {"inventory", "returns", "sizing", "margins"} <= industry_terms


def test_market_and_industry_retrieval_do_not_share_loose_papers(monkeypatch):
    market_paper = work(
        "Fashion customers compare demand and competition across online retailers. "
        "Customer acquisition and retention influence repeat purchases.",
        title="Fashion demand and customer retention", doi="https://doi.org/10.1234/market",
    )
    industry_paper = work(
        "Fashion companies manage inventory and apparel returns across supply chains. "
        "Unsold stock, sizing and seasonal margins remain operational concerns.",
        title="Fashion inventory and apparel returns", doi="https://doi.org/10.1234/industry",
    )
    install_payload(monkeypatch, {"results": [market_paper, industry_paper]})

    market = evidence.retrieve(["Fashion"], "Market", focus="Market")
    industry = evidence.retrieve(["Fashion"], "Industry", focus="Industry")

    assert [paper["doi"] for paper in market] == [market_paper["doi"]]
    assert [paper["doi"] for paper in industry] == [industry_paper["doi"]]


def test_weak_or_unlisted_repository_results_are_filtered(monkeypatch):
    unrelated = work("This paper studies software terminology but says nothing about competition.", title="Software terminology", doi="https://doi.org/10.1234/unrelated")
    repository = work("Software startups face market competition.", doi="https://doi.org/10.1234/preprint", source_type="repository", listed=False)
    install_payload(monkeypatch, {"results": [unrelated, repository]})

    assert evidence.retrieve(["Software"], "Market") == []


def test_direct_and_contextual_abstract_sentences_are_labeled_separately():
    direct, is_direct = evidence._snippet(
        "Software startups face customer competition. Other details follow.", {"software"}, {"competition"})
    contextual, is_direct_2 = evidence._snippet(
        "Software teams choose their tools. Their market research discusses competition.", {"software"}, {"competition"})

    assert direct and is_direct
    assert contextual and not is_direct_2
    assert evidence._snippet("Software was measured. Competition is discussed.", {"software"}, {"competition"})[0] == "Competition is discussed."


def test_duplicate_dois_keep_one_best_candidate(monkeypatch):
    first = work("Software ventures study market competition and survival.", doi="https://doi.org/10.1234/same", date="2025-04-01")
    duplicate = work("Software ventures study market competition and survival. Additional competition analysis.", doi="https://doi.org/10.1234/same", date="2026-06-01")
    install_payload(monkeypatch, {"results": [first, duplicate]})

    found = evidence.retrieve(["Software"], "Market")

    assert len(found) == 1
    assert found[0]["published"] == "2026-06-01"


def test_future_dated_sources_are_discarded(monkeypatch):
    future = work("Software startups face market competition.", doi="https://doi.org/10.1234/future", date="2999-01-01")
    install_payload(monkeypatch, {"results": [future]})

    assert evidence.retrieve(["Software"], "Market") == []


def test_evidence_endpoint_uses_stage2_category_and_is_private(client, monkeypatch):
    body = {"title": "Fashion startup", "stage": "stage2", "input": {
        "category": "ecommerce", "funding_total_usd": 0, "funding_rounds": 1, "has_VC": False, "has_angel": False,
        "has_roundA": False, "has_roundB": False, "has_roundC": False, "has_roundD": False,
        "avg_participants": 0, "relationships": 0, "age_first_funding_year": 0, "age_last_funding_year": 0,
    }, "context": {"concept": "Fashion marketplace for young shoppers"}}
    aid = client.post("/v1/analyses", json=body, headers=headers_for(USER_A)).json()["id"]
    received = []
    source = {"title": "Market risk in software ventures", "publisher": "Journal", "url": "https://example.org/paper",
              "published": "2026-10-01", "venue_status": "DOAJ-listed journal", "excerpt": "Abstract sentence.",
              "matched_terms": ["software", "competition"], "relation": "direct", "focus": "Market"}

    def fake(tags, node, context, country, startup_name, focus, limit):
        received.append((tags, node, context, startup_name, focus, limit))
        return [source]

    monkeypatch.setattr(evidence, "retrieve", fake)
    response = client.get(f"/v1/analyses/{aid}/evidence?node=Industry&focus=Market", headers=headers_for(USER_A))
    other_user = client.get(f"/v1/analyses/{aid}/evidence?node=Industry&focus=Market", headers=headers_for(USER_B))

    assert response.status_code == 200 and response.json()["sources"][0]["relation"] == "direct"
    assert received == [(["ecommerce"], "Industry", {"concept": "Fashion marketplace for young shoppers"}, "Fashion startup", "Market", 8)]
    assert other_user.status_code == 404
