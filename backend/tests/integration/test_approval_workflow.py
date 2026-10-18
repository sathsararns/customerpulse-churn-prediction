"""Promotion must be gated; failures preserve the approved bundle and serving API."""

from dataclasses import replace
import json

from fastapi.testclient import TestClient
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression

from pipelines import approval_pipeline as workflow
from pipelines.data_pipeline import run_data_pipeline
from src.data_validation import input_schema
from src.model_evaluation import evaluate
from src.preprocessing import build_pipeline
from utils.acceptance_gate import CandidateRejected, apply_acceptance_gate, promote_candidate
from utils.artifact_manager import get_artifact_manager, source_snapshot
from utils.config import load_config


@pytest.fixture
def approval_candidates(customers, tmp_path):
    X, y = customers
    source = tmp_path / "customers.csv"
    X.assign(Churn=y.map({0: "No", 1: "Yes"})).to_csv(source, index=False)
    settings = load_config(base_dir=tmp_path)
    data = run_data_pipeline(source, settings=settings)
    manager = get_artifact_manager(settings)
    sources, revision = source_snapshot()
    for version, classifier in [("approved", LogisticRegression()), ("candidate", LogisticRegression()),
                                ("another", LogisticRegression()), ("failing", DummyClassifier(strategy="most_frequent"))]:
        pipeline = build_pipeline(classifier).fit(data.X_train, data.y_train)
        report = {**evaluate(pipeline, data.X_test, data.y_test), "model_version": version,
                  "dataset_version": data.metadata["dataset_version"], "dataset_sha256": data.metadata["dataset_sha256"],
                  "best_model": type(classifier).__name__, "prediction_threshold": 0.5,
                  "training_rows": len(data.X_train), "test_rows": len(data.X_test), "dataset_size": len(X),
                  "feature_names": pipeline["preprocessor"].get_feature_names_out().tolist(), **revision}
        manager.save_candidate(pipeline, report, report, input_schema(), settings.snapshot(), sources)
    manager.activate("approved")
    return settings, manager, X, source


def test_failing_model_cannot_replace_approved_model_while_api_keeps_serving(approval_candidates, monkeypatch):
    settings, manager, X, _ = approval_candidates
    from app import main as api
    monkeypatch.setattr(api, "BASE_DIR", settings.base_dir)
    before = (manager.root / "active_model.json").read_bytes()
    report_before = (settings.base_dir / "reports" / "model_metrics.json").read_bytes()
    with TestClient(api.app) as client:
        expected = client.post("/predict", json=X.iloc[1].to_dict()).json()
        with pytest.raises(CandidateRejected, match="failed acceptance"):
            manager.activate("failing")
        actual = client.post("/predict", json=X.iloc[1].to_dict()).json()
        assert actual["model_version"] == expected["model_version"] == "approved"
        assert actual["probability"] == expected["probability"]
        assert client.get("/health").json()["ready"]
        assert client.get("/metrics").json()["model_version"] == "approved"
    assert (manager.root / "active_model.json").read_bytes() == before
    assert (settings.base_dir / "reports" / "model_metrics.json").read_bytes() == report_before
    receipt_id = json.loads((manager.root / "gates" / "failing" / "latest.json").read_text())["gate_id"]
    receipt = json.loads((manager.root / "gates" / "failing" / f"{receipt_id}.json").read_text())
    assert not receipt["passed"]
    with pytest.raises(CandidateRejected):
        promote_candidate(settings, "failing", receipt_id)


def test_promotion_rechecks_policy_reference_and_receipt_integrity(approval_candidates):
    settings, manager, _, _ = approval_candidates
    receipt = apply_acceptance_gate(settings, "candidate")
    stricter = replace(settings, acceptance=replace(settings.acceptance, min_precision=0.99))
    with pytest.raises(CandidateRejected, match="policy changed"):
        promote_candidate(stricter, "candidate", receipt["gate_id"])
    manager.activate("another")
    with pytest.raises(CandidateRejected, match="reference changed"):
        promote_candidate(settings, "candidate", receipt["gate_id"])
    receipt = apply_acceptance_gate(settings, "candidate")
    path = manager.root / "gates" / "candidate" / f"{receipt['gate_id']}.json"
    changed = json.loads(path.read_text())
    changed["reference_model_version"] = "forged"
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(CandidateRejected, match="Invalid or rejected"):
        promote_candidate(settings, "candidate", receipt["gate_id"])
    assert manager.get_manifest()["model_version"] == "another"


def test_explicit_version_handoffs_and_invalid_data_block_workflow(approval_candidates):
    settings, manager, X, source = approval_candidates
    before = (manager.root / "active_model.json").read_bytes()
    bad = X.assign(Churn="Yes")
    bad.loc[0, "Churn"] = None
    bad_path = settings.base_dir / "invalid.csv"
    bad.to_csv(bad_path, index=False)
    with pytest.raises(ValueError, match="Churn labels"):
        workflow.validate_dataset(settings, bad_path, "invalid-run")
    assert (manager.root / "active_model.json").read_bytes() == before
    context = workflow.validate_dataset(settings, source, "handoff-run")
    repeated = workflow.validate_dataset(settings, source, "handoff-run")
    assert repeated == context
    prepared = workflow.prepare_splits(context, settings)
    assert prepared["dataset_version"]
    assert workflow.prepare_splits(context, settings) == prepared
    with pytest.raises(ValueError, match="handoff mismatch"):
        workflow.train_candidate({**prepared, "dataset_version": "wrong-version"}, settings)
    with pytest.raises(ValueError, match="prerequisites"):
        workflow.publish_approved(prepared, settings)
    assert (manager.root / "active_model.json").read_bytes() == before


def test_each_workflow_phase_is_retry_safe_and_gated(customers, tmp_path, monkeypatch):
    import src.model_training as training
    X, y = customers
    source = tmp_path / "raw.csv"
    X.assign(Churn=y.map({0: "No", 1: "Yes"})).to_csv(source, index=False)
    settings = replace(load_config(base_dir=tmp_path), cv_folds=2,
                       tracking_uri=f"sqlite:///{(tmp_path / 'tracking.db').as_posix()}")
    monkeypatch.setenv("MLFLOW_ARTIFACT_ROOT", (tmp_path / "mlartifacts").as_uri())
    monkeypatch.setattr(training, "build_models", lambda: {"lr": LogisticRegression()})
    context = workflow.validate_dataset(settings, source, "complete-run")
    for phase in [workflow.prepare_splits, workflow.train_candidate, workflow.evaluate_candidate,
                  workflow.apply_gate, workflow.publish_approved]:
        previous = dict(context)
        context = phase(previous, settings)
        assert phase(previous, settings) == context
    manager = get_artifact_manager(settings)
    assert manager.get_manifest()["model_version"] == context["published_model_version"]
    assert context["dataset_version"] == manager.get_manifest()["dataset_version"]
    assert context["gate_id"]
