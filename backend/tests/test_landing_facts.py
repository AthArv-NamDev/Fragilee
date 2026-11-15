"""Every number on the landing page must come from the real data. If the data or the page changes, this fails."""
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
PAGE_DATA = ROOT / "lib" / "landing-data.ts"
CSV = ROOT / "backend" / "data" / "processed" / "stage1_clean.csv"
CONFIG = ROOT / "backend" / "models" / "model_config.json"
pytestmark = pytest.mark.skipif(not (PAGE_DATA.exists() and CSV.exists()), reason="frontend or data not present (e.g. in the API image)")
MIN_N = 150          # an industry needs this many startups before we quote a percentage for it


def block(name: str):
    text = PAGE_DATA.read_text().split(f"export const {name} = ")[1]
    return json.loads(text.split(";\n")[0])


@pytest.fixture(scope="module")
def shares():
    d = pd.read_csv(CSV)
    model = set(json.loads(CONFIG.read_text())["stages"]["stage1"]["tags"])
    c, k = Counter(), Counter()
    for tags, failed in zip(d["tags"].fillna(""), d["failed"]):
        for t in filter(None, tags.split("|")):
            if t in model:
                c[t] += 1
                k[t] += failed
    return {t: round(100 * k[t] / c[t]) for t in c if c[t] >= MIN_N}, c


def test_every_industry_percentage_matches_the_data(shares):
    pct, _ = shares
    for p in block("PAIRS"):
        assert pct[p["low"]] == p["lowPct"] and pct[p["high"]] == p["highPct"], p
        assert p["lowPct"] < p["highPct"]


def test_extremes_are_really_the_extremes(shares):
    pct, _ = shares
    e = block("EXTREMES")
    assert e["low"]["pct"] == min(pct.values()) == pct[e["low"]["tag"]]
    assert e["high"]["pct"] == max(pct.values()) == pct[e["high"]["tag"]]
    assert e["gap"] == e["high"]["pct"] - e["low"]["pct"]


def test_product_facts_are_true():
    cfg = json.loads(CONFIG.read_text())["stages"]["stage1"]["tags"]
    stats = {s["label"]: s["value"] for s in json.loads(PAGE_DATA.read_text().split("export const STATS = ")[1].split(";\n")[0].replace("value:", '"value":').replace("label:", '"label":').replace(",\n  }", "\n  }").replace(",\n]", "\n]"))}
    assert stats["industries understood"] == str(len(cfg))


def test_five_industries_per_idea_is_the_real_limit(client):
    tags = ["Software", "Mobile", "Games", "Music", "Media", "Video"]
    ok = client.post("/v1/predict/stage1", json={"country": "USA", "state": "CA", "tags": tags[:5]})
    too_many = client.post("/v1/predict/stage1", json={"country": "USA", "state": "CA", "tags": tags})
    assert ok.status_code == 200 and too_many.status_code == 422


def test_every_industry_tag_on_the_page_is_one_the_model_understands(shares):
    _, counts = shares
    cfg = set(json.loads(CONFIG.read_text())["stages"]["stage1"]["tags"])
    shown = block("TAGS")
    assert len(shown) == 48 and set(shown) <= cfg
    assert shown == [t for t, _ in counts.most_common()][:48]    # most common first


def test_the_page_never_names_the_data():
    page = PAGE_DATA.read_text()
    for secret in ("2013", "10,941", "922", "American", "Crunchbase", "AUC"):
        assert secret not in page, f"landing-data.ts mentions {secret}"
