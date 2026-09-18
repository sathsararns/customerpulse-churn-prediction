from pathlib import Path
import sys
import json
import joblib
import pandas as pd
import mlflow
import mlflow.sklearn

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from src.model_building import build_models


MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
MLFLOW_EXPERIMENT_NAME = "CustomerPulse-AI"


def load_split_data(base_dir: Path):
    split_dir = base_dir / "data" / "processed" / "split_data"

    X_train = pd.read_csv(split_dir / "X_train.csv")
    X_test = pd.read_csv(split_dir / "X_test.csv")
    y_train = pd.read_csv(split_dir / "y_train.csv").squeeze("columns")
    y_test = pd.read_csv(split_dir / "y_test.csv").squeeze("columns")

    return X_train, X_test, y_train, y_test


def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1_score": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_prob),
    }


def train_and_select_best_model(X_train, y_train, X_test, y_test):
    models = build_models()

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    best_model_name = None
    best_model = None
    best_metrics = None
    best_f1 = -1

    for name, model in models.items():
        print(f"\nTraining model: {name}")

        with mlflow.start_run(run_name=name):
            mlflow.log_param("model_name", name)
            mlflow.log_params(model.get_params())

            model.fit(X_train, y_train)
            metrics = evaluate_model(model, X_test, y_test)

            print(f"Accuracy : {metrics['accuracy']:.4f}")
            print(f"Precision: {metrics['precision']:.4f}")
            print(f"Recall   : {metrics['recall']:.4f}")
            print(f"F1 Score : {metrics['f1_score']:.4f}")
            print(f"ROC AUC  : {metrics['roc_auc']:.4f}")

            mlflow.log_metrics(metrics)
            mlflow.sklearn.log_model(
                model,
                name="model",
                serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE,
            )

            if metrics["f1_score"] > best_f1:
                best_f1 = metrics["f1_score"]
                best_model_name = name
                best_model = model
                best_metrics = metrics

    return best_model_name, best_model, best_metrics


def save_artifacts(base_dir: Path, model, model_name: str, metrics: dict):
    models_dir = base_dir / "models"
    reports_dir = base_dir / "reports"

    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / f"{model_name}.pkl"
    metrics_path = reports_dir / "model_metrics.json"

    joblib.dump(model, model_path)

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "best_model": model_name,
                "metrics": metrics,
            },
            f,
            indent=4
        )

    print(f"\nBest model saved to: {model_path}")
    print(f"Metrics saved to: {metrics_path}")


def main():
    X_train, X_test, y_train, y_test = load_split_data(BASE_DIR)

    best_model_name, best_model, best_metrics = train_and_select_best_model(
        X_train, y_train, X_test, y_test
    )

    print(f"\nBest model selected: {best_model_name}")
    print("Best metrics:", best_metrics)

    save_artifacts(BASE_DIR, best_model, best_model_name, best_metrics)


if __name__ == "__main__":
    main()
