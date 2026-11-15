"""Turns a validated request into: probability, risk band and a risk tree built from SHAP."""
import pandas as pd

from .features import BANDS, apply_platt, assign_band, build_stage1, build_stage2, risk_group
from .model_store import ModelStore
from .schemas import Stage1Request, Stage2Request


class InputError(ValueError):
    """A request that is well-formed but not something the model can use."""
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field, self.message = field, message


class StageUnavailable(RuntimeError):
    pass


FACTOR_LABELS = {
    "funding_total_usd": "Total funding raised (USD)",
    "funding_rounds": "Number of funding rounds",
    "has_VC": "Venture capital funding",
    "has_angel": "Angel funding",
    "has_roundA": "Reached Series A", "has_roundB": "Reached Series B",
    "has_roundC": "Reached Series C", "has_roundD": "Reached Series D",
    "avg_participants": "Average investors per funding round",
    "relationships": "Business relationships (people linked to the company)",
    "age_first_funding_year": "Years from founding to first funding",
    "age_last_funding_year": "Years from founding to latest funding",
    "n_tags": "Number of industry tags",
}
GROUP_LABELS = {"Funding": "Funding", "Traction": "Traction", "Industry": "Industry", "Location": "Location"}
BENCHMARKS = {"stage1": "Historical startup data", "stage2": "Historical startup data"}   # deliberately vague: the details of our data stay private
DISCLAIMER = ("This shows patterns in historical startup data. It is not a prediction of your startup's future "
              "and not financial or legal advice.")


def label_for(feature: str) -> str:
    if feature in FACTOR_LABELS:
        return FACTOR_LABELS[feature]
    kind, _, val = feature.partition("=")
    return {"country": "Country", "state": "State", "tag": "Industry", "category": "Industry"}.get(kind, kind) + f": {val}"


def display_value(feature: str, value: float):
    if feature.startswith("has_"):
        return "Yes" if value >= 0.5 else "No"
    if "=" in feature:
        return "Yes"
    if feature == "funding_total_usd":
        return f"${value:,.0f}"
    v = float(value)
    return int(v) if v.is_integer() else round(v, 2)       # 2.0 -> 2, but 2.5 stays 2.5


def _stage(store: ModelStore, name: str):
    sm = store.stages.get(name)
    if sm is None:
        raise StageUnavailable(f"{name} is not available")
    return sm


def _explain(sm, X, sv):
    values = X[sm.features].iloc[0]
    total = float(abs(sv).sum()) or 1.0
    groups: dict = {}
    for f, v, s in zip(sm.features, values, sv):
        g = groups.setdefault(risk_group(f), {"net": 0.0, "factors": []})
        g["net"] += float(s)
        is_flag = f.startswith(("country=", "state=", "tag=", "category="))
        # list a factor only if it applies to this startup (an unticked tag is not a "reason")
        if abs(s) >= 0.01 and (not is_flag or v == 1):
            g["factors"].append((abs(float(s)), f, v, float(s)))
    branches = []
    for name, g in groups.items():
        net = g["net"]
        top = sorted(g["factors"], reverse=True)[:3]
        branches.append({
            "group": name, "label": GROUP_LABELS[name], "band": None,
            "effect": "neutral" if net == 0 else ("raises" if net > 0 else "lowers"),
            "net_shap": round(net, 3),
            "factors": [{"feature": f, "label": label_for(f), "value": display_value(f, v), "contribution": round(s, 3),
                         "effect": "raises risk" if s > 0 else "lowers risk",
                         "impact": round(a / total, 3)} for a, f, v, s in top],
        })
    return sorted(branches, key=lambda b: b["net_shap"], reverse=True)


def _predict(store, stage, X, notes, limitations):
    sm = _stage(store, stage)
    p_raw, sv = sm.score(X)
    cal = sm.entry["calibration"]
    p = float(apply_platt(p_raw, cal["a"], cal["b"]))
    band = assign_band(p, sm.entry["band_cutoffs"])
    return {
        "stage": stage, "probability": round(p, 2), "band": band,
        "similar_startups_failure_rate": sm.entry["band_observed_failure_rate"][band], "confidence": None,
        "benchmark": BENCHMARKS[stage],
        "tree": {"label": f"Failure risk: {band}", "band": band, "probability": round(p, 2),
                 "children": _explain(sm, X, sv)},
        "notes": notes, "limitations": limitations, "disclaimer": DISCLAIMER,
    }


def predict_stage1(store: ModelStore, req: Stage1Request) -> dict:
    sm = _stage(store, "stage1")
    e = sm.entry
    unknown = [t for t in req.tags if t not in e["tags"]]
    if unknown:
        raise InputError("tags", f"Unknown industry tag(s): {', '.join(unknown)}. Use the list from /v1/meta.")
    row = pd.DataFrame([{"country": req.country, "state": req.state or "NONE", "tags": "|".join(req.tags)}])
    X = build_stage1(row, e["countries"], e["states"], e["tags"])
    notes = []
    if req.country not in e["countries"]:
        notes.append("Your country is grouped with 'other countries' because the data has few startups from it.")
    limits = ["Uses only industry and place, so it tells startups apart only modestly. It shows which kinds of startups closed more often, not what will happen to yours.",
              "Based on historical startup data, so it can miss recent shifts in the market and may fit some regions better than others."]
    return _predict(store, "stage1", X, notes, limits)


def predict_stage2(store: ModelStore, req: Stage2Request) -> dict:
    sm = _stage(store, "stage2")
    e = sm.entry
    if req.category not in e["categories"]:
        raise InputError("category", f"Unknown category '{req.category}'. Use the list from /v1/meta.")
    state = req.state if req.state in e["states"] else "OTHER"
    row = pd.DataFrame([{**req.model_dump(), "state": state}])
    X = build_stage2(row, e["numeric"], e["categories"], e["states"])
    notes = []
    for f in e["numeric"]:
        r = e["ranges"][f]
        v = float(row[f].iloc[0])
        if v < r["min"] or v > r["max"]:
            notes.append(f"{label_for(f)} is outside the range this model was trained on "
                         f"({r['min']:,.4g} to {r['max']:,.4g}). Treat the result with extra caution.")
    if req.state not in (state, "OTHER"):
        notes.append("Your state is grouped with 'other states' because the data has few startups from it.")
    limits = ["A rough guide built from a modest sample. It separates closed from acquired startups clearly better than chance, but it still gets many individual startups wrong.",
              "Business relationships is the strongest signal, and part of it may reflect success after the fact.",
              "Based on historical startup data, so it can miss recent shifts in the market and may fit some regions better than others."]
    return _predict(store, "stage2", X, notes, limits)


def meta(store: ModelStore) -> dict:
    """What the forms need and nothing else: no accuracy figures, sizes or rates. Those stay private."""
    out = {"bands": BANDS, "stages": {}}
    for name, e in store.config["stages"].items():
        item = {"available": name in store.stages}
        if name == "stage1":
            item["inputs"] = {"countries": e["countries"], "states": [s for s in e["states"] if s != "NONE"], "tags": e["tags"],
                              "notes": "Any other country is accepted and grouped as 'other'."}
        else:
            item["inputs"] = {"categories": e["categories"], "states": e["states"]}
        out["stages"][name] = item
    return out
