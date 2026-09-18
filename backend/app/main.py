from datetime import datetime, timezone
from pathlib import Path
import csv
import sys
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from app.schemas import CustomerInput
from src.model_inference import load_artifacts, predict_single
from src.prediction_store import save_prediction, get_recent_predictions
from src.db import init_db

app = FastAPI(title="CustomerPulse AI", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def root():
    return {"message": "CustomerPulse AI API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/mlflow-info")
def mlflow_info():
    return {
        "status": "connected",
        "experiment_name": "CustomerPulse-AI",
        "tracking_uri": "http://127.0.0.1:5000",
        "ui_url": "http://127.0.0.1:5000",
    }


@app.get("/model-info")
def model_info():
    metrics_path = BASE_DIR / "reports" / "model_metrics.json"
    train_x_path = BASE_DIR / "data" / "processed" / "split_data" / "X_train.csv"

    if not metrics_path.exists():
        raise HTTPException(status_code=404, detail="Model metrics not found")

    with open(metrics_path, "r", encoding="utf-8") as f:
        report_info = json.load(f)

    best_model_name = report_info["best_model"]
    model_path = BASE_DIR / "models" / f"{best_model_name}.pkl"

    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model artifact not found")
    if not train_x_path.exists():
        raise HTTPException(status_code=404, detail="Training data not found")

    with open(train_x_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        feature_count = len(next(reader))
        dataset_size = sum(1 for _ in reader)

    last_updated = datetime.fromtimestamp(model_path.stat().st_mtime, tz=timezone.utc).isoformat()
    display_name = best_model_name.replace("_", " ").title()

    return {
        "name": f"{display_name} Churn Classifier",
        "version": app.version,
        "trainingStatus": "trained",
        "lastUpdated": last_updated,
        "pipelineHealth": "healthy",
        "datasetSize": dataset_size,
        "features": feature_count,
        "algorithm": display_name,
    }


@app.get("/metrics")
def metrics():
    evaluation_path = BASE_DIR / "reports" / "evaluation_report.json"
    if not evaluation_path.exists():
        raise HTTPException(status_code=404, detail="Evaluation report not found")

    with open(evaluation_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/recent-predictions")
def recent_predictions(limit: int = 10):
    items = get_recent_predictions(limit=limit)
    return {"items": items}


@app.post("/predict")
def predict(customer: CustomerInput):
    try:
        model, scaler, train_columns, model_name = load_artifacts(BASE_DIR)
        result = predict_single(model, scaler, train_columns, customer.model_dump())

        probability = float(result["probability"])

        if probability >= 0.7:
            risk_level = "High"
        elif probability >= 0.4:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        save_prediction(
            model_name=model_name,
            prediction=result["prediction"],
            probability=probability,
            risk_level=risk_level,
            customer_payload=customer.model_dump(),
        )

        return {
            "model": model_name,
            "prediction": result["prediction"],
            "probability": probability,
            "risk_level": risk_level,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    try:
        model, scaler, train_columns, model_name = load_artifacts(BASE_DIR)
        result = predict_single(model, scaler, train_columns, customer.model_dump())

        probability = float(result["probability"])

        if probability >= 0.7:
            risk_level = "High"
        elif probability >= 0.4:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        save_prediction(
            model_name=model_name,
            prediction=result["prediction"],
            probability=probability,
            risk_level=risk_level,
            customer_payload=customer.model_dump(),
        )

        return {
            "model": model_name,
            "prediction": result["prediction"],
            "probability": probability,
            "risk_level": risk_level,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))