import json

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression
from fastapi.testclient import TestClient

from pipelines.data_pipeline import run_data_pipeline
from pipelines.inference_pipeline import run_inference_pipeline
from src.data_validation import input_schema
from src.model_evaluation import evaluate
from src.preprocessing import build_pipeline
from utils.artifact_manager import get_artifact_manager, sha256_file, source_snapshot
from utils.config import load_config


@pytest.fixture
def candidates(customers, tmp_path):
    X, y = customers
    source = tmp_path / "customers.csv"
    X.assign(Churn=y.map({0: "No", 1: "Yes"})).to_csv(source, index=False)
    settings = load_config(base_dir=tmp_path)
    data = run_data_pipeline(source, settings=settings)
    manager = get_artifact_manager(settings)
    sources, revision = source_snapshot()
    for version, threshold, offset in [("version-a", 0.9999, 0), ("version-b", 0.0001, 100)]:
        training = X.assign(MonthlyCharges=X.MonthlyCharges + offset)
        pipeline = build_pipeline(LogisticRegression()).fit(training, y)
        report = evaluate(pipeline, X, y, prediction_threshold=threshold)
        metadata = {
            "model_version": version, "best_model": "logistic_regression",
            "prediction_threshold": threshold, "dataset_version": data.metadata["dataset_version"],
            "dataset_sha256": data.metadata["dataset_sha256"], **revision,
            "mlflow_run_id": "fixture-run", "dataset_size": len(X),
            "feature_names": pipeline["preprocessor"].get_feature_names_out().tolist(),
        }
        manager.save_candidate(pipeline, metadata, report, input_schema(), settings.snapshot(), sources)
    return manager, X, source, tmp_path


def test_candidates_are_immutable_and_activation_is_explicit(candidates):
    manager, X, _, _ = candidates
    first_path = manager.root / "models" / "version-a" / "pipeline.joblib"
    original_hash = sha256_file(first_path)
    assert not (manager.root / "active_model.json").exists()
    manager._activate("version-a")
    active_a, manifest_a = manager.load_model()
    explicit_b, manifest_b = manager.load_model("version-b")
    assert manifest_a["prediction_threshold"] == 0.9999
    assert manifest_b["prediction_threshold"] == 0.0001
    assert not np.array_equal(
        active_a["preprocessor"].named_transformers_["continuous"]["scaler"].mean_,
        explicit_b["preprocessor"].named_transformers_["continuous"]["scaler"].mean_,
    )
    assert manager.get_manifest()["model_version"] == "version-a"
    manager._activate("version-b")
    assert manager.get_manifest()["model_version"] == "version-b"
    assert sha256_file(first_path) == original_hash
    with pytest.raises(FileExistsError):
        manager.save_candidate(active_a, manifest_a, {}, {}, {}, {})


def test_corrupted_model_is_rejected_before_loading(candidates):
    manager, _, _, _ = candidates
    path = manager.root / "models" / "version-a" / "pipeline.joblib"
    path.write_bytes(path.read_bytes() + b"corrupted")
    with pytest.raises(ValueError, match="checksum mismatch: pipeline.joblib"):
        manager.load_model("version-a")


def test_batch_uses_requested_version_and_saved_threshold(candidates):
    manager, X, source, root = candidates
    manager._activate("version-b")
    result = run_inference_pipeline(source, root / "predictions.csv", "version-a", root)
    pipeline, manifest = manager.load_model("version-a")
    expected = pipeline.predict_proba(X)[:, 1]
    np.testing.assert_allclose(result.probability, expected.round(4))
    assert set(result.model_version) == {"version-a"}
    assert (result.prediction.eq("Churn").to_numpy() == (expected >= manifest["prediction_threshold"])).all()
    assert manager.get_manifest()["model_version"] == "version-b"


def test_invalid_versions_and_changed_manifests_are_rejected(candidates):
    manager, _, _, _ = candidates
    with pytest.raises(ValueError, match="Invalid artifact version"):
        manager.load_model("../escape")
    manager._activate("version-a")
    path = manager.root / "models" / "version-a" / "manifest.json"
    metadata = json.loads(path.read_text())
    metadata["prediction_threshold"] = 0.1
    path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="manifest checksum mismatch"):
        manager.load_model()


def test_api_uses_active_version_threshold(candidates, monkeypatch):
    manager, X, _, root = candidates
    from app import main as api
    from src import db
    monkeypatch.setattr(api, "BASE_DIR", root)
    monkeypatch.setattr(db, "DB_PATH", root / "history.db")
    manager._activate("version-a")
    with TestClient(api.app) as client:
        result = client.post("/predict", json=X.iloc[1].to_dict())
        assert result.status_code == 200, result.text
        assert result.json()["model_version"] == "version-a"
        assert result.json()["prediction"] == "Not Churn"
        assert client.get("/model-info").json()["predictionThreshold"] == 0.9999


def test_api_loads_once_and_keeps_version_metrics_and_history_pinned(candidates, monkeypatch):
    manager, X, _, root = candidates
    from app import main as api
    from src import db
    monkeypatch.setattr(api, "BASE_DIR", root)
    monkeypatch.setattr(db, "DB_PATH", root / "history.db")
    manager._activate("version-a")
    calls = []
    original = api.load_model_bundle
    def counted(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(api, "load_model_bundle", counted)
    with TestClient(api.app) as client:
        first = client.post("/predict", json=X.iloc[1].to_dict()).json()
        manager._activate("version-b")
        second = client.post("/predict", json=X.iloc[1].to_dict()).json()
        assert len(calls) == 1
        assert first["event_id"] != second["event_id"]
        assert {k: v for k, v in first.items() if k != "event_id"} == {k: v for k, v in second.items() if k != "event_id"}
        assert second["model_version"] == "version-a"
        assert client.get("/model-info").json()["version"] == "version-a"
        assert client.get("/metrics").json()["model_version"] == "version-a"
        assert client.get("/recent-predictions").json()["items"][0]["model_version"] == "version-a"
        health = client.get("/health").json()
        assert health["model_version"] == "version-a"
        assert health["selected_model_version"] == "version-b"
        assert health["reload_required"] is True
        assert health["predictionCount"] == 2


def test_customer_identity_is_traced_and_does_not_change_api_features(candidates, monkeypatch):
    manager, X, _, root = candidates
    from app import main as api
    monkeypatch.setattr(api, "BASE_DIR", root)
    manager._activate("version-a")
    captured = []
    original = api.predict_single
    def inspect_features(pipeline, features, threshold):
        captured.append(features)
        return original(pipeline, features, threshold)
    monkeypatch.setattr(api, "predict_single", inspect_features)
    with TestClient(api.app) as client:
        first = client.post("/predict", json={**X.iloc[1].to_dict(), "customer_id": "00001"}).json()
        second = client.post("/predict", json={**X.iloc[1].to_dict(), "customer_id": "00002"}).json()
        assert first["probability"] == second["probability"]
        assert captured[0] == captured[1]
        assert "customer_id" not in captured[0] and "customerID" not in captured[0]
        assert first["event_id"] != second["event_id"]
        row = client.get("/recent-predictions").json()["items"][0]
        assert row["event_id"] == second["event_id"]
        assert row["customer_id"] == "00002"
        assert row["source"] == "api"
    with TestClient(api.app) as client:
        assert client.get("/recent-predictions").json()["items"][0]["event_id"] == second["event_id"]


def test_batch_preserves_customer_ids_and_records_replayable_events(candidates):
    from src.db import prediction_count
    from src.prediction_store import get_recent_predictions
    manager, X, source, root = candidates
    manager._activate("version-a")
    identifiers = [f"{i:05d}" for i in range(len(X))]
    X.assign(customerID=identifiers).to_csv(source, index=False)
    result = run_inference_pipeline(source, root / "batch.csv", output_dir=root)
    assert result.customer_id.tolist() == identifiers
    assert set(result.source) == {"batch"}
    assert prediction_count() == len(X)
    assert get_recent_predictions()[0]["customer_id"] == identifiers[-1]
    X.assign(customerID=identifiers, event_id=result.event_id).to_csv(source, index=False)
    run_inference_pipeline(source, root / "batch-replay.csv", output_dir=root)
    assert prediction_count() == len(X)
