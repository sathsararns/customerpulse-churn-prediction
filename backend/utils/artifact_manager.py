"""Versioned local storage boundary for datasets and fitted model bundles."""

import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Protocol
from uuid import uuid4

import joblib
import pandas as pd

from utils.config import BACKEND_DIR, load_config

METRIC_NAMES = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(content):
    return hashlib.sha256(content).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def source_snapshot():
    files = {}
    for directory in ["src", "pipelines", "utils", "app", "migrations", "streaming", "deployment"]:
        for path in sorted((BACKEND_DIR / directory).rglob("*.py")):
            files[path.relative_to(BACKEND_DIR).as_posix()] = path.read_bytes()
    for name in ["requirements.txt", "requirements-streaming.txt", "constraints.txt", "config.yaml"]:
        files[name] = (BACKEND_DIR / name).read_bytes()
    digest = hashlib.sha256()
    for name, content in sorted(files.items()):
        digest.update(name.encode() + b"\0" + content)
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BACKEND_DIR,
                                  capture_output=True, text=True, timeout=10, check=False)
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=normal",
                                 "--", "src", "pipelines", "utils", "app",
                                 "requirements.txt", "config.yaml"],
                                cwd=BACKEND_DIR, capture_output=True, text=True,
                                timeout=10, check=False)
        commit = revision.stdout.strip() if revision.returncode == 0 else None
        dirty = bool(status.stdout.strip()) if status.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        commit, dirty = None, None
    return files, {"git_commit": commit or os.getenv("GIT_REVISION") or None,
                   "git_dirty": dirty, "source_sha256": digest.hexdigest()}


def new_model_version():
    return "churn-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8]


class ArtifactManager(Protocol):
    """A future storage provider must preserve these bundle and selection semantics."""

    def save_candidate(self, pipeline, manifest, report, schema, config, sources): ...
    def load_model(self, model_version=None): ...
    def get_manifest(self, model_version=None): ...
    def get_evaluation(self, model_version=None): ...
    def activate(self, model_version): ...
    def save_dataset(self, version, files, metadata): ...
    def load_dataset(self, version): ...
    def list_versions(self): ...


class LocalArtifactManager:
    def __init__(self, base_dir, artifacts_dir="artifacts", settings=None):
        self.base_dir = Path(base_dir).resolve()
        self.root = (self.base_dir / artifacts_dir).resolve()
        self.settings = settings or load_config(base_dir=self.base_dir)
        if not self.root.is_relative_to(self.base_dir):
            raise ValueError("Artifact root must stay inside the output directory")

    def _version_dir(self, kind, version):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", version) or ".." in version:
            raise ValueError("Invalid artifact version")
        return self.root / kind / version

    @staticmethod
    def _child(root, name):
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Artifact file must stay inside its version directory")
        return path

    def save_dataset(self, version, files, metadata):
        destination = self._version_dir("datasets", version)
        if destination.exists():
            saved = self.get_dataset_metadata(version)
            expected = {name: sha256_bytes(content) for name, content in files.items()}
            if saved["files"] != expected:
                raise ValueError("Existing dataset version has different content")
            self._verify_files(destination, saved["files"])
            return saved
        staging = destination.parent / (".incomplete-" + uuid4().hex)
        staging.mkdir(parents=True)
        for name, content in files.items():
            path = self._child(staging, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        metadata = {**metadata, "dataset_version": version,
                    "files": {name: sha256_bytes(content) for name, content in files.items()}}
        write_json(staging / "metadata.json", metadata)
        staging.rename(destination)
        return metadata

    def get_dataset_metadata(self, version):
        return json.loads((self._version_dir("datasets", version) / "metadata.json").read_text())

    def load_dataset(self, version):
        directory = self._version_dir("datasets", version)
        metadata = self.get_dataset_metadata(version)
        self._verify_files(directory, metadata["files"])
        frames = [pd.read_csv(BytesIO((directory / name).read_bytes()), float_precision="round_trip")
                  for name in ["X_train.csv", "X_test.csv", "y_train.csv", "y_test.csv"]]
        return frames[0], frames[1], frames[2].squeeze("columns"), frames[3].squeeze("columns"), metadata

    def save_candidate(self, pipeline, manifest, report, schema, config, sources):
        version = manifest["model_version"]
        destination = self._version_dir("models", version)
        if destination.exists():
            raise FileExistsError(f"Model version already exists: {version}")
        staging = destination.parent / (".incomplete-" + uuid4().hex)
        staging.mkdir(parents=True)
        joblib.dump(pipeline, staging / "pipeline.joblib")
        write_json(staging / "evaluation_report.json", report)
        write_json(staging / "input_schema.json", schema)
        write_json(staging / "config.json", config)
        for name, content in sources.items():
            path = self._child(staging / "source", name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        checksums = {path.relative_to(staging).as_posix(): sha256_file(path)
                     for path in sorted(staging.rglob("*")) if path.is_file()}
        manifest = {**manifest, "artifact_format": "sklearn_pipeline_v2",
                    "model_path": (destination / "pipeline.joblib").relative_to(self.base_dir).as_posix(),
                    "files": checksums}
        write_json(staging / "manifest.json", manifest)
        staging.rename(destination)
        return manifest

    def get_manifest(self, model_version=None):
        if model_version is None:
            pointer = self.root / "active_model.json"
            if pointer.exists():
                selection = json.loads(pointer.read_text())
                model_version = selection["model_version"]
                manifest_path = self._version_dir("models", model_version) / "manifest.json"
                if sha256_file(manifest_path) != selection["manifest_sha256"]:
                    raise ValueError("Active model manifest checksum mismatch")
            else:
                # Phase 1 compatibility: keep the currently served model usable
                # until a versioned candidate is explicitly activated.
                legacy_path = self.base_dir / "reports" / "model_metrics.json"
                if not legacy_path.exists():
                    raise FileNotFoundError("No model selected. Train with --activate or activate a candidate.")
                manifest = json.loads(legacy_path.read_text())
                if manifest.get("artifact_format") != "sklearn_pipeline_v1":
                    raise ValueError("Legacy model artifacts require retraining")
                return {**manifest, "prediction_threshold": 0.5, "model_version": "phase1"}
        directory = self._version_dir("models", model_version)
        manifest = json.loads((directory / "manifest.json").read_text())
        if manifest.get("artifact_format") != "sklearn_pipeline_v2" or manifest["model_version"] != model_version:
            raise ValueError("Model manifest does not match the requested version")
        return manifest

    @staticmethod
    def _verify_files(directory, checksums):
        for name, checksum in checksums.items():
            path = LocalArtifactManager._child(directory, name)
            if sha256_file(path) != checksum:
                raise ValueError(f"Artifact checksum mismatch: {name}")

    def load_model(self, model_version=None):
        manifest = self.get_manifest(model_version)
        if manifest["artifact_format"] == "sklearn_pipeline_v1":
            path = self._child(self.base_dir, manifest["model_path"])
        else:
            directory = self._version_dir("models", manifest["model_version"])
            # Never pair a classifier with preprocessing from a different run.
            self._verify_files(directory, manifest["files"])
            path = directory / "pipeline.joblib"
        pipeline = joblib.load(path)
        if "preprocessor" not in getattr(pipeline, "named_steps", {}):
            raise ValueError("Expected a complete fitted preprocessing/model pipeline")
        return pipeline, manifest

    def get_evaluation(self, model_version=None):
        manifest = self.get_manifest(model_version)
        if manifest["artifact_format"] == "sklearn_pipeline_v1":
            path = self.base_dir / "reports" / "evaluation_report.json"
        else:
            path = self._version_dir("models", manifest["model_version"]) / "evaluation_report.json"
            self._verify_files(path.parent, {"evaluation_report.json": manifest["files"]["evaluation_report.json"]})
        return json.loads(path.read_text())

    def activate(self, model_version):
        """Every public promotion path enforces the configured acceptance gate."""
        from utils.acceptance_gate import promote_candidate
        return promote_candidate(self.settings, model_version)

    def _activate(self, model_version):
        """Internal pointer update; callers must hold the promotion lock and pass gates."""
        _, manifest = self.load_model(model_version)
        path = self._version_dir("models", model_version) / "manifest.json"
        write_json(self.root / "active_model.json", {
            "model_version": model_version, "manifest_sha256": sha256_file(path),
            "activated_at": utc_now(),
        })
        self._write_compatibility_reports(manifest)
        return manifest

    def _write_compatibility_reports(self, manifest):
        model_version = manifest["model_version"]
        # Compatibility reports for existing scripts; serving reads the pinned bundle.
        write_json(self.base_dir / "reports" / "model_metrics.json", manifest)
        write_json(self.base_dir / "reports" / "evaluation_report.json", self.get_evaluation(model_version))
        from utils.run_status import record_activation
        record_activation(self.root, model_version)

    def list_versions(self):
        return sorted(path.parent.name for path in (self.root / "models").glob("*/manifest.json")
                      if not path.parent.name.startswith("."))


def get_artifact_manager(settings):
    if settings.storage_backend != "local":
        raise NotImplementedError("Only local artifact storage is implemented")
    return LocalArtifactManager(settings.base_dir, settings.artifacts_dir, settings=settings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["list", "activate"])
    parser.add_argument("version", nargs="?")
    parser.add_argument("--config", dest="config_path")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    manager = get_artifact_manager(load_config(args.config_path, args.output_dir))
    if args.action == "list":
        print("\n".join(manager.list_versions()) or "No versioned candidates")
    elif args.version:
        print(json.dumps(manager.activate(args.version), indent=2))
    else:
        parser.error("activate requires a version")


if __name__ == "__main__":
    main()
