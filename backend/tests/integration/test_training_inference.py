import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression

from pipelines.training_pipeline import run_training_pipeline
from src.model_inference import load_artifacts, predict_single
import src.model_training as training


def test_training_saves_pipeline_and_api_matches_offline(customers, tmp_path, monkeypatch):
    X, y = customers
    raw = X.assign(Churn=y.map({0: "No", 1: "Yes"}), customerID=[f"C{i}" for i in X.index])
    raw_path = tmp_path / "customers.csv"
    raw.to_csv(raw_path, index=False)
    monkeypatch.setenv("MLFLOW_ARTIFACT_ROOT", (tmp_path / "mlartifacts").as_uri())
    monkeypatch.setattr(training, "build_models", lambda: {
        "baseline": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": LogisticRegression(max_iter=1000),
    })
    evaluations = []
    real_evaluate = training.evaluate

    def record_evaluation(pipeline, X_test, y_test, **kwargs):
        evaluations.append((pipeline, X_test.copy()))
        return real_evaluate(pipeline, X_test, y_test, **kwargs)

    monkeypatch.setattr(training, "evaluate", record_evaluation)
    name, fitted, report = run_training_pipeline(
        raw_path, tmp_path, cv_folds=2, activate=True,
        tracking_uri=f"sqlite:///{(tmp_path / 'tracking.db').as_posix()}",
    )
    assert name == max(report["cv_results"], key=lambda n: report["cv_results"][n]["mean_f1"])
    assert len(evaluations) == 1  # Only the selected candidate sees the test set.
    assert evaluations[0][0] is fitted
    assert not (tmp_path / "artifacts" / "scaler.pkl").exists()
    saved, saved_name = load_artifacts(tmp_path)
    np.testing.assert_allclose(saved.predict_proba(X), fitted.predict_proba(X))
    metadata = json.loads((tmp_path / "reports" / "model_metrics.json").read_text())
    evaluation = json.loads((tmp_path / "reports" / "evaluation_report.json").read_text())
    assert metadata["artifact_format"] == "sklearn_pipeline_v2"
    assert metadata["dataset_size"] == len(X)
    assert sum(map(sum, evaluation["confusion_matrix"])) == report["test_rows"]
    assert evaluation["updated_at"]
    assert metadata["dataset_sha256"]
    assert metadata["source_sha256"]
    assert "git_commit" in metadata
    assert metadata["prediction_threshold"] == 0.5
    bundle = tmp_path / "artifacts" / "models" / report["model_version"]
    for filename in ["pipeline.joblib", "manifest.json", "input_schema.json", "config.json", "evaluation_report.json"]:
        assert (bundle / filename).is_file()
    assert (bundle / "source" / "src" / "preprocessing.py").is_file()
    configuration = json.loads((bundle / "config.json").read_text())
    assert configuration["data_path"] == str(raw_path.resolve())
    from utils.run_status import read_latest_run
    from utils.config import load_config
    recorded = read_latest_run(load_config(base_dir=tmp_path))
    assert recorded["status"] == "completed"
    assert all(stage["status"] == "completed" for stage in recorded["stages"])
    assert recorded["model_version"] == report["model_version"]
    saved_split = pd.read_csv(tmp_path / "artifacts" / "datasets" / report["dataset_version"] / "X_train.csv")
    assert "Contract" in saved_split  # Raw split, not an encoded/scaled dataset.
    assert set(saved_split.SeniorCitizen) == {0, 1}

    # Serving must not require training CSVs or separately saved scalers.
    sample = X.iloc[1].to_dict()
    offline = predict_single(saved, sample)
    (tmp_path / "artifacts" / "datasets" / report["dataset_version"] / "X_train.csv").unlink()
    from app import main as api
    from src import db
    monkeypatch.setattr(api, "BASE_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "history.db")
    with TestClient(api.app) as client:
        response = client.post("/predict", json=sample)
        assert response.status_code == 200, response.text
        assert response.json()["probability"] == offline["probability"]
        assert response.json()["prediction"] == offline["prediction"]
        assert response.json()["model"] == saved_name
        assert client.get("/model-info").json()["features"] == len(metadata["feature_names"])
        history = client.get("/recent-predictions").json()["items"]
        assert history[0]["probability"] == offline["probability"]


def test_legacy_artifacts_require_retraining(tmp_path):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "model_metrics.json").write_text('{"best_model": "old"}')
    with pytest.raises(ValueError, match="Legacy model artifacts"):
        load_artifacts(tmp_path)


def test_missing_target_is_never_imputed(customers, tmp_path):
    X, y = customers
    raw = X.assign(Churn=y.map({0: "No", 1: "Yes"}))
    raw.loc[0, "Churn"] = None
    path = tmp_path / "missing_target.csv"
    raw.to_csv(path, index=False)
    with pytest.raises(ValueError, match="Churn labels must be non-missing"):
        run_training_pipeline(path, tmp_path)
