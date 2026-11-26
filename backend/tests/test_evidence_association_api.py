import uuid

from app.auth import User
from conftest import USER_A, USER_B, headers_for


def make_analysis(client, user_id=USER_A):
    body = {"title": "Evidence API test", "stage": "stage2", "input": {
        "category": "ecommerce", "funding_total_usd": 0, "funding_rounds": 1,
        "has_VC": False, "has_angel": False, "has_roundA": False,
        "has_roundB": False, "has_roundC": False, "has_roundD": False,
        "avg_participants": 0, "relationships": 0,
        "age_first_funding_year": 0, "age_last_funding_year": 0,
    }}
    return client.post("/v1/analyses", json=body, headers=headers_for(user_id)).json()["id"]


def make_snapshot(client, analysis_id, user_id=USER_A):
    source = {
        "title": "Research on retention",
        "publisher": "Example Journal", "journal": "Example Journal",
        "authors": ["A. Researcher"], "doi": "https://doi.org/10.1234/retention",
        "openalex_id": "https://openalex.org/W123", "url": "https://example.org/retention",
        "published": "2026-06-01", "year": "2026", "access_status": "abstract_only",
        "excerpt": "Customer retention varies among early-stage businesses.",
        "retrieved_at": "2026-11-16",
    }
    store = client.app.state.analyses
    snapshot = store.save_evidence_snapshot(User(user_id, "test-token"), {
        "analysis_id": analysis_id, "node": "Industry", "focus": "Market",
        "payload": {"provider": "OpenAlex", "sources": [source], "state": "relevant_results"},
    })
    return snapshot, source


def association_body(snapshot, source, **changes):
    body = {
        "snapshot_id": snapshot["id"],
        "claim_text": "Retention varies across early-stage businesses.",
        "claim_category": "general_research_finding",
        "source_id": source["openalex_id"],
        "source_access": "abstract_excerpt",
        "exact_passage_text": source["excerpt"],
        "passage_location": "Abstract",
        "source_url": source["url"],
        "publication": {key: source.get(key) for key in (
            "title", "url", "publisher", "journal", "authors", "doi", "published", "year")},
        "relationship": "supports",
        "limitations": ["Abstract excerpt only."],
    }
    body.update(changes)
    return body


def test_association_api_appends_pending_record_and_reads_by_analysis_snapshot(client):
    analysis_id = make_analysis(client)
    snapshot, source = make_snapshot(client, analysis_id)
    response = client.post(f"/v1/analyses/{analysis_id}/evidence/associations",
                           json=association_body(snapshot, source), headers=headers_for(USER_A))
    assert response.status_code == 201
    created = response.json()
    assert created["verification_state"] == "pending_review"
    assert created["verification_method"] == "none"
    assert created["reviewer_id"] is None
    listed = client.get(f"/v1/analyses/{analysis_id}/evidence/associations?snapshot_id={snapshot['id']}", headers=headers_for(USER_A))
    assert listed.status_code == 200
    assert listed.json()["associations"][0]["record_id"] == created["record_id"]
    fetched = client.get(f"/v1/analyses/{analysis_id}/evidence/associations/{created['record_id']}", headers=headers_for(USER_A))
    assert fetched.status_code == 200 and fetched.json()["record_id"] == created["record_id"]


def test_association_api_rejects_invalid_source_and_passage(client):
    analysis_id = make_analysis(client)
    snapshot, source = make_snapshot(client, analysis_id)
    invalid_source = association_body(snapshot, source, source_id="https://openalex.org/W-missing")
    response = client.post(f"/v1/analyses/{analysis_id}/evidence/associations", json=invalid_source, headers=headers_for(USER_A))
    assert response.status_code == 422
    invalid_passage = association_body(snapshot, source, exact_passage_text="A fabricated quote.")
    response = client.post(f"/v1/analyses/{analysis_id}/evidence/associations", json=invalid_passage, headers=headers_for(USER_A))
    assert response.status_code == 422


def test_research_snapshot_cannot_masquerade_as_historical_case_source(client):
    analysis_id = make_analysis(client)
    snapshot, source = make_snapshot(client, analysis_id)
    body = association_body(snapshot, source, claim_category="historical_case_fact")
    response = client.post(f"/v1/analyses/{analysis_id}/evidence/associations", json=body, headers=headers_for(USER_A))
    assert response.status_code == 422


def test_association_api_rejects_forged_review_identity_and_foreign_owner(client):
    analysis_id = make_analysis(client)
    snapshot, source = make_snapshot(client, analysis_id)
    forged = association_body(snapshot, source, reviewer_id=USER_B, verification_state="verified")
    assert client.post(f"/v1/analyses/{analysis_id}/evidence/associations", json=forged, headers=headers_for(USER_A)).status_code == 422
    denied = client.get(f"/v1/analyses/{analysis_id}/evidence/associations", headers=headers_for(USER_B))
    assert denied.status_code == 404


def test_review_appends_correction_derived_from_authenticated_user(client):
    analysis_id = make_analysis(client)
    snapshot, source = make_snapshot(client, analysis_id)
    created = client.post(f"/v1/analyses/{analysis_id}/evidence/associations",
                          json=association_body(snapshot, source), headers=headers_for(USER_A)).json()
    response = client.post(f"/v1/analyses/{analysis_id}/evidence/associations/{created['record_id']}/review",
                           json={"relationship": "partially_supports", "verification_state": "verified",
                                 "limitations": ["No startup-specific causal inference."]}, headers=headers_for(USER_A))
    assert response.status_code == 201
    corrected = response.json()
    assert corrected["record_id"] != created["record_id"]
    assert corrected["supersedes_record_id"] == created["record_id"]
    assert corrected["reviewer_id"] == USER_A
    assert corrected["verification_state"] == "verified"
    original = client.get(f"/v1/analyses/{analysis_id}/evidence/associations/{created['record_id']}", headers=headers_for(USER_A)).json()
    assert original["verification_state"] == "pending_review"
    assert original["is_current"] is False


def test_contradiction_candidate_requires_two_saved_passage_records_and_starts_pending(client):
    analysis_id = make_analysis(client)
    snapshot, source = make_snapshot(client, analysis_id)
    store = client.app.state.analyses
    second_source = {**source, "openalex_id": "https://openalex.org/W124", "doi": "https://doi.org/10.1234/other",
                     "url": "https://example.org/other", "title": "A contrasting retention paper",
                     "excerpt": "Retention differences were not observed in this sample."}
    snapshot = store.save_evidence_snapshot(User(USER_A, "test-token"), {
        "analysis_id": analysis_id, "node": "Industry", "focus": "Market",
        "payload": {"provider": "OpenAlex", "sources": [source, second_source], "state": "relevant_results"},
    })
    ids = []
    for src in (source, second_source):
        response = client.post(f"/v1/analyses/{analysis_id}/evidence/associations",
                               json=association_body(snapshot, src, relationship="contextualizes"), headers=headers_for(USER_A))
        assert response.status_code == 201
        ids.append(response.json()["record_id"])
    response = client.post(f"/v1/analyses/{analysis_id}/evidence/contradictions", json={
        "association_ids": ids, "nature": "insufficient_information",
        "assessment_text": "These abstracts may differ, but population and methods have not been compared.",
        "limitations": ["Abstract-based candidate only."],
    }, headers=headers_for(USER_A))
    assert response.status_code == 201
    assert response.json()["verification_state"] == "pending_review"
    assert response.json()["is_current"] is True
    duplicate = client.post(f"/v1/analyses/{analysis_id}/evidence/contradictions", json={
        "association_ids": ids, "nature": "insufficient_information",
        "assessment_text": "Duplicate manual comparison.",
        "limitations": [],
    }, headers=headers_for(USER_A))
    assert duplicate.status_code == 409

    reviewed = client.post(
        f"/v1/analyses/{analysis_id}/evidence/contradictions/{response.json()['record_id']}/review",
        json={"verification_state": "rejected", "nature": "complementary",
              "assessment_text": "The abstracts address different measures and are not contradictory.",
              "limitations": ["Only abstracts were compared."]}, headers=headers_for(USER_A),
    )
    assert reviewed.status_code == 201
    assert reviewed.json()["verification_state"] == "rejected"
    assert reviewed.json()["reviewer_id"] == USER_A
    records = client.get(f"/v1/analyses/{analysis_id}/evidence/contradictions", headers=headers_for(USER_A)).json()["assessments"]
    assert len(records) == 2
    assert records[0]["record_id"] != records[1]["record_id"]


def test_explicit_comparison_uses_exact_saved_passages_and_deduplicates_reversed_pair(client):
    analysis_id = make_analysis(client)
    first = {
        "title": "Retention and growth study", "publisher": "Journal", "journal": "Journal",
        "authors": ["A. Author"], "doi": "https://doi.org/10.1234/one",
        "openalex_id": "https://openalex.org/W1", "url": "https://example.org/one",
        "published": "2024-01-01", "year": "2024", "access_status": "abstract_only",
        "excerpt": "Customer retention has a positive relationship with revenue growth among fashion sellers.",
        "retrieved_at": "2026-11-16",
    }
    second = {**first, "title": "Retention and growth replication", "doi": "https://doi.org/10.1234/two",
              "openalex_id": "https://openalex.org/W2", "url": "https://example.org/two",
              "excerpt": "Customer retention has a negative relationship with revenue growth among fashion sellers."}
    store = client.app.state.analyses
    snapshot = store.save_evidence_snapshot(User(USER_A, "test-token"), {
        "analysis_id": analysis_id, "node": "Industry", "focus": "Market",
        "payload": {"provider": "OpenAlex", "sources": [first, second], "state": "relevant_results"},
    })
    association_ids = []
    for source in (first, second):
        linked = client.post(
            f"/v1/analyses/{analysis_id}/evidence/associations",
            json=association_body(snapshot, source, relationship="contextualizes"),
            headers=headers_for(USER_A),
        )
        assert linked.status_code == 201
        association_ids.append(linked.json()["record_id"])

    path = f"/v1/analyses/{analysis_id}/evidence/contradictions/compare"
    compared = client.post(path, json={"association_ids": association_ids}, headers=headers_for(USER_A))
    assert compared.status_code == 200
    candidate = compared.json()
    assert candidate["relationship"] == "contradicts"
    assert candidate["verification_state"] == "pending_review"
    assert candidate["verification_method"] == "none"
    assert candidate["detection_method"] == "deterministic_excerpt_rules"
    assert candidate["compared_evidence"][0]["exact_passage_text"] == first["excerpt"]
    assert candidate["compared_evidence"][1]["exact_passage_text"] == second["excerpt"]
    saved_snapshot = store.get_evidence_snapshot(User(USER_A, "test-token"), uuid.UUID(analysis_id), uuid.UUID(snapshot["id"]))

    repeated_same_order = client.post(path, json={"association_ids": association_ids}, headers=headers_for(USER_A))
    assert repeated_same_order.status_code == 200
    assert repeated_same_order.json()["record_id"] == candidate["record_id"]
    assert repeated_same_order.json()["reused_existing"] is True
    repeated_reversed = client.post(path, json={"association_ids": list(reversed(association_ids))}, headers=headers_for(USER_A))
    assert repeated_reversed.status_code == 200
    assert repeated_reversed.json()["record_id"] == candidate["record_id"]
    assert repeated_reversed.json()["reused_existing"] is True
    assert len([row for row in store._contradiction_assessments if row["analysis_id"] == analysis_id]) == 1
    assert store.get_evidence_snapshot(User(USER_A, "test-token"), uuid.UUID(analysis_id), uuid.UUID(snapshot["id"])) == saved_snapshot

    forged_review = client.post(
        f"/v1/analyses/{analysis_id}/evidence/contradictions/{candidate['record_id']}/review",
        json={"verification_state": "verified", "nature": "genuine_disagreement",
              "relationship": "contradicts", "assessment_text": "Forged reviewer.",
              "reviewer_id": USER_B, "limitations": []},
        headers=headers_for(USER_A),
    )
    assert forged_review.status_code == 422

    reviewed = client.post(
        f"/v1/analyses/{analysis_id}/evidence/contradictions/{candidate['record_id']}/review",
        json={"verification_state": "verified", "nature": "insufficient_information",
              "relationship": "insufficient", "assessment_text": "Human review found that context is missing.",
              "reviewer_explanation": "The excerpts do not state equivalent measures or sample details.",
              "limitations": ["Abstract excerpts only."]},
        headers=headers_for(USER_A),
    )
    assert reviewed.status_code == 201
    assert reviewed.json()["relationship"] == "insufficient"
    assert reviewed.json()["reviewer_id"] == USER_A
    comparison_after_review = client.post(
        path, json={"association_ids": list(reversed(association_ids))}, headers=headers_for(USER_A),
    )
    assert comparison_after_review.status_code == 200
    assert comparison_after_review.json()["record_id"] == reviewed.json()["record_id"]
    assert comparison_after_review.json()["reused_existing"] is True
    assert comparison_after_review.json()["is_current"] is True
    original = client.get(
        f"/v1/analyses/{analysis_id}/evidence/contradictions",
        headers=headers_for(USER_A),
    ).json()["assessments"]
    original = [row for row in original if row["analysis_id"] == analysis_id]
    assert len(original) == 2
    assert original[0]["reviewer_explanation"] == "The excerpts do not state equivalent measures or sample details."
    assert original[1]["verification_state"] == "pending_review"


def test_comparison_pair_deduplication_is_scoped_to_its_analysis(client):
    store = client.app.state.analyses
    records_by_analysis = {}
    for suffix in ("one", "two"):
        analysis_id = make_analysis(client)
        first = {
            "title": f"Retention study {suffix}", "publisher": "Journal", "journal": "Journal",
            "authors": ["A. Author"], "doi": f"https://doi.org/10.1234/{suffix}-one",
            "openalex_id": f"https://openalex.org/W-{suffix}-one", "url": f"https://example.org/{suffix}-one",
            "published": "2024-01-01", "year": "2024", "access_status": "abstract_only",
            "excerpt": "Customer retention has a positive relationship with revenue growth among sellers.",
            "retrieved_at": "2026-11-16",
        }
        second = {
            **first, "title": f"Retention study {suffix} replication",
            "doi": f"https://doi.org/10.1234/{suffix}-two",
            "openalex_id": f"https://openalex.org/W-{suffix}-two",
            "url": f"https://example.org/{suffix}-two",
            "excerpt": "Customer retention has a negative relationship with revenue growth among sellers.",
        }
        snapshot = store.save_evidence_snapshot(User(USER_A, "test-token"), {
            "analysis_id": analysis_id, "node": "Industry", "focus": "Market",
            "payload": {"provider": "OpenAlex", "sources": [first, second], "state": "relevant_results"},
        })
        association_ids = []
        for source in (first, second):
            linked = client.post(
                f"/v1/analyses/{analysis_id}/evidence/associations",
                json=association_body(snapshot, source, relationship="contextualizes"),
                headers=headers_for(USER_A),
            )
            assert linked.status_code == 201
            association_ids.append(linked.json()["record_id"])
        compared = client.post(
            f"/v1/analyses/{analysis_id}/evidence/contradictions/compare",
            json={"association_ids": association_ids}, headers=headers_for(USER_A),
        )
        assert compared.status_code == 200
        records_by_analysis[analysis_id] = compared.json()["record_id"]

    assert records_by_analysis[next(iter(records_by_analysis))] != records_by_analysis[next(reversed(records_by_analysis))]
    for analysis_id, record_id in records_by_analysis.items():
        history = client.get(
            f"/v1/analyses/{analysis_id}/evidence/contradictions", headers=headers_for(USER_A),
        )
        assert history.status_code == 200
        assert [item["record_id"] for item in history.json()["assessments"]] == [record_id]


def test_automatic_comparison_rejects_cross_user_and_missing_association_references(client):
    analysis_id = make_analysis(client)
    response = client.post(
        f"/v1/analyses/{analysis_id}/evidence/contradictions/compare",
        json={"association_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
        headers=headers_for(USER_B),
    )
    assert response.status_code == 404


def test_automatic_comparison_cannot_reference_association_from_another_analysis(client):
    analysis_id = make_analysis(client)
    foreign_analysis_id = make_analysis(client)
    foreign_snapshot, foreign_source = make_snapshot(client, foreign_analysis_id)
    foreign_link = client.post(
        f"/v1/analyses/{foreign_analysis_id}/evidence/associations",
        json=association_body(foreign_snapshot, foreign_source), headers=headers_for(USER_A),
    ).json()
    response = client.post(
        f"/v1/analyses/{analysis_id}/evidence/contradictions/compare",
        json={"association_ids": [foreign_link["record_id"], str(uuid.uuid4())]},
        headers=headers_for(USER_A),
    )
    assert response.status_code == 404


def test_snapshot_scan_detects_appends_and_deduplicates_only_after_explicit_action(client):
    analysis_id = make_analysis(client)
    store = client.app.state.analyses
    sources = [
        {"title": "First retention paper", "publisher": "Journal", "journal": "Journal",
         "authors": ["A. Author"], "doi": "https://doi.org/10.1234/first",
         "openalex_id": "https://openalex.org/W901", "url": "https://example.org/first",
         "published": "2024-01-01", "year": "2024", "access_status": "abstract_only",
         "excerpt": "Customer retention has a positive relationship with revenue growth among fashion sellers.",
         "retrieved_at": "2026-11-16"},
        {"title": "Second retention paper", "publisher": "Journal", "journal": "Journal",
         "authors": ["B. Author"], "doi": "https://doi.org/10.1234/second",
         "openalex_id": "https://openalex.org/W902", "url": "https://example.org/second",
         "published": "2025-01-01", "year": "2025", "access_status": "abstract_only",
         "excerpt": "Customer retention has a negative relationship with revenue growth among fashion sellers.",
         "retrieved_at": "2026-11-17"},
    ]
    snapshots = []
    for source in sources:
        snapshot = store.save_evidence_snapshot(User(USER_A, "test-token"), {
            "analysis_id": analysis_id, "node": "Industry", "focus": "Market",
            "payload": {"provider": "OpenAlex", "sources": [source], "state": "relevant_results"},
        })
        snapshots.append(snapshot)
        linked = client.post(
            f"/v1/analyses/{analysis_id}/evidence/associations",
            json=association_body(snapshot, source, relationship="contextualizes"),
            headers=headers_for(USER_A),
        )
        assert linked.status_code == 201

    history_path = f"/v1/analyses/{analysis_id}/evidence/contradictions"
    assert client.get(history_path, headers=headers_for(USER_A)).json()["assessments"] == []
    scan_path = f"/v1/analyses/{analysis_id}/evidence/contradictions/detect"
    first_scan = client.post(scan_path, json={"snapshot_id": snapshots[1]["id"]}, headers=headers_for(USER_A))
    assert first_scan.status_code == 200
    assert first_scan.json()["state"] == "complete"
    assert first_scan.json()["created"] == 1, first_scan.json()
    assert first_scan.json()["scanned_pairs"] == 1
    records = client.get(history_path, headers=headers_for(USER_A)).json()["assessments"]
    assert len(records) == 1
    candidate = records[0]
    assert candidate["relationship"] == "contradicts"
    assert candidate["verification_state"] == "pending_review"
    assert {passage["snapshot_id"] for passage in candidate["compared_evidence"]} == {item["id"] for item in snapshots}

    old_snapshot = store.get_evidence_snapshot(User(USER_A, "test-token"), uuid.UUID(analysis_id), uuid.UUID(snapshots[0]["id"]))
    repeat_scan = client.post(scan_path, json={"snapshot_id": snapshots[1]["id"]}, headers=headers_for(USER_A))
    assert repeat_scan.status_code == 200
    assert repeat_scan.json()["created"] == 0
    assert repeat_scan.json()["reused_existing"] == 1
    assert len(client.get(history_path, headers=headers_for(USER_A)).json()["assessments"]) == 1
    assert store.get_evidence_snapshot(User(USER_A, "test-token"), uuid.UUID(analysis_id), uuid.UUID(snapshots[0]["id"])) == old_snapshot


def test_automatic_comparison_requires_two_distinct_associations(client):
    analysis_id = make_analysis(client)
    record_id = str(uuid.uuid4())
    response = client.post(
        f"/v1/analyses/{analysis_id}/evidence/contradictions/compare",
        json={"association_ids": [record_id, record_id]},
        headers=headers_for(USER_A),
    )
    assert response.status_code == 422

def test_anonymous_association_read_is_rejected(client, anon_client):
    analysis_id = make_analysis(client)
    snapshot, source = make_snapshot(client, analysis_id)
    root = f"/v1/analyses/{analysis_id}/evidence"
    assert anon_client.get(f"{root}/associations").status_code == 401
    assert anon_client.get(f"{root}/contradictions").status_code == 401
    assert anon_client.post(
        f"{root}/associations", json=association_body(snapshot, source),
    ).status_code == 401
    pair = [str(uuid.uuid4()), str(uuid.uuid4())]
    assert anon_client.post(
        f"{root}/contradictions/compare", json={"association_ids": pair},
    ).status_code == 401
    assert anon_client.post(
        f"{root}/contradictions", json={
            "association_ids": pair, "nature": "insufficient_information",
            "assessment_text": "Unauthenticated request must be rejected before record validation.",
        },
    ).status_code == 401
    assert anon_client.post(
        f"{root}/contradictions/detect", json={"snapshot_id": snapshot["id"]},
    ).status_code == 401


def test_snapshot_from_another_analysis_is_not_accepted(client):
    analysis_id = make_analysis(client)
    other_analysis_id = make_analysis(client)
    snapshot, source = make_snapshot(client, other_analysis_id)
    response = client.post(f"/v1/analyses/{analysis_id}/evidence/associations",
                           json=association_body(snapshot, source), headers=headers_for(USER_A))
    assert response.status_code == 404
