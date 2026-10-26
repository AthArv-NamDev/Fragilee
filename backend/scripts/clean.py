"""Module 1, step 1: build the two training tables.

Run from the backend/ folder:
    python scripts/clean.py [raw_dir] [out_dir]        (defaults: data/raw  data/processed)

Inputs (in raw_dir):
    startup data.csv                    Kaggle 'Startup Success Prediction' (923 startups) -> Stage 2
    big_startup_secsees_dataset.csv     Kaggle 'Big Startup Success' (Crunchbase, 66k rows) -> Stage 1
Outputs (in out_dir):
    startup_clean.csv     Stage 2 training table
    stage1_clean.csv      Stage 1 training table
    column_decisions.csv  what happened to every original column, and why
    datasets.csv          a one-line card per dataset (source, label, limits)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "data/processed")
OUT.mkdir(parents=True, exist_ok=True)
SMALL, BIG = RAW / "startup data.csv", RAW / "big_startup_secsees_dataset.csv"


def check(condition, message):
    if not condition:
        sys.exit(f"DATA CHECK FAILED: {message}")


def group_rare(series, min_count, other):
    """Merge categories with fewer than min_count rows into one 'other' bucket."""
    counts = series.value_counts()
    return series.where(series.isin(counts[counts >= min_count].index), other)


D, CARDS = [], []  # column decisions, dataset cards


def add(dataset, cols, decision, used_as, reason):
    for c in cols.split(","):
        D.append((dataset, c.strip(), decision, used_as, reason))


# =============================== Stage 2 table ================================
small = pd.read_csv(SMALL)
rows_in = len(small)
small = small.drop_duplicates(subset="object_id").reset_index(drop=True)   # one startup appears twice
small["failed"] = (small["status"] == "closed").astype(int)
small["founded_year"] = pd.to_datetime(small["founded_at"], errors="coerce").dt.year
small["category"] = group_rare(small["category_code"], 10, "other")
small["state"] = group_rare(small["state_code"], 10, "OTHER")

STAGE2 = ["funding_total_usd", "funding_rounds", "has_VC", "has_angel", "has_roundA", "has_roundB",
          "has_roundC", "has_roundD", "avg_participants", "relationships",
          "age_first_funding_year", "age_last_funding_year"]
s2 = small[["failed", "category", "state", "founded_year"] + STAGE2]
check(set(s2["failed"]) == {0, 1}, "Stage 2 target must be 0/1")
check((s2["funding_total_usd"] >= 0).all(), "negative funding found")
check(s2[STAGE2].isna().sum().sum() == 0, "unexpected blanks in Stage 2 features")
s2.to_csv(OUT / "startup_clean.csv", index=False)

S = "Stage 2 (startup data.csv)"
add(S, "status", "target source", "failed", "closed = 1 (failure), acquired = 0. No IPO rows exist in this file.")
add(S, "labels", "dropped", "-", "Same information as status (acquired = 1), so it is the answer itself.")
add(S, "closed_at", "dropped (leak)", "-", "Filled for 326 closed and 9 acquired startups, so it gives away the outcome.")
add(S, "is_top500", "held out", "-", "Closed rate is 28% when 1 but 66% when 0. Looks like an after-the-fact flag. Adding it gave no AUC gain.")
add(S, "Unnamed: 0, id, object_id, name", "dropped", "-", "Identifiers. Not features.")
add(S, "Unnamed: 6, zip_code, city, latitude, longitude, state_code.1", "dropped", "-", "Too specific (near-identifiers) or duplicates of state_code.")
add(S, "state_code", "kept", "state", "Rare states (under 10 rows) merged into OTHER. Used by Stage 2.")
add(S, "category_code", "kept", "category", "Rare categories (under 10 rows) merged into other. Used by Stage 2.")
add(S, "founded_at", "kept as year (not a feature)", "founded_year", "Only used for the time-based check. As a feature it mostly measures time, not risk.")
add(S, "first_funding_at, last_funding_at", "dropped", "-", "Raw dates. The age_*_funding_year columns already hold this.")
add(S, "is_CA, is_NY, is_MA, is_TX, is_otherstate", "dropped", "-", "Duplicates of state.")
add(S, "is_software, is_web, is_mobile, is_enterprise, is_advertising, is_gamesvideo, is_ecommerce, is_biotech, is_consulting, is_othercategory",
    "dropped", "-", "Duplicates of category.")
add(S, "funding_total_usd, funding_rounds, has_VC, has_angel, has_roundA, has_roundB, has_roundC, has_roundD, avg_participants",
    "kept", "Stage 2 feature", "Funding signals. Only known once the startup has raised money.")
add(S, "relationships", "kept (caution)", "Stage 2 feature", "Strongest signal. It counts people linked to the company at snapshot time, so part of it may reflect success after the fact.")
add(S, "age_first_funding_year, age_last_funding_year", "kept", "Stage 2 feature", "Funding timing. A few negative values (funding dated before founding) are kept as-is.")
add(S, "milestones, age_first_milestone_year, age_last_milestone_year", "held out (leak risk)", "-",
    "Milestones can record the acquisition itself (e.g. 'X completes acquisition of Y'). Removing them cost only about 0.01 AUC.")
missing = set(pd.read_csv(SMALL, nrows=0).columns) - {c for d, c, *_ in D if d == S}
check(not missing, f"undocumented Stage 2 columns: {missing}")
CARDS.append(("Kaggle Startup Success Prediction", "startup data.csv", len(s2), "1 = closed, 0 = acquired",
              round(s2["failed"].mean(), 3), "Stage 2 (funding and traction)",
              "US only. 922 rows. Only startups with a final outcome. Snapshot counts (relationships) may reflect later success."))

# =============================== Stage 1 table ================================
if BIG.exists():
    big = pd.read_csv(BIG, low_memory=False, keep_default_na=False, na_values=[""])
    big = big.drop_duplicates(subset="permalink")
    big = big[big["status"].isin(["closed", "acquired", "ipo"])].copy()   # drop still-operating: outcome unknown
    big["failed"] = (big["status"] == "closed").astype(int)
    big["tags"] = big["category_list"].fillna("").str.split("|").map(
        lambda t: "|".join(x.strip() for x in t if x.strip()))
    big["country"] = big["country_code"].fillna("UNK")
    big["state"] = np.where(big["country"] == "USA", big["state_code"].fillna("UNK"), "NONE")
    year = pd.to_datetime(big["founded_at"], errors="coerce").dt.year
    big["founded_year"] = year.where(year.between(1990, 2014))
    big = big[big["tags"] != ""]                                         # no industry = nothing to describe the idea
    # The app always asks for country (and state for USA). Rows with these missing are dropped, so the
    # model cannot learn "poorly documented company" as a risk signal.
    n_before = len(big)
    big = big[(big["country"] != "UNK") & (big["state"] != "UNK")]
    print(f"Stage 1: dropped {n_before - len(big)} rows with unknown country or US state")
    s1 = big[["failed", "country", "state", "tags", "founded_year"]].reset_index(drop=True)
    check(set(s1["failed"]) == {0, 1}, "Stage 1 target must be 0/1")
    check(len(s1) > 5000, "Stage 1 table is unexpectedly small")
    s1.to_csv(OUT / "stage1_clean.csv", index=False)

    S = "Stage 1 (big_startup_secsees_dataset.csv)"
    add(S, "status", "target source", "failed", "closed = 1 (failure), acquired or ipo = 0. Still-operating companies are dropped because their outcome is unknown.")
    add(S, "category_list", "kept", "tags", "Industry tags separated by |. Top 150 tags become 0/1 features.")
    add(S, "country_code", "kept", "country", "Top 15 countries kept, others grouped as OTHER. Rows with no country are dropped (missing data was acting as a risk signal).")
    add(S, "state_code", "kept", "state", "Only for USA. Other countries get NONE.")
    add(S, "founded_at", "kept as year (not a feature)", "founded_year", "Only used for the time-based check (train on older startups, test on newer).")
    add(S, "permalink", "dropped", "-", "Identifier. Used only to remove duplicates.")
    add(S, "name, homepage_url", "dropped", "-", "Identifiers.")
    add(S, "region, city", "dropped", "-", "Too specific for an idea-stage input.")
    add(S, "funding_total_usd, funding_rounds, first_funding_at, last_funding_at", "held out", "-",
        "Funding is not known at idea stage. Stage 1 is meant for idea-only inputs.")
    CARDS.append(("Kaggle Big Startup Success (Crunchbase)", "big_startup_secsees_dataset.csv", len(s1), "1 = closed, 0 = acquired or IPO",
                  round(s1["failed"].mean(), 3), "Stage 1 (idea: industry tags, country, state)",
                  "Global but US-heavy, 2013-era. Only startups with a final outcome (operating ones excluded)."))
else:
    print(f"NOTE: {BIG.name} not found in {RAW}. Stage 1 table skipped.")

pd.DataFrame(D, columns=["dataset", "column", "decision", "used_as", "reason"]).to_csv(OUT / "column_decisions.csv", index=False)
pd.DataFrame(CARDS, columns=["dataset", "file", "rows_used", "label", "failure_share", "used_for", "limitations"]).to_csv(OUT / "datasets.csv", index=False)

print(f"Stage 2: rows in {rows_in} -> out {len(s2)} | failed share {s2['failed'].mean():.3f}")
if BIG.exists():
    print(f"Stage 1: rows out {len(s1)} | failed share {s1['failed'].mean():.3f}")
print("Wrote:", ", ".join(p.name for p in sorted(OUT.glob('*.csv'))))
