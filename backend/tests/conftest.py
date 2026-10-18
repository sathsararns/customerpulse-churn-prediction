"""Small raw customer records shared by regression and API tests."""

from pathlib import Path
import sys

import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    from src import db
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "predictions.db")


@pytest.fixture
def customers():
    records = []
    for i in range(40):
        records.append({
            "gender": "Female" if i % 2 else "Male",
            "SeniorCitizen": int(i % 7 == 0),
            "Partner": "Yes" if i % 2 else "No",
            "Dependents": "No",
            "tenure": i + 1,
            "PhoneService": "Yes",
            "MultipleLines": "No",
            "InternetService": "DSL" if i % 2 else "Fiber optic",
            "OnlineSecurity": "No", "OnlineBackup": "Yes",
            "DeviceProtection": "No", "TechSupport": "No",
            "StreamingTV": "Yes", "StreamingMovies": "No",
            "Contract": "Month-to-month" if i % 2 else "Two year",
            "PaperlessBilling": "Yes", "PaymentMethod": "Electronic check",
            "MonthlyCharges": float(20 + 2 * i),
            "TotalCharges": " " if i % 11 == 0 else str((i + 1) * (20 + 2 * i)),
        })
    return pd.DataFrame(records), pd.Series([i % 2 for i in range(40)])
