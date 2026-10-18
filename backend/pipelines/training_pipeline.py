"""One command to prepare data and save a complete, traceable model candidate."""

import argparse
from dataclasses import replace
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipelines.data_pipeline import load_prepared_data, run_data_pipeline
from src.model_training import train_and_select_best_model, save_artifacts
from utils.artifact_manager import get_artifact_manager, new_model_version, source_snapshot
from utils.config import load_config
from utils.run_status import RunRecorder


def run_training_pipeline(data_path=None, output_dir=None, cv_folds=None, tracking_uri=None,
                          config_path=None, dataset_version=None, activate=False):
    if data_path and dataset_version:
        raise ValueError("Choose --data-path or --dataset-version, not both")
    settings = load_config(config_path, output_dir)
    if data_path:
        settings = replace(settings, data_path=Path(data_path).resolve())
    if cv_folds is not None:
        settings = replace(settings, cv_folds=cv_folds)
    if tracking_uri:
        settings = replace(settings, tracking_uri=tracking_uri)
    version = new_model_version()
    recorder = RunRecorder(settings, version)
    try:
        with recorder.observe("data"):
            data = (load_prepared_data(dataset_version, settings) if dataset_version
                    else run_data_pipeline(data_path, settings=settings))
        sources, revision = source_snapshot()
        lineage = {
            "model_version": version, "dataset_version": data.metadata["dataset_version"],
            "dataset_sha256": data.metadata["dataset_sha256"],
            "normalized_sha256": data.metadata["normalized_sha256"],
            "git_commit": revision["git_commit"], "git_dirty": revision["git_dirty"],
            "source_sha256": revision["source_sha256"],
        }
        name, pipeline, report = train_and_select_best_model(
            data.X_train, data.y_train, data.X_test, data.y_test,
            settings=settings, lineage=lineage, recorder=recorder,
        )
        with recorder.observe("artifacts"):
            manifest = save_artifacts(settings, pipeline, report, sources)
        if activate:
            with recorder.observe("activation"):
                get_artifact_manager(settings).activate(version)
        else:
            recorder.skip_stage("activation", "Candidate awaiting explicit activation")
        recorder.complete(dataset_version=data.metadata["dataset_version"],
                          best_model=name, mlflow_run_id=report["mlflow_run_id"])
    except Exception as error:
        recorder.fail(error)
        raise
    print(f"Saved candidate: {version}", flush=True)
    print(f"Bundle: {settings.base_dir / manifest['model_path']}", flush=True)
    print(f"Selected {name} using CV F1; test F1: {report['f1_score']:.4f}", flush=True)
    print("Activated for inference" if activate else "Candidate saved; active model unchanged", flush=True)
    return name, pipeline, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--cv-folds", type=int)
    parser.add_argument("--tracking-uri")
    parser.add_argument("--config", dest="config_path", type=Path)
    parser.add_argument("--dataset-version")
    parser.add_argument("--activate", action="store_true")
    run_training_pipeline(**vars(parser.parse_args()))


if __name__ == "__main__":
    main()
