"""Feature and scoring code shared by training (scripts/train.py) and the API.

Keeping it in ONE place means the model always receives its input built the
same way it was trained on. Building it two different ways is a classic,
silent bug.
"""
import numpy as np
import pandas as pd

# ---- Stage 2 (funding + traction) -------------------------------------------
STAGE2_NUMERIC = [
    "funding_total_usd", "funding_rounds", "has_VC", "has_angel",
    "has_roundA", "has_roundB", "has_roundC", "has_roundD",
    "avg_participants", "relationships",
    "age_first_funding_year", "age_last_funding_year",
]


def build_stage2(df, numeric, categories, states):
    """Rows of startup details -> the numeric table the Stage 2 model reads."""
    out = df[numeric].astype(float).copy()
    for c in categories:
        out[f"category={c}"] = (df["category"] == c).astype(float)
    for s in states:
        out[f"state={s}"] = (df["state"] == s).astype(float)
    return out


# ---- Stage 1 (idea only: country, state, industry tags) ----------------------
def build_stage1(df, countries, states, tags):
    """Rows with country, state and tags ('Software|Mobile') -> the Stage 1 table.

    Anything outside the known lists falls into an OTHER bucket.
    """
    country = df["country"].where(df["country"].isin(countries), "OTHER")
    state = df["state"].where(df["state"].isin(states), "OTHER")
    tagsets = df["tags"].fillna("").map(lambda s: set(s.split("|")) if s else set())
    cols = {}
    for c in list(countries) + ["OTHER"]:
        cols[f"country={c}"] = (country == c).astype(float)
    for s_ in list(states) + ["OTHER"]:
        cols[f"state={s_}"] = (state == s_).astype(float)
    for t in tags:
        cols[f"tag={t}"] = tagsets.map(lambda ts, t=t: float(t in ts))
    cols["n_tags"] = tagsets.map(len).clip(upper=8).astype(float)
    return pd.DataFrame(cols, index=df.index)


def risk_group(feature: str) -> str:
    """Which risk-tree branch a model feature belongs to."""
    if feature.startswith(("country=", "state=")):
        return "Location"
    if feature.startswith(("category=", "tag=")) or feature == "n_tags":
        return "Market"
    if feature == "relationships":
        return "Traction"
    return "Funding"


# ---- calibration and risk bands ----------------------------------------------
BANDS = ["Low", "Medium", "High", "Critical"]


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def apply_platt(p_raw, a, b):
    """Turn the model's raw score into a calibrated probability (Platt scaling).

    a and b are two numbers stored in model_config.json. No pickle needed.
    """
    return 1.0 / (1.0 + np.exp(-(a * _logit(p_raw) + b)))


def assign_band(p, cutoffs):
    """cutoffs = three ascending probabilities separating the four bands."""
    return BANDS[int(np.searchsorted(cutoffs, p, side="right"))]


# ---- risk-tree branch severity ------------------------------------------------
# A branch's net SHAP push is in log-odds. Low = no push or lowers risk. 0.25 roughly
# multiplies the odds of closing by 1.3, and 0.75 by more than 2.
BRANCH_CUTOFFS = [0.05, 0.25, 0.75]


def branch_band(net_push: float) -> str:
    """How strongly one group of factors pushes the failure risk UP."""
    return assign_band(net_push, BRANCH_CUTOFFS)
