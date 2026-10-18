import json
import sqlite3
from urllib.error import URLError

from fastapi.testclient import TestClient
import pytest

from app import main as api
from src import db
from src.prediction_store import get_recent_predictions, save_prediction
from utils.config import load_config
from utils.service_health import probe_tracking


@pytest.fixture
def isolated_api(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "BASE_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "history.db")
    return tmp_path


def test_missing_model_reports_degraded_state_and_no_predictions(isolated_api, customers):
    X, _ = customers
    with TestClient(api.app) as client:
        health = client.get("/health").json()
        assert health["status"] == "degraded"
        assert health["ready"] is False
        assert health["model_version"] is None
        assert client.get("/model-info").status_code == 503
        assert client.get("/metrics").status_code == 503
        assert client.post("/predict", json=X.iloc[1].to_dict()).status_code == 503
        assert client.get("/pipeline-status").json()["run"] is None


@pytest.mark.parametrize("changes", [
    {"Contract": "Unsupported"}, {"SeniorCitizen": 2}, {"SeniorCitizen": True},
    {"tenure": -1}, {"tenure": 1.5}, {"MonthlyCharges": -1},
    {"MonthlyCharges": "NaN"}, {"TotalCharges": "Infinity"},
    {"MonthlyCharges": 1001}, {"TotalCharges": 50001},
    {"PhoneService": "No"}, {"InternetService": "No"},
    {"Unexpected": "field"},
    {"customer_id": ""}, {"customer_id": "   "}, {"customer_id": "x" * 129},
])
def test_invalid_customer_is_rejected_before_prediction(isolated_api, customers, changes):
    X, _ = customers
    with TestClient(api.app) as client:
        response = client.post("/predict", json={**X.iloc[1].to_dict(), **changes})
        assert response.status_code == 422, response.text


def test_tracking_probe_is_read_only_and_reports_real_connectivity(tmp_path):
    settings = load_config(base_dir=tmp_path)
    result = probe_tracking(settings)
    assert result["status"] == "disconnected"
    path = tmp_path / "artifacts" / "training" / "mlflow.db"
    assert not path.exists()
    path.parent.mkdir(parents=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE experiments (experiment_id INTEGER)")
    assert probe_tracking(settings)["status"] == "connected"


def test_tracking_http_failure_is_not_reported_connected(tmp_path, monkeypatch):
    from dataclasses import replace
    from utils import service_health
    settings = replace(load_config(base_dir=tmp_path), tracking_uri="http://127.0.0.1:9999")
    def unavailable(*args, **kwargs):
        raise URLError("Connection refused")
    monkeypatch.setattr(service_health, "urlopen", unavailable)
    assert probe_tracking(settings)["status"] == "disconnected"


def test_mlflow_endpoint_uses_the_probe_result(isolated_api, monkeypatch):
    monkeypatch.setattr(api, "probe_tracking", lambda settings: {
        "status": "disconnected", "experiment_name": settings.experiment_name,
        "tracking_uri": "http://offline", "checked_at": "2026-10-17T06:00:00Z",
        "detail": "Connection refused",
    })
    with TestClient(api.app) as client:
        result = client.get("/mlflow-info")
        assert result.status_code == 200
        assert result.json()["status"] == "disconnected"


def test_history_migration_preserves_rows_and_records_new_versions(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    with sqlite3.connect(path) as connection:
        connection.execute("""CREATE TABLE predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            model_name TEXT, prediction TEXT, probability REAL,
            risk_level TEXT, customer_payload TEXT)""")
        connection.execute("""INSERT INTO predictions
            (model_name,prediction,probability,risk_level,customer_payload)
            VALUES ('old','Not Churn',0.1,'Low','{}')""")
    db.init_db()
    db.init_db()
    save_prediction("new", "Churn", 0.8, "High", {}, model_version="version-a")
    rows = get_recent_predictions()
    assert len(rows) == 2
    assert rows[0]["model_version"] == "version-a"
    assert rows[1]["model_version"] is None
    assert rows[0]["created_at"].endswith("Z")


def test_failed_training_is_recorded(customers, tmp_path):
    from pipelines.training_pipeline import run_training_pipeline
    from utils.run_status import read_latest_run
    X, y = customers
    raw = X.assign(Churn=y.map({0: "No", 1: "Yes"}))
    raw.loc[0, "Churn"] = None
    path = tmp_path / "bad.csv"
    raw.to_csv(path, index=False)
    with pytest.raises(ValueError):
        run_training_pipeline(path, tmp_path)
    run = read_latest_run(load_config(base_dir=tmp_path))
    assert run["status"] == "failed"
    assert run["stages"][0]["status"] == "failed"
    assert run["completed_at"]
    assert run["stages"][1]["status"] == "pending"
