"""Train-split-fitted preprocessing for future eligible model experiments.

Do not apply this pipeline to the legacy model artifacts without a separate,
eligible dataset and independent evaluation. Call fit only on training folds.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def make_preprocessor(numeric_features: Sequence[str], categorical_features: Sequence[str]) -> ColumnTransformer:
    """Build a deterministic transformer; no statistics are learned until fit()."""
    numeric = Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
    ])
    categorical = Pipeline([
        ("impute", SimpleImputer(strategy="constant", fill_value="__UNKNOWN__")),
        ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer(
        [("numeric", numeric, list(numeric_features)),
         ("categorical", categorical, list(categorical_features))],
        remainder="drop",
        verbose_feature_names_out=True,
    )


def validate_feature_frame(
    frame: pd.DataFrame,
    numeric_features: Sequence[str],
    categorical_features: Sequence[str],
    numeric_bounds: dict[str, tuple[float, float]] | None = None,
) -> None:
    """Validate declared inputs without coercing unknown/missing values to zero."""
    required = [*numeric_features, *categorical_features]
    missing_columns = sorted(set(required) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing feature columns: {', '.join(missing_columns)}")
    for name in numeric_features:
        non_missing = frame[name].dropna()
        if non_missing.empty:
            raise ValueError(f"Feature {name} has no observed training values; safe imputation is unavailable")
        if not pd.api.types.is_numeric_dtype(non_missing):
            raise ValueError(f"Feature {name} must contain numeric values or missing values")
        if not np.isfinite(non_missing.to_numpy(dtype=float)).all():
            raise ValueError(f"Feature {name} must not contain infinite values")
        if numeric_bounds and name in numeric_bounds:
            lower, upper = numeric_bounds[name]
            if lower > upper or not non_missing.between(lower, upper).all():
                raise ValueError(f"Feature {name} is outside its documented numeric bounds")
