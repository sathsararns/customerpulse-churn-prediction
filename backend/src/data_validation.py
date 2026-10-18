"""Validate the telecom input contract without learning data statistics."""

import numpy as np
import pandas as pd

from src.preprocessing import (
    BINARY_COLUMNS, CATEGORICAL_COLUMNS, CONTINUOUS_COLUMNS, FEATURE_COLUMNS,
    normalize_features,
)

CATEGORY_VALUES = {
    "gender": ["Female", "Male"],
    "Partner": ["Yes", "No"], "Dependents": ["Yes", "No"],
    "PhoneService": ["Yes", "No"],
    "MultipleLines": ["Yes", "No", "No phone service"],
    "InternetService": ["DSL", "Fiber optic", "No"],
    **{column: ["Yes", "No", "No internet service"] for column in [
        "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport",
        "StreamingTV", "StreamingMovies",
    ]},
    "Contract": ["Month-to-month", "One year", "Two year"],
    "PaperlessBilling": ["Yes", "No"],
    "PaymentMethod": ["Electronic check", "Mailed check",
                      "Bank transfer (automatic)", "Credit card (automatic)"],
}


def input_schema():
    properties = {
        name: {"type": ["number", "null"], "minimum": 0}
        for name in CONTINUOUS_COLUMNS
    }
    properties["tenure"]["type"] = ["integer", "null"]
    properties["SeniorCitizen"] = {"type": ["integer", "null"], "enum": [0, 1, None]}
    properties.update({
        name: {"type": ["string", "null"], "enum": values + [None]}
        for name, values in CATEGORY_VALUES.items()
    })
    return {"type": "object", "required": FEATURE_COLUMNS,
            "properties": properties, "additionalProperties": True}


def validate_and_normalize(data, require_target=True):
    required = set(FEATURE_COLUMNS) | ({"Churn"} if require_target else set())
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if data.empty:
        raise ValueError("Customer dataset cannot be empty")
    if "customerID" in data:
        identifiers = data["customerID"].astype("string").str.strip()
        if identifiers.isna().any() or identifiers.eq("").any():
            raise ValueError("customerID must not be missing or blank")
        if identifiers.duplicated().any():
            raise ValueError("Duplicate customerID values are not allowed")

    for name in CONTINUOUS_COLUMNS + BINARY_COLUMNS:
        raw = data[name].replace(r"^\s*$", np.nan, regex=True)
        numeric = pd.to_numeric(raw, errors="coerce")
        if (raw.notna() & numeric.isna()).any() or np.isinf(numeric.dropna()).any():
            raise ValueError(f"{name} contains invalid numeric values")
        if (numeric.dropna() < 0).any():
            raise ValueError(f"{name} must be non-negative")
        if name in ["SeniorCitizen", "tenure"] and (numeric.dropna() % 1 != 0).any():
            raise ValueError(f"{name} must contain whole numbers")
        if name == "SeniorCitizen" and not numeric.dropna().isin([0, 1]).all():
            raise ValueError("SeniorCitizen must be 0 or 1")

    normalized = normalize_features(data)
    for name in CATEGORICAL_COLUMNS:
        if not normalized[name].dropna().isin(CATEGORY_VALUES[name]).all():
            raise ValueError(f"{name} contains unsupported categorical values")
    target = None
    if require_target:
        labels = data["Churn"].astype("string").str.strip()
        if labels.isna().any() or not labels.isin(["Yes", "No"]).all():
            raise ValueError("Churn labels must be non-missing Yes or No values")
        if set(labels) != {"Yes", "No"}:
            raise ValueError("Training requires both Yes and No churn classes")
        target = labels.map({"Yes": 1, "No": 0}).astype(int)
        target.name = "Churn"
    return normalized, target
