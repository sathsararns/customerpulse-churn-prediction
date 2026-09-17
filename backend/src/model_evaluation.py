from pathlib import Path
import sys
import json
import joblib
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
    model_path = base_dir / "models" / f"{model_name}.pkl"
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    return joblib.load(model_path)


def evaluate(model, X_test, y_test):
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1_score": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_prob),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
    }


def save_report(base_dir: Path, metrics: dict):
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / "evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)

    print(f"Evaluation report saved to: {report_path}")


def main():
    metrics_path = BASE_DIR / "reports" / "model_metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"Metrics file not found: {metrics_path}")

    with open(metrics_path, "r", encoding="utf-8") as f:
        report_info = json.load(f)

    best_model_name = report_info["best_model"]
    print(f"Best model from training: {best_model_name}")

    X_test, y_test = load_split_data(BASE_DIR)
    model = load_model(BASE_DIR, best_model_name)

    metrics = evaluate(model, X_test, y_test)

    print("\nEvaluation Results:")
    print(f"Accuracy : {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall   : {metrics['recall']:.4f}")
    print(f"F1 Score : {metrics['f1_score']:.4f}")
    print(f"ROC AUC  : {metrics['roc_auc']:.4f}")
    print("\nConfusion Matrix:")
    print(metrics["confusion_matrix"])

    save_report(BASE_DIR, metrics)


if __name__ == "__main__":
    main()