from pathlib import Path
import sys
import json
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))


def load_split_data(base_dir: Path):
    split_dir = base_dir / "data" / "processed" / "split_data"

    X_test = pd.read_csv(split_dir / "X_test.csv")
    y_test = pd.read_csv(split_dir / "y_test.csv").squeeze("columns")

    return X_test, y_test


def load_model(base_dir: Path, model_name: str):
    from src.model_inference import load_artifacts
    pipeline, saved_name = load_artifacts(base_dir)
    if model_name != saved_name:
        raise ValueError(f"Requested {model_name}, but the saved pipeline is {saved_name}")
    return pipeline


def evaluate(model, X_test, y_test, prediction_threshold=0.5):
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= prediction_threshold).astype(int)

    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1_score": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_prob),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, output_dict=True, zero_division=0),
    }


def save_report(base_dir: Path, metrics: dict):
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / "evaluation_report.json"
    # Preserve the CV selection evidence if evaluation is manually repeated.
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    report.update(metrics)
    from datetime import datetime, timezone
    report["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    print(f"Evaluation report saved to: {report_path}")


def main():
    import argparse
    from utils.artifact_manager import get_artifact_manager
    from utils.config import load_config

    parser = argparse.ArgumentParser(description="Repeat evaluation without changing saved bundles")
    parser.add_argument("--model-version")
    parser.add_argument("--output-dir")
    parser.add_argument("--config", dest="config_path")
    args = parser.parse_args()
    settings = load_config(args.config_path, args.output_dir)
    manager = get_artifact_manager(settings)
    pipeline, manifest = manager.load_model(args.model_version)
    if manifest["artifact_format"] == "sklearn_pipeline_v2":
        _, X_test, _, y_test, _ = manager.load_dataset(manifest["dataset_version"])
    else:
        X_test, y_test = load_split_data(settings.base_dir)
    print(json.dumps(evaluate(pipeline, X_test, y_test,
                              manifest["prediction_threshold"]), indent=2))


if __name__ == "__main__":
    main()
