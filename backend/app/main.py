from pathlib import Path
import sys
import json

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
    if not metrics_path.exists():
        raise HTTPException(status_code=404, detail="Model metrics not found")

    with open(metrics_path, "r", encoding="utf-8") as f:
        report_info = json.load(f)

    return report_info


@app.get("/metrics")
def metrics():
    evaluation_path = BASE_DIR / "reports" / "evaluation_report.json"
    if not evaluation_path.exists():
        raise HTTPException(status_code=404, detail="Evaluation report not found")

    with open(evaluation_path, "r", encoding="utf-8") as f:
        return json.load(f)


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