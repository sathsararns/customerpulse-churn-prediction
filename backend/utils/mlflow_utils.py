"""Shared experiment setup and logging of complete candidate pipelines."""

from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
from mlflow.models import ModelSignature
from mlflow.types import ColSpec, Schema
import numpy as np
import pandas as pd
import sklearn

from src.preprocessing import (
    BINARY_COLUMNS, CATEGORICAL_COLUMNS, CONTINUOUS_COLUMNS, normalize_features,
)
from utils.config import BACKEND_DIR


class MLflowTracker:
    def __init__(self, settings):
        directory = settings.base_dir / settings.artifacts_dir / "training"
        directory.mkdir(parents=True, exist_ok=True)
        self.settings = settings
        self.tracking_uri = settings.tracking_uri or f"sqlite:///{(directory / 'mlflow.db').as_posix()}"
        mlflow.set_tracking_uri(self.tracking_uri)
        if mlflow.get_experiment_by_name(settings.experiment_name) is None:
            artifact_root = settings.artifact_root
            if artifact_root and "://" not in artifact_root:
                artifact_root = Path(artifact_root).resolve().as_uri()
            if not artifact_root and not self.tracking_uri.startswith(("http://", "https://")):
                artifact_root = (directory / "mlartifacts").as_uri()
            mlflow.create_experiment(settings.experiment_name, artifact_location=artifact_root)
        mlflow.set_experiment(settings.experiment_name)

    def log_candidate(self, name, pipeline, classifier, cv_result, example, lineage):
        # Explicit doubles accommodate numeric missing values and avoid the
        # integer-schema warning. Normalization here learns no statistics.
        example = normalize_features(example)
        for column in CONTINUOUS_COLUMNS + BINARY_COLUMNS:
            example[column] = example[column].astype(float)
        signature = ModelSignature(
            inputs=Schema(
                [ColSpec("double", name=column, required=False)
                 for column in CONTINUOUS_COLUMNS + BINARY_COLUMNS]
                + [ColSpec("string", name=column, required=False)
                   for column in CATEGORICAL_COLUMNS]
            ),
            outputs=Schema([ColSpec("long")]),
        )
        with mlflow.start_run(run_name=f"{lineage['model_version']} | {name}") as run:
            mlflow.set_tags({key: value for key, value in lineage.items() if value is not None})
            mlflow.log_params({
                **classifier.get_params(), "model_name": name,
                "cv_folds": self.settings.cv_folds, "selection_metric": "cv_f1",
                "prediction_threshold": self.settings.prediction_threshold,
            })
            mlflow.log_metrics({"cv_f1_mean": cv_result["mean_f1"],
                                "cv_f1_std": cv_result["std_f1"]})
            mlflow.sklearn.log_model(
                pipeline, name="model", input_example=example, signature=signature,
                serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE,
                code_paths=[str(BACKEND_DIR / "src"), str(BACKEND_DIR / "utils")],
                pip_requirements=[f"scikit-learn=={sklearn.__version__}",
                                  f"pandas=={pd.__version__}", f"numpy=={np.__version__}",
                                  f"joblib=={joblib.__version__}"],
            )
            return run.info.run_id

    def log_evaluation(self, report):
        with mlflow.start_run(run_id=report["mlflow_run_id"]):
            mlflow.set_tag("selected_candidate", "true")
            mlflow.log_metrics({f"test_{key}": report[key] for key in
                               ["accuracy", "precision", "recall", "f1_score", "roc_auc"]})
            mlflow.log_dict(report, "evaluation_report.json")

    def log_manifest(self, manifest, config, schema):
        with mlflow.start_run(run_id=manifest["mlflow_run_id"]):
            mlflow.log_dict(manifest, "manifest.json")
            mlflow.log_dict(config, "config.json")
            mlflow.log_dict(schema, "input_schema.json")
