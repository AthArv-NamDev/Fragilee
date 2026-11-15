"""'Startups like yours' counts, and the founder's context (saved next to an analysis, never scored)."""
import json

import numpy as np
import pandas as pd
import pytest

from app import cohort
from app.cohort import MIN_N, CohortIndex, wilson
from conftest import USER_A, headers_for

COUNTRIES = ["USA", "GBR"]


def make_index(tmp_path, rows):
    p = tmp_path / "s1.csv"
    pd.DataFrame(rows, columns=["failed", "country", "state", "tags", "founded_year"]).to_csv(p, index=False)
    return CohortIndex(p, COUNTRIES)


def rows(n, closed, country, state, tags):
    return [[1 if i < closed else 0, country, state, tags, 2010] for i in range(n)]


# ---- unit: the maths and the slicing -------------------------------------------------
def test_wilson_range_contains_the_share_and_shrinks_with_more_data():
    lo, hi = wilson(30, 100)
    assert lo < 0.30 < hi
    lo2, hi2 = wilson(300, 1000)
    assert (hi2 - lo2) < (hi - lo)
    assert wilson(0, 0) == (0.0, 1.0)
    assert 0.0 <= wilson(0, 50)[0] and wilson(50, 50)[1] <= 1.0


def test_slices_count_the_right_startups(tmp_path):
    data = (rows(100, 40, "USA", "CA", "Software|Mobile") + rows(50, 10, "USA", "NY", "Software")
            + rows(60, 30, "GBR", "NONE", "Software") + rows(40, 20, "USA", "CA", "Biotechnology"))
    d = CohortIndex.describe(make_index(tmp_path, data), "USA", "CA", ["Software"])
    s = {x["key"]: x for x in d["slices"]}
    assert s["place_industry"]["n"] == 100 and s["place_industry"]["closed_share"] == 0.4
    assert s["place"]["n"] == 140                       # CA only: 100 + 40
    assert s["industry"]["n"] == 210                    # Software anywhere: 100 + 50 + 60
    assert d["overall"] == {"n": 250, "closed_share": 0.4}
    assert 0.3 < s["place_industry"]["low"] < 0.4 < s["place_industry"]["high"] < 0.5


def test_too_few_startups_gives_a_count_but_no_percentage(tmp_path):
    data = rows(MIN_N - 1, 10, "USA", "CA", "Software") + rows(200, 80, "GBR", "NONE", "Biotechnology")
    s = {x["key"]: x for x in make_index(tmp_path, data).describe("USA", "CA", ["Software"])["slices"]}
    assert s["place_industry"]["n"] == MIN_N - 1
    assert s["place_industry"]["enough"] is False
    assert s["place_industry"]["closed_share"] is None and s["place_industry"]["low"] is None


def test_small_state_falls_back_to_the_whole_country(tmp_path):
    data = rows(5, 2, "USA", "ND", "Software") + rows(100, 40, "USA", "CA", "Software")
    d = make_index(tmp_path, data).describe("USA", "ND", ["Software"])
    place = d["slices"][0]
    assert "based in the United States" in place["detail"] and place["n"] == 105


def test_unlisted_country_is_grouped_as_other(tmp_path):
    data = rows(40, 20, "JPN", "NONE", "Software") + rows(40, 10, "BRA", "NONE", "Software") + rows(100, 40, "USA", "CA", "Software")
    d = make_index(tmp_path, data).describe("JPN", None, ["Software"])
    assert d["slices"][1]["n"] == 80 and "other countries" in d["slices"][1]["detail"]


def test_wording_for_one_tag_and_for_many(tmp_path):
    idx = make_index(tmp_path, rows(100, 40, "USA", "CA", "Software|Mobile"))
    assert "in Software" in idx.describe("USA", "CA", ["Software"])["slices"][2]["detail"]
    assert "at least one of your industries" in idx.describe("USA", "CA", ["Software", "Mobile"])["slices"][2]["detail"]


def test_missing_data_file_turns_the_feature_off(tmp_path):
    assert cohort.load(tmp_path / "nope.csv", COUNTRIES) is None


def test_output_is_aggregate_only(tmp_path):
    d = make_index(tmp_path, rows(60, 30, "USA", "CA", "Software")).describe("USA", "CA", ["Software"])
    assert set(d) == {"basis", "overall", "slices", "note"}
    assert all(set(s) == {"key", "label", "detail", "n", "enough", "closed_share", "low", "high"} for s in d["slices"])


# ---- API: real data -----------------------------------------------------------------
S1 = {"country": "USA", "state": "CA", "tags": ["Software", "Mobile"]}


def test_counts_are_private_by_default(client):
    r = client.post("/v1/predict/stage1", json=S1).json()
    assert r["cohort"] is None
    assert "base_failure_rate" not in r


def test_stage1_response_has_real_cohort_numbers_when_switched_on(client, monkeypatch):
    from app import settings
    monkeypatch.setattr(settings, "EXPOSE_COHORT", True)
    r = client.post("/v1/predict/stage1", json=S1).json()
    c = r["cohort"]
    assert c["overall"]["n"] == 10941 and c["overall"]["closed_share"] == pytest.approx(0.391, abs=0.001)
    assert [s["key"] for s in c["slices"]] == ["place_industry", "place", "industry"]
    top = c["slices"][0]
    assert top["enough"] and top["low"] < top["closed_share"] < top["high"]
    assert top["n"] <= c["slices"][1]["n"] and top["n"] <= c["slices"][2]["n"]    # the narrowest slice is the smallest
    assert "do not change your risk band" in c["note"]


def test_stage2_has_no_cohort(client):
    from test_api import STAGE2_OK
    assert client.post("/v1/predict/stage2", json=STAGE2_OK).json()["cohort"] is None


# ---- API: the founder's context --------------------------------------------------------
CTX = {"concept": "  A coffee delivery app for offices ", "vision": "Every office in Europe", "customer": "Office managers",
       "revenue_model": "Subscription", "startup_stage": "prototype", "team_size": 3, "biggest_worry": "Cash"}


def create(client, ctx=None, **extra):
    body = {"title": "Coffee", "stage": "stage1", "input": S1, **extra}
    if ctx is not None:
        body["context"] = ctx
    return client.post("/v1/analyses", json=body, headers=headers_for(USER_A))


def test_context_is_saved_and_returned_trimmed(client):
    r = create(client, CTX)
    assert r.status_code == 201, r.text
    got = client.get(f"/v1/analyses/{r.json()['id']}", headers=headers_for(USER_A)).json()
    assert got["context"]["concept"] == "A coffee delivery app for offices"
    assert got["context"]["team_size"] == 3 and got["context"]["startup_stage"] == "prototype"


def test_context_never_changes_the_band_or_probability(client):
    with_ctx, without = create(client, CTX).json(), create(client).json()
    assert (with_ctx["band"], with_ctx["probability"]) == (without["band"], without["probability"])
    assert without["context"] is None


def test_blank_context_answers_are_dropped(client):
    r = create(client, {"concept": "Only this", "vision": "   ", "customer": ""})
    got = client.get(f"/v1/analyses/{r.json()['id']}", headers=headers_for(USER_A)).json()
    assert got["context"] == {"concept": "Only this"}


@pytest.mark.parametrize("bad", [
    {"concept": "x" * 801}, {"vision": "x" * 801}, {"customer": "x" * 201}, {"concept": "a\x00b"},
    {"startup_stage": "huge"}, {"team_size": 0}, {"team_size": 501}, {"surprise": "field"}, {"team_size": "many"}])
def test_bad_context_is_rejected(client, bad):
    assert create(client, bad).status_code == 422


def test_newlines_are_allowed_in_text(client):
    assert create(client, {"concept": "line one\nline two"}).status_code == 201


def test_largest_possible_context_fits_the_request_limit(client):
    emoji = "\U0001F600"
    ctx = {"concept": emoji * 800, "vision": emoji * 800, "customer": emoji * 200, "revenue_model": emoji * 200, "biggest_worry": emoji * 200}
    body = {"title": emoji * 80, "stage": "stage1", "input": S1, "context": ctx}
    assert len(json.dumps(body, ensure_ascii=False).encode()) < 16000
    assert client.post("/v1/analyses", json=body, headers=headers_for(USER_A)).status_code == 201


def test_other_users_cannot_read_my_context(client):
    from conftest import USER_B
    mine = create(client, CTX).json()["id"]
    assert client.get(f"/v1/analyses/{mine}", headers=headers_for(USER_B)).status_code == 404


def test_context_works_for_stage2_too(client):
    from test_api import STAGE2_OK
    r = client.post("/v1/analyses", headers=headers_for(USER_A),
                    json={"title": "Funded", "stage": "stage2", "input": STAGE2_OK, "context": {"concept": "x"}})
    assert r.status_code == 201
