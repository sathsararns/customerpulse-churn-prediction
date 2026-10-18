"""Load a pinned complete pipeline and apply its recorded decision threshold."""

from pathlib import Path

import pandas as pd

from utils.artifact_manager import get_artifact_manager
from utils.config import load_config


def load_model_bundle(base_dir: Path, model_version=None, settings=None):
    settings = settings or load_config(base_dir=base_dir)
    return get_artifact_manager(settings).load_model(model_version)


def load_model_metadata(base_dir: Path, model_version=None):
    return get_artifact_manager(load_config(base_dir=base_dir)).get_manifest(model_version)


def load_artifacts(base_dir: Path, model_version=None):
    pipeline, manifest = load_model_bundle(base_dir, model_version)
    return pipeline, manifest["best_model"]


def predict_single(pipeline, input_data: dict, prediction_threshold=0.5):
    probability = float(pipeline.predict_proba(pd.DataFrame([input_data]))[0][1])
    return {
        "prediction": "Churn" if probability >= prediction_threshold else "Not Churn",
        "probability": round(probability, 4),
    }
