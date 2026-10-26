"""Loads the trained models once at startup. Refuses to run if a model file was changed."""
import hashlib
import json
import threading
from pathlib import Path

import numpy as np
import shap
from xgboost import XGBClassifier


class StageModel:
    def __init__(self, name: str, entry: dict, models_dir: Path):
        self.name, self.entry, self.features = name, entry, entry["features"]
        path = models_dir / entry["model_file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            raise RuntimeError(f"{path.name}: file does not match the hash in model_config.json. Refusing to load it.")
        self.model = XGBClassifier()
        self.model.load_model(path)
        self.model.set_params(n_jobs=1)
        self.explainer = shap.TreeExplainer(self.model)
        self._lock = threading.Lock()   # one prediction at a time: they take milliseconds, and it avoids races

    def score(self, X):
        """Returns (raw model score, SHAP value per feature) for a one-row table."""
        X = X[self.features]
        with self._lock:
            p_raw = float(self.model.predict_proba(X)[0, 1])
            sv = np.asarray(self.explainer.shap_values(X))[0]
        return p_raw, sv


class ModelStore:
    def __init__(self, models_dir: Path):
        self.config = json.loads((models_dir / "model_config.json").read_text())
        self.stages = {name: StageModel(name, e, models_dir)
                       for name, e in self.config["stages"].items()
                       if e.get("usable") and e.get("model_file")}
        if not self.stages:
            raise RuntimeError("No usable model found. Run scripts/train.py first.")
