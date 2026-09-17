from pathlib import Path
from datetime import datetime, timezone
import sys
import json

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from app.schemas import CustomerInput
from src.model_inference import load_artifacts, predict_single

app = FastAPI(title="CustomerPulse AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "CustomerPulse AI API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/model-info")
def model_info():
    metrics_path = BASE_DIR / "reports" / "model_metrics.json"
    train_x_path = BASE_DIR / "data" / "processed" / "split_data" / "X_train.csv"
    test_x_path = BASE_DIR / "data" / "processed" / "split_data" / "X_test.csv"
    scaler_path = BASE_DIR / "artifacts" / "scaler.pkl"

    if not metrics_path.exists():
        raise HTTPException(status_code=404, detail="Model metrics not found")

    with open(metrics_path, "r", encoding="utf-8") as f:
        report_info = json.load(f)

    best_model_name = report_info.get("best_model", "unknown")
    model_path = BASE_DIR / "models" / f"{best_model_name}.pkl"

    train_rows = len(pd.read_csv(train_x_path)) if train_x_path.exists() else 0
    test_rows = len(pd.read_csv(test_x_path)) if test_x_path.exists() else 0
    feature_count = (
        len(pd.read_csv(train_x_path, nrows=1).columns) if train_x_path.exists() else 0
    )
    last_updated = datetime.fromtimestamp(
        metrics_path.stat().st_mtime, tz=timezone.utc
    ).isoformat()

    return {
        "name": f"{best_model_name.replace('_', ' ').title()} — Churn Classifier",
        "version": app.version,
        "algorithm": best_model_name,
        "trainingStatus": "trained" if model_path.exists() else "idle",
        "pipelineHealth": "healthy" if model_path.exists() and scaler_path.exists() else "degraded",
        "lastUpdated": last_updated,
        "datasetSize": train_rows + test_rows,
        "features": feature_count,
    }


@app.get("/metrics")
def metrics():
    evaluation_path = BASE_DIR / "reports" / "evaluation_report.json"
    if not evaluation_path.exists():
        raise HTTPException(status_code=404, detail="Evaluation report not found")

    with open(evaluation_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["updated_at"] = datetime.fromtimestamp(
        evaluation_path.stat().st_mtime, tz=timezone.utc
    ).isoformat()
    return data


@app.post("/predict")
def predict(customer: CustomerInput):
    try:
        model, scaler, train_columns, model_name = load_artifacts(BASE_DIR)
        result = predict_single(model, scaler, train_columns, customer.model_dump())
        return {
            "model": model_name,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))