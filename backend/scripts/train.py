"""Module 1, step 2: train, tune, calibrate, test and export the Fragilee models.

Run from the backend/ folder:   python scripts/train.py
Needs data/processed/*.csv (made by scripts/clean.py). Takes a few minutes.

For each stage (Stage 1 = idea only, Stage 2 = funding + traction):
  1. Hold out 20% of rows as a final test set (touched once, at the end).
  2. Compare Logistic Regression, Random Forest and XGBoost with cross-validation.
  3. Tune XGBoost with a random search (the imbalance weight is one of the settings).
  4. Calibrate the scores (Platt scaling) and cut them into four risk bands.
  5. Test on the held-out rows: AUC with a 95% confidence interval, Brier score,
     observed failure rate per band, and a time-based check (train old, test new).
  6. Ablation: how much does each group of inputs matter?
  7. Retrain on all rows, save as .json (never pickle) plus model_config.json.
A stage whose cross-validated AUC is below MIN_USABLE_AUC is not exported.
"""
import hashlib
import json
import sys
import warnings
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import (RandomizedSearchCV, RepeatedStratifiedKFold, StratifiedKFold,
                                     cross_val_predict, cross_val_score, cross_validate, train_test_split)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.features import (BANDS, STAGE2_NUMERIC, apply_platt, assign_band, build_stage1,  # noqa: E402
                          build_stage2, risk_group)

SEED = 42
MIN_USABLE_AUC = 0.65   # a stage below this in cross-validation is not trusted
DATA, MODELS, REPORTS = ROOT / "data/processed", ROOT / "models", ROOT / "reports"
MODELS.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)
XGB_BASE = dict(eval_metric="logloss", random_state=SEED, n_jobs=1, tree_method="hist",
                n_estimators=250, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8)


# ------------------------------- loading ---------------------------------------
def read(name):
    return pd.read_csv(DATA / name, keep_default_na=False, na_values=[""])


def load_stage2():
    df = read("startup_clean.csv")
    meta = {"numeric": STAGE2_NUMERIC, "categories": sorted(df["category"].unique()),
            "states": sorted(df["state"].unique())}
    return df, build_stage2(df, meta["numeric"], meta["categories"], meta["states"]), meta


def load_stage1():
    df = read("stage1_clean.csv")
    tag_counts = Counter(t for s in df["tags"] for t in s.split("|"))
    meta = {"countries": list(df["country"].value_counts().head(15).index),
            "states": list(df["state"].value_counts().head(16).index),
            "tags": [t for t, n in tag_counts.most_common(150) if n >= 30]}
    return df, build_stage1(df, meta["countries"], meta["states"], meta["tags"]), meta


SPECS = {
    "stage1": dict(load=load_stage1, repeats=1, tune_iter=12, tune_cv=3, rf_trees=100),
    "stage2": dict(load=load_stage2, repeats=3, tune_iter=40, tune_cv=5, rf_trees=300),
}


# ------------------------------- helpers ---------------------------------------
def fit_platt(p_raw, y):
    z = np.log(np.clip(p_raw, 1e-6, 1 - 1e-6) / (1 - np.clip(p_raw, 1e-6, 1 - 1e-6)))
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(z.reshape(-1, 1), y)
    return float(lr.coef_[0, 0]), float(lr.intercept_[0])


def oof_raw(params, X, y):
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    return cross_val_predict(XGBClassifier(**params), X, y, cv=cv, method="predict_proba")[:, 1]


def band_rows(stage, label, p, y, cutoffs):
    bands = np.array([assign_band(v, cutoffs) for v in p])
    rows = []
    for b in BANDS:
        m = bands == b
        rows.append({"stage": stage, "set": label, "band": b, "n": int(m.sum()),
                     "mean_predicted": round(float(p[m].mean()), 3) if m.any() else None,
                     "observed_failure_rate": round(float(y[m].mean()), 3) if m.any() else None})
    return rows


def linear_view(X, name):
    """Logistic Regression likes smaller numbers, so squash the huge funding amounts."""
    if name == "Logistic Regression" and "funding_total_usd" in X:
        return X.assign(funding_total_usd=np.log1p(X["funding_total_usd"]))
    return X


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(obj):
    """Make numpy numbers JSON-friendly."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    return obj


# ------------------------------- one stage -------------------------------------
def run_stage(stage, spec, out):
    print(f"\n{'=' * 78}\n{stage.upper()}\n{'=' * 78}")
    df, X, meta = spec["load"]()
    y = df["failed"].to_numpy()
    idx = np.arange(len(df))
    tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=SEED)
    Xtr, ytr, Xte, yte = X.iloc[tr], y[tr], X.iloc[te], y[te]
    ratio = float((ytr == 0).sum() / (ytr == 1).sum())
    print(f"rows {len(df)} | features {X.shape[1]} | train {len(tr)} | test {len(te)} | failed share {y.mean():.3f}")

    # --- 2. compare models with repeated cross-validation ---
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=spec["repeats"], random_state=SEED)
    models = {
        "Logistic Regression": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                             LogisticRegression(C=0.3, max_iter=3000)),
        "Random Forest": make_pipeline(SimpleImputer(strategy="median"),
                                       RandomForestClassifier(n_estimators=spec["rf_trees"], max_depth=14,
                                                              min_samples_leaf=3, random_state=SEED, n_jobs=-1)),
        "XGBoost (default)": XGBClassifier(**XGB_BASE),
    }
    comp = []
    for name, m in models.items():
        r = cross_validate(m, linear_view(Xtr, name), ytr, cv=cv, scoring={
            "auc": "roc_auc", "ap": "average_precision", "brier": "neg_brier_score"})
        comp.append({"stage": stage, "model": name, "auc_mean": r["test_auc"].mean(), "auc_std": r["test_auc"].std(),
                     "avg_precision": r["test_ap"].mean(), "brier": -r["test_brier"].mean()})
    print("\nModel comparison (cross-validation on the training rows):")

    # --- 3. tune XGBoost ---
    space = {"n_estimators": [150, 250, 350], "max_depth": [2, 3, 4, 5], "learning_rate": [0.03, 0.05, 0.1],
             "subsample": [0.7, 0.85, 1.0], "colsample_bytree": [0.5, 0.7, 0.9],
             "min_child_weight": [1, 3, 5, 10], "reg_lambda": [1, 5, 10], "scale_pos_weight": [1.0, ratio]}
    search = RandomizedSearchCV(XGBClassifier(**XGB_BASE), space, n_iter=spec["tune_iter"], scoring="roc_auc",
                                cv=StratifiedKFold(spec["tune_cv"], shuffle=True, random_state=SEED),
                                random_state=SEED, n_jobs=-1)
    search.fit(Xtr, ytr)
    best = {**XGB_BASE, **search.best_params_}
    r = cross_validate(XGBClassifier(**best), Xtr, ytr, cv=cv, scoring={
        "auc": "roc_auc", "ap": "average_precision", "brier": "neg_brier_score"})
    comp.append({"stage": stage, "model": "XGBoost (tuned)", "auc_mean": r["test_auc"].mean(),
                 "auc_std": r["test_auc"].std(), "avg_precision": r["test_ap"].mean(), "brier": -r["test_brier"].mean()})
    comp_df = pd.DataFrame(comp).round(3)
    print(comp_df[["model", "auc_mean", "auc_std", "avg_precision", "brier"]].to_string(index=False))
    print("tuned settings:", {k: v for k, v in search.best_params_.items()})
    cv_auc = float(r["test_auc"].mean())
    usable = cv_auc >= MIN_USABLE_AUC
    out["comparison"].append(comp_df)

    # --- 4. calibrate on out-of-fold scores and cut into four risk bands ---
    p_oof = oof_raw(best, Xtr, ytr)
    a, b = fit_platt(p_oof, ytr)
    cal_oof = apply_platt(p_oof, a, b)
    cutoffs = [float(np.quantile(cal_oof, q)) for q in (0.25, 0.5, 0.75)]

    # --- 5. final test, used once ---
    model = XGBClassifier(**best).fit(Xtr, ytr)
    p_te_raw = model.predict_proba(Xte)[:, 1]
    p_te = apply_platt(p_te_raw, a, b)
    auc = roc_auc_score(yte, p_te)
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(1000):
        i = rng.integers(0, len(yte), len(yte))
        if yte[i].min() != yte[i].max():
            boots.append(roc_auc_score(yte[i], p_te[i]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    bands_te = np.array([assign_band(v, cutoffs) for v in p_te])
    flag = np.isin(bands_te, ["High", "Critical"])
    prec = float(yte[flag].mean()) if flag.any() else float("nan")
    rec = float(((yte == 1) & flag).sum() / max((yte == 1).sum(), 1))

    t_auc = None
    if "founded_year" in df and df["founded_year"].notna().sum() > 200:
        cut = int(df["founded_year"].quantile(0.75))
        known = df["founded_year"].notna().to_numpy()
        old, new = known & (df["founded_year"] < cut).to_numpy(), known & (df["founded_year"] >= cut).to_numpy()
        tm = XGBClassifier(**best).fit(X.loc[old], y[old])
        t_auc = float(roc_auc_score(y[new], tm.predict_proba(X.loc[new])[:, 1]))
        print(f"\nTime-based check: train on startups founded before {cut} ({old.sum()} rows), "
              f"test on {cut} or later ({new.sum()} rows): AUC {t_auc:.3f}")

    print(f"\nHeld-out test ({len(yte)} rows): AUC {auc:.3f} (95% CI {lo:.3f} to {hi:.3f}) | "
          f"Brier raw {brier_score_loss(yte, p_te_raw):.3f} -> calibrated {brier_score_loss(yte, p_te):.3f} | "
          f"average precision {average_precision_score(yte, p_te):.3f}")
    print(f"High + Critical bands flag {flag.sum()} of {len(yte)}: precision {prec:.2f}, recall {rec:.2f} "
          f"(base failure rate {yte.mean():.2f})")
    out["test"].append({"stage": stage, "usable": usable, "cv_auc": round(cv_auc, 3), "test_auc": round(auc, 3),
                        "auc_ci_low": round(lo, 3), "auc_ci_high": round(hi, 3),
                        "brier_raw": round(brier_score_loss(yte, p_te_raw), 3),
                        "brier_calibrated": round(brier_score_loss(yte, p_te), 3),
                        "avg_precision": round(average_precision_score(yte, p_te), 3),
                        "time_check_auc": None if t_auc is None else round(t_auc, 3),
                        "high_critical_precision": round(prec, 3), "high_critical_recall": round(rec, 3),
                        "base_failure_rate": round(float(yte.mean()), 3)})
    rows = band_rows(stage, "train out-of-fold", cal_oof, ytr, cutoffs) + band_rows(stage, "test", p_te, yte, cutoffs)
    out["bands"] += rows
    print("\nObserved failure rate per risk band (test rows):")
    print(pd.DataFrame([r_ for r_ in rows if r_["set"] == "test"])[["band", "n", "mean_predicted", "observed_failure_rate"]].to_string(index=False))

    # --- 6. ablation: drop one group of inputs at a time ---
    cv5 = StratifiedKFold(5, shuffle=True, random_state=SEED)
    base_auc = cross_val_score(XGBClassifier(**best), Xtr, ytr, cv=cv5, scoring="roc_auc").mean()
    print(f"\nAblation (cross-validated AUC, all inputs = {base_auc:.3f}):")
    for g in sorted({risk_group(c) for c in X.columns}):
        cols = [c for c in X.columns if risk_group(c) != g]
        if not cols or len(cols) == X.shape[1]:
            continue
        auc_g = cross_val_score(XGBClassifier(**best), Xtr[cols], ytr, cv=cv5, scoring="roc_auc").mean()
        out["ablation"].append({"stage": stage, "dropped_group": g, "auc": round(auc_g, 3),
                                "change_vs_all": round(auc_g - base_auc, 3)})
        print(f"  without {g:9s}: {auc_g:.3f} ({auc_g - base_auc:+.3f})")

    # --- 7. retrain on all rows, calibrate, export ---
    entry = {"usable": usable, "label": "failed = closed", "rows": int(len(df)), "failed_share": round(float(y.mean()), 4),
             "cv_auc": round(cv_auc, 3), "test_auc": round(auc, 3), "test_auc_ci": [round(lo, 3), round(hi, 3)],
             "time_check_auc": None if t_auc is None else round(t_auc, 3), "best_params": search.best_params_,
             "features": list(X.columns), **meta}
    if not usable:
        print(f"\nNOT USABLE: cross-validated AUC {cv_auc:.3f} is below {MIN_USABLE_AUC}. No model exported.")
        (MODELS / f"{stage}.json").unlink(missing_ok=True)
        return entry, None, None
    p_all = oof_raw(best, X, y)
    a_all, b_all = fit_platt(p_all, y)
    cal_all = apply_platt(p_all, a_all, b_all)
    cut_all = [float(np.quantile(cal_all, q)) for q in (0.25, 0.5, 0.75)]
    final = XGBClassifier(**best).fit(X, y)
    path = MODELS / f"{stage}.json"
    final.save_model(path)
    reloaded = XGBClassifier()
    reloaded.load_model(path)
    assert np.allclose(final.predict_proba(X)[:, 1], reloaded.predict_proba(X)[:, 1]), "reload mismatch"
    obs = {r_["band"]: r_["observed_failure_rate"] for r_ in band_rows(stage, "all", cal_all, y, cut_all)}
    entry.update({"model_file": path.name, "sha256": sha256(path),
                  "calibration": {"a": a_all, "b": b_all}, "band_cutoffs": cut_all,
                  "band_observed_failure_rate": obs})
    if stage == "stage2":
        entry["ranges"] = {c: {"min": float(df[c].min()), "max": float(df[c].max()),
                               "p01": float(df[c].quantile(0.01)), "p99": float(df[c].quantile(0.99))}
                           for c in meta["numeric"]}
    print(f"\nSaved models/{path.name} (reload check passed). Band cutoffs {[round(c, 3) for c in cut_all]}")
    return entry, final, X


def shap_report(stage, model, X, out):
    try:
        import shap
        sv = shap.TreeExplainer(model).shap_values(X)
        mean_abs = pd.Series(np.abs(sv).mean(axis=0), index=X.columns).sort_values(ascending=False)
        print(f"\nTop factors overall (mean |SHAP|) for {stage}:")
        print(mean_abs.head(8).round(3).to_string())
        groups = mean_abs.groupby(mean_abs.index.map(risk_group)).sum().sort_values(ascending=False)
        print("Share of influence by risk-tree branch:", (groups / groups.sum()).round(2).to_dict())
        for f, v in mean_abs.head(25).items():
            out["shap"].append({"stage": stage, "feature": f, "mean_abs_shap": round(float(v), 4), "group": risk_group(f)})
    except Exception as e:  # keep going, but say clearly what failed
        print(f"\nSHAP check failed for {stage}:", type(e).__name__, e)


# ------------------------------- main ------------------------------------------
out = {"comparison": [], "test": [], "bands": [], "ablation": [], "shap": []}
config = {"created": str(date.today()), "versions": {"xgboost": xgboost.__version__, "scikit-learn": sklearn.__version__,
                                                     "numpy": np.__version__, "pandas": pd.__version__},
          "bands": BANDS, "stages": {}}
for stage, spec in SPECS.items():
    entry, model, X = run_stage(stage, spec, out)
    config["stages"][stage] = entry
    if model is not None:
        shap_report(stage, model, X, out)

(MODELS / "model_config.json").write_text(json.dumps(clean(config), indent=2))
pd.concat(out["comparison"]).round(3).to_csv(REPORTS / "model_comparison.csv", index=False)
pd.DataFrame(out["test"]).to_csv(REPORTS / "test_results.csv", index=False)
pd.DataFrame(out["bands"]).to_csv(REPORTS / "risk_bands.csv", index=False)
pd.DataFrame(out["ablation"]).to_csv(REPORTS / "ablation.csv", index=False)
pd.DataFrame(out["shap"]).to_csv(REPORTS / "shap_importance.csv", index=False)
print("\nSaved models/model_config.json and reports/*.csv")
