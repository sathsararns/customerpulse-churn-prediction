"""Audited quality gates and atomic promotion that preserves the serving model."""

from dataclasses import asdict
import json
import math

from utils.artifact_manager import get_artifact_manager, sha256_bytes, sha256_file, utc_now, write_json
from utils.file_lock import exclusive_lock


class CandidateRejected(ValueError):
    pass


def policy_checksum(settings):
    return sha256_bytes(json.dumps(asdict(settings.acceptance), sort_keys=True).encode())


def active_reference(manager):
    pointer = manager.root / "active_model.json"
    if pointer.exists():
        manifest = manager.get_manifest()
        return manifest, sha256_file(pointer)
    legacy = manager.base_dir / "reports" / "model_metrics.json"
    if legacy.exists():
        return manager.get_manifest(), sha256_file(legacy)
    return None, None


def assess_metrics(report, policy, reference=None):
    checks = []
    for metric, minimum in [("f1_score", policy.min_f1), ("recall", policy.min_recall),
                             ("precision", policy.min_precision), ("roc_auc", policy.min_roc_auc)]:
        value = report.get(metric)
        valid = type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1
        checks.append({"check": metric, "passed": bool(valid and value + 1e-12 >= minimum),
                       "observed": value if valid else None, "minimum": minimum})
    if reference is not None:
        for metric, tolerance in [("f1_score", policy.max_f1_drop), ("recall", policy.max_recall_drop)]:
            previous = reference.get(metric)
            value = report.get(metric)
            valid = all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in [previous, value])
            checks.append({"check": "approved_" + metric + "_regression", "passed": bool(valid and value + tolerance + 1e-12 >= previous),
                           "observed": value if valid else None, "reference": previous if valid else None,
                           "max_drop": tolerance})
    return checks


def _validate_report(report, manifest):
    for name in ["model_version", "dataset_version", "prediction_threshold"]:
        if report.get(name) != manifest.get(name):
            raise CandidateRejected(f"Candidate report/manifest mismatch: {name}")
    matrix = report.get("confusion_matrix")
    if (not isinstance(matrix, list) or len(matrix) != 2 or any(not isinstance(row, list) or len(row) != 2 for row in matrix)
            or any(type(value) is not int or value < 0 for row in matrix for value in row)):
        raise CandidateRejected("A valid binary confusion matrix is required")
    tn, fp, fn, tp = matrix[0] + matrix[1]
    if sum(matrix[0]) == 0 or sum(matrix[1]) == 0 or tn + fp + fn + tp != report.get("test_rows"):
        raise CandidateRejected("Holdout must contain both classes and match the recorded test rows")
    precision, recall = tp / (tp + fp) if tp + fp else 0, tp / (tp + fn)
    expected = {"precision": precision, "recall": recall,
                "f1_score": 2 * precision * recall / (precision + recall) if precision + recall else 0,
                "accuracy": (tp + tn) / (tp + tn + fp + fn)}
    for name, value in expected.items():
        observed = report.get(name)
        if type(observed) not in (int, float) or not math.isfinite(observed) or not math.isclose(observed, value, abs_tol=1e-9):
            raise CandidateRejected(f"Holdout metric does not match confusion matrix: {name}")


def apply_acceptance_gate(settings, model_version):
    manager = get_artifact_manager(settings)
    directory = manager._version_dir("models", model_version)
    manifest = manager.get_manifest(model_version)
    manager._verify_files(directory, manifest["files"])
    report = manager.get_evaluation(model_version)
    _validate_report(report, manifest)
    _, X_test, _, y_test, dataset = manager.load_dataset(manifest["dataset_version"])
    if len(X_test) != report["test_rows"] or len(y_test) != report["test_rows"] or dataset["dataset_sha256"] != manifest["dataset_sha256"]:
        raise CandidateRejected("Evaluation dataset provenance does not match the candidate")
    current, reference_checksum = active_reference(manager)
    reference = manager.get_evaluation() if current else None
    checks = assess_metrics(report, settings.acceptance, reference)
    if current and settings.acceptance.require_same_dataset:
        checks.append({"check": "same_evaluation_dataset", "passed": manifest["dataset_version"] == current.get("dataset_version"),
                       "candidate": manifest["dataset_version"], "reference": current.get("dataset_version")})
    receipt = {
        "model_version": model_version, "dataset_version": manifest["dataset_version"],
        "passed": all(check["passed"] for check in checks), "checks": checks,
        "policy": asdict(settings.acceptance), "policy_sha256": policy_checksum(settings),
        "manifest_sha256": sha256_file(directory / "manifest.json"),
        "reference_model_version": current["model_version"] if current else None,
        "reference_pointer_sha256": reference_checksum, "checked_at": utc_now(),
    }
    receipt["gate_id"] = sha256_bytes(json.dumps(receipt, sort_keys=True, allow_nan=False).encode())
    write_json(manager._version_dir("gates", model_version) / f"{receipt['gate_id']}.json", receipt)
    write_json(manager._version_dir("gates", model_version) / "latest.json", {"gate_id": receipt["gate_id"]})
    if not receipt["passed"]:
        failed = ", ".join(check["check"] for check in checks if not check["passed"])
        raise CandidateRejected(f"Candidate {model_version} failed acceptance: {failed}; approved model unchanged")
    return receipt


def promote_candidate(settings, model_version, gate_id=None):
    manager = get_artifact_manager(settings)
    with exclusive_lock(manager.root / "promotion.lock"):
        if gate_id is None:
            receipt = apply_acceptance_gate(settings, model_version)
        else:
            if len(gate_id) != 64 or any(c not in "0123456789abcdef" for c in gate_id):
                raise CandidateRejected("Invalid gate receipt ID")
            receipt = json.loads((manager._version_dir("gates", model_version) / f"{gate_id}.json").read_text(encoding="utf-8"))
            digest = sha256_bytes(json.dumps({k: v for k, v in receipt.items() if k != "gate_id"}, sort_keys=True, allow_nan=False).encode())
            if digest != gate_id or receipt.get("model_version") != model_version or not receipt.get("passed"):
                raise CandidateRejected("Invalid or rejected gate receipt")
        if receipt["policy_sha256"] != policy_checksum(settings):
            raise CandidateRejected("Acceptance policy changed; rerun the gate")
        path = manager._version_dir("models", model_version) / "manifest.json"
        if sha256_file(path) != receipt["manifest_sha256"]:
            raise CandidateRejected("Candidate changed after acceptance")
        current, pointer_checksum = active_reference(manager)
        if current and current["model_version"] == model_version:
            # Repair a retry after pointer replacement but before report/audit writes.
            manager.load_model(model_version)
            manager._write_compatibility_reports(current)
            write_json(manager._version_dir("gates", model_version) / "publication.json",
                       {"model_version": model_version, "gate_id": receipt["gate_id"], "published_at": utc_now()})
            return current
        if pointer_checksum != receipt["reference_pointer_sha256"]:
            raise CandidateRejected("Approved reference changed; rerun the gate")
        # _activate verifies every bundle file before the atomic pointer replace.
        manifest = manager._activate(model_version)
        write_json(manager._version_dir("gates", model_version) / "publication.json",
                   {"model_version": model_version, "gate_id": receipt["gate_id"], "published_at": utc_now()})
        return manifest
