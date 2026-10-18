"""Retry-safe version handoffs for manual Airflow tasks or a local approval run."""

import argparse
from io import BytesIO
import json
from pathlib import Path
import sys
from uuid import uuid4

import joblib
import pandas as pd

from pipelines.data_pipeline import load_prepared_data, run_data_pipeline
from src.data_validation import validate_and_normalize
from src.model_training import train_candidates, evaluate_selected_model, save_artifacts
from utils.acceptance_gate import CandidateRejected, apply_acceptance_gate, promote_candidate
from utils.artifact_manager import get_artifact_manager, sha256_bytes, sha256_file, source_snapshot, write_json
from utils.config import load_config
from utils.file_lock import exclusive_lock
from utils.run_status import RunRecorder

STAGES = [("validation", "Validate dataset"), ("data", "Prepare versioned splits"),
          ("training", "Train candidates using CV"), ("evaluation", "Evaluate selected candidate"),
          ("gate", "Apply acceptance gate"), ("activation", "Publish approved version")]


def _config_checksum(settings):
    return sha256_bytes(json.dumps(settings.snapshot(), sort_keys=True).encode())


def _directory(settings, version):
    return get_artifact_manager(settings)._version_dir("workflows", version)


def _phase(context, settings, stage, operation):
    directory = _directory(settings, context["model_version"])
    with exclusive_lock(directory / "task.lock"):
        state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
        saved = state["context"]
        if saved["config_sha256"] != _config_checksum(settings):
            raise ValueError("Workflow configuration changed; start a new run")
        for key in ["model_version", "dataset_version", "gate_id"]:
            if key in context and context[key] != saved.get(key):
                raise ValueError(f"Workflow version handoff mismatch: {key}")
        if stage in state["completed"]:
            return saved
        index = [name for name, _ in STAGES].index(stage)
        if any(name not in state["completed"] for name, _ in STAGES[:index]):
            raise ValueError(f"Workflow prerequisites missing before {stage}")
        recorder = RunRecorder.resume(settings, saved["model_version"], STAGES)
        try:
            with recorder.observe(stage):
                saved.update(operation(saved, directory) or {})
            state["completed"].append(stage)
            write_json(directory / "state.json", state)
            if stage == "activation":
                recorder.complete(dataset_version=saved["dataset_version"], gate_id=saved["gate_id"])
        except Exception as error:
            recorder.fail(error)
            raise
        return saved


def validate_dataset(settings, data_path=None, run_key=None):
    run_key = run_key or str(uuid4())
    version = "churn-wf-" + sha256_bytes(run_key.encode())[:24]
    directory = _directory(settings, version)
    directory.mkdir(parents=True, exist_ok=True)
    # A run key identifies one immutable input snapshot and one model version.
    with exclusive_lock(directory / "initialize.lock"):
        state_path = directory / "state.json"
        if not state_path.exists():
            write_json(state_path, {"context": {"model_version": version, "run_key": run_key,
                                                "config_sha256": _config_checksum(settings)}, "completed": []})
        elif json.loads(state_path.read_text(encoding="utf-8"))["context"]["run_key"] != run_key:
            raise ValueError("Workflow run key collision")
    def validate(context, root):
        snapshot = root / "validated_source.csv"
        if not snapshot.exists():
            content = Path(data_path or settings.data_path).read_bytes()
            # Save only after validation succeeds. No fitted transformations here.
            validate_and_normalize(pd.read_csv(BytesIO(content)))
            snapshot.write_bytes(content)
        content = snapshot.read_bytes()
        validate_and_normalize(pd.read_csv(BytesIO(content)))
        return {"dataset_sha256": sha256_bytes(content), "source_snapshot": str(snapshot)}
    return _phase({"model_version": version}, settings, "validation", validate)


def prepare_splits(context, settings):
    def prepare(saved, directory):
        source = Path(saved["source_snapshot"])
        if sha256_file(source) != saved["dataset_sha256"]:
            raise ValueError("Validated input snapshot changed")
        data = run_data_pipeline(source, settings=settings)
        if data.metadata["dataset_sha256"] != saved["dataset_sha256"]:
            raise ValueError("Prepared data does not match validated input")
        return {"dataset_version": data.metadata["dataset_version"]}
    return _phase(context, settings, "data", prepare)


def train_candidate(context, settings):
    def train(saved, directory):
        staging = directory / "trained"
        data = load_prepared_data(saved["dataset_version"], settings)
        if staging.exists():
            metadata = json.loads((staging / "metadata.json").read_text(encoding="utf-8"))
            get_artifact_manager(settings)._verify_files(staging, metadata["files"])
            if metadata["dataset_version"] != saved["dataset_version"]:
                raise ValueError("Trained candidate dataset mismatch")
            return {"mlflow_run_id": metadata["mlflow_run_id"]}
        sources, revision = source_snapshot()
        lineage = {"model_version": saved["model_version"], "dataset_version": saved["dataset_version"],
                   "dataset_sha256": data.metadata["dataset_sha256"],
                   "normalized_sha256": data.metadata["normalized_sha256"], **revision}
        _, pipeline, selection = train_candidates(data.X_train, data.y_train, settings=settings, lineage=lineage)
        temporary = directory / (".trained-" + uuid4().hex)
        temporary.mkdir()
        joblib.dump(pipeline, temporary / "pipeline.joblib")
        write_json(temporary / "selection.json", selection)
        for name, content in sources.items():
            path = temporary / "source" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        files = {path.relative_to(temporary).as_posix(): sha256_file(path) for path in temporary.rglob("*") if path.is_file()}
        write_json(temporary / "metadata.json", {"files": files, "dataset_version": saved["dataset_version"],
                                                 "mlflow_run_id": selection["mlflow_run_id"]})
        temporary.rename(staging)
        return {"mlflow_run_id": selection["mlflow_run_id"]}
    return _phase(context, settings, "training", train)


def evaluate_candidate(context, settings):
    def evaluate(saved, directory):
        manager = get_artifact_manager(settings)
        final = manager._version_dir("models", saved["model_version"])
        if final.exists():
            manager.load_model(saved["model_version"])
            if manager.get_manifest(saved["model_version"])["dataset_version"] != saved["dataset_version"]:
                raise ValueError("Evaluated candidate dataset mismatch")
            return {}
        staging = directory / "trained"
        metadata = json.loads((staging / "metadata.json").read_text(encoding="utf-8"))
        manager._verify_files(staging, metadata["files"])
        data = load_prepared_data(saved["dataset_version"], settings)
        selection = json.loads((staging / "selection.json").read_text(encoding="utf-8"))
        pipeline = joblib.load(staging / "pipeline.joblib")
        report = evaluate_selected_model(pipeline, selection, data.X_test, data.y_test, settings=settings)
        source_root = staging / "source"
        sources = {path.relative_to(source_root).as_posix(): path.read_bytes() for path in source_root.rglob("*") if path.is_file()}
        save_artifacts(settings, pipeline, report, sources)
        return {}
    return _phase(context, settings, "evaluation", evaluate)


def apply_gate(context, settings):
    def gate(saved, directory):
        receipt = apply_acceptance_gate(settings, saved["model_version"])
        return {"gate_id": receipt["gate_id"]}
    return _phase(context, settings, "gate", gate)


def publish_approved(context, settings):
    def publish(saved, directory):
        promote_candidate(settings, saved["model_version"], saved["gate_id"])
        return {"published_model_version": saved["model_version"]}
    return _phase(context, settings, "activation", publish)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["run", "validate", "prepare", "train", "evaluate", "gate", "publish"])
    parser.add_argument("--context-json")
    parser.add_argument("--data-path")
    parser.add_argument("--run-key")
    parser.add_argument("--config")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    settings = load_config(args.config, args.output_dir)
    try:
        if args.phase in {"validate", "run"}:
            result = validate_dataset(settings, args.data_path, args.run_key)
            if args.phase == "run":
                for operation in [prepare_splits, train_candidate, evaluate_candidate, apply_gate, publish_approved]:
                    result = operation(result, settings)
        else:
            if not args.context_json:
                parser.error("This task requires an explicit --context-json version handoff")
            context = json.loads(args.context_json)
            operation = {"prepare": prepare_splits, "train": train_candidate, "evaluate": evaluate_candidate,
                         "gate": apply_gate, "publish": publish_approved}[args.phase]
            result = operation(context, settings)
    except CandidateRejected as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(3)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
    print("WORKFLOW_RESULT=" + json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
