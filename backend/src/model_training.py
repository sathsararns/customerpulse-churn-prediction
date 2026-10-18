"""Select complete pipelines on training-only CV and evaluate the winner once."""

from dataclasses import replace

import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score

from src.data_validation import input_schema
from src.model_building import build_models
from src.model_evaluation import evaluate
from src.preprocessing import FEATURE_COLUMNS, build_pipeline
from utils.artifact_manager import get_artifact_manager, utc_now
from utils.config import load_config
from utils.mlflow_utils import MLflowTracker


def train_candidates(X_train, y_train, *, cv_folds=None, tracking_uri=None,
                     settings=None, lineage=None, recorder=None):
    """Select using training-only CV; this function never receives the holdout."""
    settings = settings or load_config()
    if cv_folds is not None:
        settings = replace(settings, cv_folds=cv_folds)
    if tracking_uri:
        settings = replace(settings, tracking_uri=tracking_uri)
    if y_train.nunique() != 2 or y_train.value_counts().min() < settings.cv_folds:
        raise ValueError("Each training class must have at least cv_folds records")
    if recorder:
        recorder.start_stage("training")
    tracker = MLflowTracker(settings)
    cv = StratifiedKFold(n_splits=settings.cv_folds, shuffle=True,
                        random_state=settings.random_state)
    candidates, runs, pipelines = {}, {}, {}
    lineage = lineage or {"model_version": "unpublished"}

    def score(estimator, features, target):
        positive = estimator.predict_proba(features)[:, 1] >= settings.prediction_threshold
        return f1_score(target, positive, zero_division=0)

    for name, classifier in build_models().items():
        if "random_state" in classifier.get_params():
            classifier.set_params(random_state=settings.random_state)
        print(f"Cross-validating {name} ({settings.cv_folds} folds)", flush=True)
        pipeline = build_pipeline(classifier)
        scores = cross_val_score(pipeline, X_train, y_train, cv=cv,
                                 scoring=score, n_jobs=1, error_score="raise")
        candidates[name] = {"mean_f1": float(np.mean(scores)),
                            "std_f1": float(np.std(scores)), "fold_f1": scores.tolist()}
        pipeline.fit(X_train, y_train)
        pipelines[name] = pipeline
        runs[name] = tracker.log_candidate(name, pipeline, classifier, candidates[name],
                                           X_train.head(2), lineage)
        print(f"  CV F1: {candidates[name]['mean_f1']:.4f}", flush=True)

    best_name = max(candidates, key=lambda name: candidates[name]["mean_f1"])
    best_pipeline = pipelines[best_name]
    if recorder:
        recorder.complete_stage("training")
    selection = {
        **lineage, "best_model": best_name, "selection_metric": "cv_f1",
        "cv_folds": settings.cv_folds, "cv_results": candidates,
        "mlflow_run_id": runs[best_name], "mlflow_tracking_uri": tracker.tracking_uri,
        "prediction_threshold": settings.prediction_threshold,
        "training_rows": len(X_train), "input_features": FEATURE_COLUMNS,
        "feature_names": best_pipeline["preprocessor"].get_feature_names_out().tolist(),
        "updated_at": utc_now(),
    }
    return best_name, best_pipeline, selection


def evaluate_selected_model(pipeline, selection, X_test, y_test, *, settings, recorder=None):
    if recorder:
        recorder.start_stage("evaluation")
    report = {**selection, **evaluate(pipeline, X_test, y_test,
                                      prediction_threshold=selection["prediction_threshold"]),
              "test_rows": len(X_test), "dataset_size": selection["training_rows"] + len(X_test),
              "updated_at": utc_now()}
    MLflowTracker(settings).log_evaluation(report)
    if recorder:
        recorder.complete_stage("evaluation")
    return report


def train_and_select_best_model(X_train, y_train, X_test, y_test, *,
                                cv_folds=None, tracking_uri=None, settings=None, lineage=None, recorder=None):
    settings = settings or load_config()
    if cv_folds is not None:
        settings = replace(settings, cv_folds=cv_folds)
    if tracking_uri:
        settings = replace(settings, tracking_uri=tracking_uri)
    name, pipeline, selection = train_candidates(X_train, y_train, settings=settings,
                                                 lineage=lineage, recorder=recorder)
    report = evaluate_selected_model(pipeline, selection, X_test, y_test, settings=settings, recorder=recorder)
    return name, pipeline, report


def save_artifacts(settings, pipeline, report, sources):
    manager = get_artifact_manager(settings)
    manifest = {key: value for key, value in report.items()
                if key not in ["confusion_matrix", "classification_report"]}
    manifest["metrics"] = {key: report[key] for key in
                           ["accuracy", "precision", "recall", "f1_score", "roc_auc"]}
    saved = manager.save_candidate(pipeline, manifest, report, input_schema(),
                                    settings.snapshot(), sources)
    MLflowTracker(settings).log_manifest(saved, settings.snapshot(), input_schema())
    return saved
