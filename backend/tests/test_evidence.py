import json
import uuid
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.error import URLError

from app import evidence
from app.auth import User
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
            "landing_page_url": f"https://example.org/{doi.rsplit('/', 1)[-1]}" if doi else "https://example.org/paper",
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
    article = work("Software startups face market competition, customer acquisition and retention challenges.")
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
    assert len(requests) == 3  # two first-window variants plus a wider-window retry for fewer than three distinct sources
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
    assert all("fashion" in query.casefold() and "india" in query.casefold() for query in market_queries[:-1] + industry_queries[:-1])
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


def test_weak_results_are_filtered_and_repository_peer_review_is_not_assumed(monkeypatch):
    unrelated = work("This paper studies software terminology but says nothing about competition.", title="Software terminology", doi="https://doi.org/10.1234/unrelated")
    repository = work("Software startups face market competition, customer acquisition and retention.", doi="https://doi.org/10.1234/preprint", source_type="repository", listed=False)
    install_payload(monkeypatch, {"results": [unrelated, repository]})

    found = evidence.retrieve(["Software"], "Market")
    assert len(found) == 1
    assert found[0]["venue_status"] == "Repository record; peer-review status unknown"
    assert found[0]["metadata_status"].startswith("OpenAlex record")
    assert found[0]["access_status"] == "abstract_only"


def test_generic_market_or_customer_overlap_is_not_enough_to_accept_a_paper(monkeypatch):
    generic = work(
        "Online marketplaces connect consumers. Customer adoption is discussed across digital services.",
        title="Consumers and online marketplaces",
        doi="https://doi.org/10.1234/generic",
    )
    install_payload(monkeypatch, {"results": [generic]})

    report = evidence.retrieve_detailed(["E-Commerce", "Marketplaces"], "Market", focus="Market")

    assert report["sources"] == []
    assert report["state"] == "weak_relevance"
    assert report["weak_candidates"] >= 1


def test_generic_technology_tag_cannot_admit_an_unrelated_fintech_paper(monkeypatch):
    fintech = work(
        "Financial technology platforms examine customer adoption and trust in digital finance.",
        title="Financial technology adoption in digital banking",
        doi="https://doi.org/10.1234/fintech",
    )
    install_payload(monkeypatch, {"results": [fintech]})

    report = evidence.retrieve_detailed(
        ["E-Commerce", "Marketplaces", "Clean Technology"], "Market", focus="Market",
    )

    assert report["sources"] == []
    assert report["state"] == "weak_relevance"


def test_direct_and_contextual_abstract_sentences_are_labeled_separately():
    direct, is_direct = evidence._snippet(
        "Software startups face customer competition. Other details follow.", {"software"}, {"competition"})
    contextual, is_direct_2 = evidence._snippet(
        "Software teams choose their tools. Their market research discusses competition.", {"software"}, {"competition"})

    assert direct and is_direct
    assert contextual and not is_direct_2
    assert evidence._snippet("Software was measured. Competition is discussed.", {"software"}, {"competition"})[0] == "Competition is discussed."


def test_duplicate_dois_keep_one_best_candidate(monkeypatch):
    first = work("Software ventures study market competition, customer acquisition and retention.", doi="https://doi.org/10.1234/same", date="2025-04-01")
    duplicate = work("Software ventures study market competition, customer acquisition and retention. Additional competition analysis.", doi="https://doi.org/10.1234/same", date="2026-06-01")
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
        return {"sources": [source], "state": "relevant_results", "queries_attempted": 1,
                "query_results": [{"query_index": 1, "state": "results", "records": 1, "accepted": 1}],
                "records_retrieved": 1, "candidates_filtered": 0, "weak_candidates": 0, "retrieved_at": "2026-11-15"}

    monkeypatch.setattr(evidence, "retrieve_detailed", fake)
    response = client.get(f"/v1/analyses/{aid}/evidence?node=Industry&focus=Market", headers=headers_for(USER_A))
    other_user = client.get(f"/v1/analyses/{aid}/evidence?node=Industry&focus=Market", headers=headers_for(USER_B))

    assert response.status_code == 200 and response.json()["sources"][0]["relation"] == "direct"
    assert response.json()["state"] == "relevant_results"
    assert response.json()["query_results"][0]["accepted"] == 1
    assert received == [(["ecommerce"], "Industry", {"concept": "Fashion marketplace for young shoppers"}, "Fashion startup", "Market", 8)]
    assert other_user.status_code == 404


def test_evidence_endpoint_reuses_snapshot_and_explicit_refresh_appends(client, monkeypatch):
    body = {"title": "Snapshot test", "stage": "stage2", "input": {
        "category": "ecommerce", "funding_total_usd": 0, "funding_rounds": 1, "has_VC": False, "has_angel": False,
        "has_roundA": False, "has_roundB": False, "has_roundC": False, "has_roundD": False,
        "avg_participants": 0, "relationships": 0, "age_first_funding_year": 0, "age_last_funding_year": 0,
    }}
    aid = client.post("/v1/analyses", json=body, headers=headers_for(USER_A)).json()["id"]
    calls = []

    def fake(*args):
        calls.append(1)
        n = len(calls)
        return {"sources": [], "state": "no_results", "queries_attempted": 1, "query_results": [],
                "records_retrieved": n, "candidates_filtered": 0, "weak_candidates": 0,
                "retrieved_at": f"2026-11-{n:02d}"}

    monkeypatch.setattr(evidence, "retrieve_detailed", fake)
    path = f"/v1/analyses/{aid}/evidence?node=Industry&focus=Market"
    first = client.get(path, headers=headers_for(USER_A)).json()
    again = client.get(path, headers=headers_for(USER_A)).json()
    calls_after_reuse = len(calls)
    refreshed = client.post(f"/v1/analyses/{aid}/evidence/refresh?node=Industry&focus=Market", headers=headers_for(USER_A)).json()
    latest = client.get(path, headers=headers_for(USER_A)).json()
    history_path = f"/v1/analyses/{aid}/evidence/history?node=Industry&focus=Market"
    history = client.get(history_path, headers=headers_for(USER_A)).json()["snapshots"]
    historical = client.get(f"/v1/analyses/{aid}/evidence/snapshots/{first['snapshot_id']}", headers=headers_for(USER_A)).json()
    other_history = client.get(history_path, headers=headers_for(USER_B))

    assert first["snapshot_saved"] is True and first["snapshot_id"]
    assert again["retrieved_at"] == first["retrieved_at"] and calls_after_reuse == 1
    assert refreshed["retrieved_at"] == "2026-11-02" and refreshed["snapshot_id"] != first["snapshot_id"]
    assert latest["snapshot_id"] == refreshed["snapshot_id"] and latest["retrieved_at"] == refreshed["retrieved_at"]
    assert history[0]["id"] == refreshed["snapshot_id"] and history[1]["id"] == first["snapshot_id"]
    assert historical["records_retrieved"] == 1 and historical["snapshot_id"] == first["snapshot_id"]
    assert other_history.status_code == 404
    snapshots = client.app.state.analyses._evidence_snapshots
    assert len([item for item in snapshots if item["analysis_id"] == aid]) == 2
    assert next(item for item in snapshots if item["id"] == first["snapshot_id"])["payload"]["records_retrieved"] == 1


def test_storage_failure_is_distinct_from_empty_research(client, monkeypatch):
    body = {"title": "Storage failure", "stage": "stage2", "input": {
        "category": "ecommerce", "funding_total_usd": 0, "funding_rounds": 1, "has_VC": False, "has_angel": False,
        "has_roundA": False, "has_roundB": False, "has_roundC": False, "has_roundD": False,
        "avg_participants": 0, "relationships": 0, "age_first_funding_year": 0, "age_last_funding_year": 0,
    }}
    aid = client.post("/v1/analyses", json=body, headers=headers_for(USER_A)).json()["id"]
    calls = []
    monkeypatch.setattr(evidence, "retrieve_detailed", lambda *_: (calls.append(1) or {"sources": [], "state": "no_results", "retrieved_at": "2026-11-16"}))
    monkeypatch.setattr(client.app.state.analyses, "get_latest_evidence_snapshot", lambda *_: (_ for _ in ()).throw(RuntimeError("database unavailable")))
    monkeypatch.setattr(client.app.state.analyses, "save_evidence_snapshot", lambda *_: (_ for _ in ()).throw(RuntimeError("database unavailable")))

    response = client.get(f"/v1/analyses/{aid}/evidence?node=Industry&focus=Market", headers=headers_for(USER_A))
    history = client.get(f"/v1/analyses/{aid}/evidence/history?node=Industry&focus=Market", headers=headers_for(USER_A))
    assert response.status_code == 200 and response.json()["state"] == "no_results"
    assert response.json()["snapshot_saved"] is False
    assert "could not be saved" in response.json()["snapshot_persistence_note"]
    assert history.status_code == 200 and history.json()["snapshots"] == []
    assert len(calls) == 1


def test_legacy_analysis_without_snapshots_still_loads_then_retrieves(client, monkeypatch):
    body = {"title": "Legacy-compatible report", "stage": "stage2", "input": {
        "category": "ecommerce", "funding_total_usd": 0, "funding_rounds": 1, "has_VC": False, "has_angel": False,
        "has_roundA": False, "has_roundB": False, "has_roundC": False, "has_roundD": False,
        "avg_participants": 0, "relationships": 0, "age_first_funding_year": 0, "age_last_funding_year": 0,
    }}
    aid = client.post("/v1/analyses", json=body, headers=headers_for(USER_A)).json()["id"]
    store = client.app.state.analyses
    assert store.list_evidence_snapshots(User(USER_A, "test"), uuid.UUID(aid), "Industry", "Market", 20) == []
    monkeypatch.setattr(evidence, "retrieve_detailed", lambda *_: {"sources": [], "state": "no_results", "retrieved_at": "2026-11-16"})

    legacy_report = client.get(f"/v1/analyses/{aid}", headers=headers_for(USER_A))
    evidence_report = client.get(f"/v1/analyses/{aid}/evidence?node=Industry&focus=Market", headers=headers_for(USER_A))
    assert legacy_report.status_code == 200 and "input" in legacy_report.json()
    assert evidence_report.json()["state"] == "no_results"
    assert evidence_report.json()["snapshot_saved"] is True


def test_snapshot_latest_order_is_deterministic_for_equal_timestamps(client):
    store = client.app.state.analyses
    user = User(USER_A, "test-token")
    body = {"title": "Tie order", "stage": "stage2", "input": {
        "category": "ecommerce", "funding_total_usd": 0, "funding_rounds": 1, "has_VC": False, "has_angel": False,
        "has_roundA": False, "has_roundB": False, "has_roundC": False, "has_roundD": False,
        "avg_participants": 0, "relationships": 0, "age_first_funding_year": 0, "age_last_funding_year": 0,
    }}
    analysis_id = client.post("/v1/analyses", json=body, headers=headers_for(USER_A)).json()["id"]
    a = store.save_evidence_snapshot(user, {"analysis_id": analysis_id, "node": "Industry", "focus": "Market", "payload": {"state": "partial"}})
    b = store.save_evidence_snapshot(user, {"analysis_id": analysis_id, "node": "Industry", "focus": "Market", "payload": {"state": "no_results"}})
    for row in store._evidence_snapshots:
        if row["id"] in (a["id"], b["id"]):
            row["created_at"] = "2026-11-16T00:00:00+00:00"
    assert store.get_latest_evidence_snapshot(user, uuid.UUID(analysis_id), "Industry", "Market")["id"] == max(a["id"], b["id"])


def test_duplicate_and_concurrent_snapshot_inserts_are_append_only(client):
    from concurrent.futures import ThreadPoolExecutor
    store = client.app.state.analyses
    user = User(USER_A, "test-token")
    body = {"title": "Concurrent writes", "stage": "stage2", "input": {
        "category": "ecommerce", "funding_total_usd": 0, "funding_rounds": 1, "has_VC": False, "has_angel": False,
        "has_roundA": False, "has_roundB": False, "has_roundC": False, "has_roundD": False,
        "avg_participants": 0, "relationships": 0, "age_first_funding_year": 0, "age_last_funding_year": 0,
    }}
    analysis_id = client.post("/v1/analyses", json=body, headers=headers_for(USER_A)).json()["id"]
    record = {"analysis_id": analysis_id, "node": "Industry", "focus": "Market", "payload": {"state": "partial"}}
    with ThreadPoolExecutor(max_workers=6) as executor:
        inserted = list(executor.map(lambda _: store.save_evidence_snapshot(user, record), range(6)))
    assert len({item["id"] for item in inserted}) == 6
    history = store.list_evidence_snapshots(user, uuid.UUID(analysis_id), "Industry", "Market", 20)
    latest = store.get_latest_evidence_snapshot(user, uuid.UUID(analysis_id), "Industry", "Market")
    assert len(history) == 6
    assert latest["id"] == history[0]["id"]


def test_profile_fields_expand_queries_without_metric_values_or_startup_name():
    context = {"profile": {
        "identity": {"business_model": "marketplace", "operating_geography": "India"},
        "customer_market": {"customer_description": "environmentally conscious shoppers", "metrics": [{"field_id": "customers", "value": 99}]},
        "business_model_details": {"kind": "marketplace", "buyer_group": "eco-conscious shoppers", "seller_group": "verified sustainable goods sellers"},
        "team_operations": {"critical_dependencies": "seller verification"},
    }}
    _, queries, _, _ = evidence.build_queries(["E-Commerce"], "Market", context, "IND", "EcoCart", "Market")
    joined = " ".join(queries).casefold()
    assert "marketplace" in joined and "shoppers" in joined and "verification" in joined
    assert "ecocart" not in joined and "99" not in joined
    assert 2 <= len(queries) <= 4


def test_refill_startup_gets_a_product_specific_query_for_each_research_lens():
    context = {
        "concept": "A refill subscription for concentrated household cleaning products in reusable bottles.",
        "customer": "Urban renters seeking lower-waste cleaning refills",
        "revenue_model": "Online starter kits plus recurring concentrate refill subscriptions",
        "profile": {"team_operations": {"metrics": [{"field_id": "team_size", "value": 2}]}},
    }
    _, market_queries, _, _ = evidence.build_queries(
        ["E-Commerce", "Consumer Goods", "Delivery"], "Market", context, "IND", "LoopCart", "Market",
    )
    _, industry_queries, _, _ = evidence.build_queries(
        ["E-Commerce", "Consumer Goods", "Delivery"], "Industry", context, "IND", "LoopCart", "Industry",
    )

    assert market_queries[-1] == "refill household consumer purchase willingness"
    assert industry_queries[-1] == "refill household packaging supply chain logistics"
    assert all("loopcart" not in query.casefold() and "2" not in query for query in market_queries + industry_queries)


def test_profile_specific_passage_admitted_and_generic_ecommerce_market_paper_rejected(monkeypatch):
    refill_research = work(
        "Consumers are looking for solutions to reduce waste at source. Selling products in bulk using reusable containers is an emerging path. "
        "A survey analyzed household purchasing preferences. Results indicate that most consumers do not appear to have a willingness to pay more for bulk household products with reusable packaging.",
        title="Consumer interest and willingness to pay for in-bulk products with reusable packaging options",
        doi="https://doi.org/10.3389/frsus.2023.1228917",
    )
    unrelated = work(
        "Consumers adopt online pharmacies for convenience and timely delivery. The study discusses purchase behavior, trust, and adoption in healthcare.",
        title="Consumer adoption and resistance of E-Pharmacy",
        doi="https://doi.org/10.1186/s12889-024-20265-7",
    )
    install_payload(monkeypatch, {"results": [refill_research, unrelated]})
    context = {
        "concept": "A refill subscription for concentrated household cleaning products in reusable bottles.",
        "customer": "Urban renters seeking lower-waste cleaning refills",
        "revenue_model": "Online starter kits plus recurring concentrate refill subscriptions",
    }

    report = evidence.retrieve_detailed(
        ["E-Commerce", "Consumer Goods", "Delivery"], "Market", context, "IND", "LoopCart", "Market",
    )

    assert [source["doi"] for source in report["sources"]] == ["https://doi.org/10.3389/frsus.2023.1228917"]
    assert report["sources"][0]["relation"] == "contextual"
    assert "willingness" in report["sources"][0]["excerpt"].casefold()


def test_relevant_negative_research_finding_is_preserved_as_a_passage():
    excerpt, direct = evidence._snippet(
        "Consumers found no willingness to pay more for reusable household packaging.",
        {"consumers"}, {"willingness", "purchase"}, {"reusable", "household"}, {"willingness"},
    )

    assert excerpt == "Consumers found no willingness to pay more for reusable household packaging."
    assert direct is True


def test_provider_failure_is_not_reported_as_no_research(monkeypatch):
    evidence._CACHE.clear()
    calls = []
    monkeypatch.setattr(evidence, "urlopen", lambda *_args, **_kwargs: (calls.append(1), (_ for _ in ()).throw(URLError("offline")))[1])
    report = evidence.retrieve_detailed(["Software"], "Market")
    assert report["sources"] == []
    assert report["state"] == "provider_unavailable"
    assert report["queries_attempted"] > 0
    calls_before_recovery = len(calls)
    article = work("Software startups face market competition, customer acquisition and retention.")
    recovered_calls = []
    def recover(request, timeout):
        recovered_calls.append(request)
        return Response(json.dumps({"results": [article]}).encode())
    monkeypatch.setattr(evidence, "urlopen", recover)
    recovered = evidence.retrieve_detailed(["Software"], "Market")
    assert len(calls) == calls_before_recovery and recovered_calls
    assert recovered["state"] == "relevant_results"


def test_provider_timeout_is_distinct_from_unavailable(monkeypatch):
    evidence._CACHE.clear()
    monkeypatch.setattr(evidence.time, "sleep", lambda *_args: None)
    monkeypatch.setattr(evidence, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError()))

    report = evidence.retrieve_detailed(["Software"], "Market")

    assert report["state"] == "provider_timeout"
    assert report["sources"] == []
    assert report["query_results"]
    assert {query["state"] for query in report["query_results"]} == {"provider_timeout"}


def test_rate_limit_is_distinct_from_generic_provider_error(monkeypatch):
    evidence._CACHE.clear()
    monkeypatch.setattr(evidence.time, "sleep", lambda *_args: None)

    def rate_limited(request, timeout):
        raise HTTPError(request.full_url, 429, "Too Many Requests", {"Retry-After": "0"}, None)

    monkeypatch.setattr(evidence, "urlopen", rate_limited)
    report = evidence.retrieve_detailed(["Software"], "Market")

    assert report["state"] == "rate_limited"
    assert report["sources"] == []
    assert report["query_results"]
    assert {query["state"] for query in report["query_results"]} == {"rate_limited"}


def test_successful_retry_is_not_mislabeled_as_partial(monkeypatch):
    article = work("Software startups face market competition, customer acquisition and retention.")
    calls = []
    def flaky(request, timeout):
        calls.append(request)
        if len(calls) == 1:
            raise URLError("temporary connection issue")
        return Response(json.dumps({"results": [article]}).encode())
    monkeypatch.setattr(evidence, "urlopen", flaky)
    evidence._CACHE.clear()
    report = evidence.retrieve_detailed(["Software"], "Market")
    assert len(calls) >= 2
    assert report["state"] == "relevant_results"


def test_empty_provider_results_are_distinct_from_filtered_results(monkeypatch):
    install_payload(monkeypatch, {"results": []})
    assert evidence.retrieve_detailed(["Software"], "Market")["state"] == "no_results"
    install_payload(monkeypatch, {"results": [work("The paper describes historical theatre participants.", title="Unrelated history")]})
    report = evidence.retrieve_detailed(["Software"], "Market")
    assert report["state"] == "filtered_out"
    assert report["records_retrieved"] > 0 and report["candidates_filtered"] > 0


def test_deduplicates_normalized_titles_when_doi_is_missing(monkeypatch):
    first = work("Software startups face market competition, customer acquisition and retention.", title="Software startups and market competition", doi=None)
    second = work("Software startups face market competition, customer acquisition and retention.", title="Software startups and market competition!", doi=None, date="2026-09-01")
    install_payload(monkeypatch, {"results": [first, second]})
    found = evidence.retrieve(["Software"], "Market")
    assert len(found) == 1


def test_invalid_doi_is_not_rendered_as_a_verified_citation(monkeypatch):
    record = work("Software startups face market competition, customer acquisition and retention.", doi="https://evil.example/10.1234/demo")
    install_payload(monkeypatch, {"results": [record]})
    found = evidence.retrieve(["Software"], "Market")
    assert len(found) == 1
    assert found[0]["doi"] is None
    assert found[0]["url"] == "https://example.org/demo"


def test_unsafe_source_urls_are_filtered(monkeypatch):
    record = work("Software startups face market competition, customer acquisition and retention.", doi=None)
    record["primary_location"]["landing_page_url"] = "javascript:alert(1)"
    record["id"] = ""
    install_payload(monkeypatch, {"results": [record]})
    assert evidence.retrieve(["Software"], "Market") == []


def test_pagination_is_bounded_and_counts_provider_pages(monkeypatch):
    candidate = work("Software startups face market competition, customer acquisition and retention.", doi="https://doi.org/10.1234/page")
    requests = []

    def fake(request, timeout):
        requests.append(request)
        query = parse_qs(urlparse(request.full_url).query)
        if query.get("cursor") == ["*"]:
            return Response(json.dumps({"results": [], "meta": {"next_cursor": "next"}}).encode())
        if query.get("cursor") == ["next"]:
            return Response(json.dumps({"results": [candidate]}).encode())
        return Response(json.dumps({"results": []}).encode())

    monkeypatch.setattr(evidence, "urlopen", fake)
    evidence._CACHE.clear()
    report = evidence.retrieve_detailed(["Software"], "Market")
    assert report["state"] == "relevant_results"
    assert report["records_retrieved"] == 1
    assert len(requests) <= 6


def test_provider_exception_is_failure_safe_in_report_endpoint(client, monkeypatch):
    aid = client.post("/v1/analyses", json={"title": "Software", "stage": "stage1",
        "input": {"country": "USA", "state": "CA", "tags": ["Software"]}}, headers=headers_for(USER_A)).json()["id"]
    def fail(*_args, **_kwargs):
        raise RuntimeError("provider response contents are not logged")
    monkeypatch.setattr(evidence, "retrieve_detailed", fail)
    response = client.get(f"/v1/analyses/{aid}/evidence?node=Industry", headers=headers_for(USER_A))
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "provider_error" and body["sources"] == []
    assert "returned an error" in body["note"].casefold()
