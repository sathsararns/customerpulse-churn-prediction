"""Shared, fitted preprocessing for raw telecom customer records."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, OneToOneFeatureMixin, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.utils.validation import check_array, check_is_fitted

CONTINUOUS_COLUMNS = ["tenure", "MonthlyCharges", "TotalCharges"]
BINARY_COLUMNS = ["SeniorCitizen"]
CATEGORICAL_COLUMNS = [
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
    "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod",
]
FEATURE_COLUMNS = CONTINUOUS_COLUMNS + BINARY_COLUMNS + CATEGORICAL_COLUMNS


def normalize_features(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize types without learning statistics; identifiers are never features."""
    missing = sorted(set(FEATURE_COLUMNS) - set(data.columns))
    if missing:
        raise ValueError(f"Missing customer features: {', '.join(missing)}")
    result = data.loc[:, FEATURE_COLUMNS].copy()
    for column in CONTINUOUS_COLUMNS + BINARY_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
    for column in CATEGORICAL_COLUMNS:
        values = result[column].astype(object).map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        result[column] = values.where(values.notna() & values.ne(""), np.nan)
    return result


class IQRClipper(OneToOneFeatureMixin, TransformerMixin, BaseEstimator):
    """Learn continuous-feature bounds during fit and reuse them during transform."""

    def __init__(self, factor=1.5):
        self.factor = factor

    def fit(self, X, y=None):
        values = check_array(X, dtype=float)
        self.n_features_in_ = values.shape[1]
        lower_quartile, upper_quartile = np.percentile(values, [25, 75], axis=0)
        spread = upper_quartile - lower_quartile
        self.lower_bounds_ = np.where(
            spread > 0, lower_quartile - self.factor * spread, -np.inf
        )
        self.upper_bounds_ = np.where(
            spread > 0, upper_quartile + self.factor * spread, np.inf
        )
        return self

    def transform(self, X):
        check_is_fitted(self, ["lower_bounds_", "upper_bounds_"])
        values = check_array(X, dtype=float)
        if values.shape[1] != self.n_features_in_:
            raise ValueError("Outlier transformer received an unexpected feature count")
        return np.clip(values, self.lower_bounds_, self.upper_bounds_)


def build_pipeline(classifier) -> Pipeline:
    """Build an unfitted pipeline so every CV fold learns its own preprocessing."""
    continuous = Pipeline([
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("outliers", IQRClipper()),
        ("scaler", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    preprocessor = ColumnTransformer([
        ("continuous", continuous, CONTINUOUS_COLUMNS),
        ("binary", SimpleImputer(strategy="most_frequent", keep_empty_features=True), BINARY_COLUMNS),
        ("categorical", categorical, CATEGORICAL_COLUMNS),
    ], remainder="drop")
    return Pipeline([
        ("normalize", FunctionTransformer(normalize_features, validate=False)),
        ("preprocessor", preprocessor),
        ("classifier", classifier),
    ])
