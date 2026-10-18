"""Serve one startup-loaded model and report the state actually used for inference."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sys
import time

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.schemas import CustomerInput, PredictionResponse
from src import db
from src.model_inference import load_model_bundle, predict_single
from src.prediction_store import save_prediction, get_recent_predictions, get_risk_level
from src.stream_store import stream_analytics
from utils.artifact_manager import get_artifact_manager
from utils.config import load_config
from utils.run_status import read_latest_run
from utils.service_health import probe_tracking

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application):
    settings = load_config(base_dir=BASE_DIR)
    state = application.state
    state.settings = settings
    state.started = time.monotonic()
    state.pipeline = None
    state.manifest = None
    state.evaluation = None
    state.model_error = None
    state.prediction_error = None
    state.database_error = None
    try:
        db.init_db()
    except Exception as error:
        logger.exception("Prediction database initialization failed")
        state.database_error = str(error)
    try:
        pipeline, manifest = load_model_bundle(BASE_DIR, settings=settings)
        # Pin the report to exactly the version loaded, even if activation changes.
        version = manifest["model_version"] if manifest["artifact_format"] == "sklearn_pipeline_v2" else None
        evaluation = get_artifact_manager(settings).get_evaluation(version)
        state.pipeline, state.manifest = pipeline, manifest
        state.evaluation = {**evaluation, "model_version": manifest["model_version"],
                            "prediction_threshold": manifest["prediction_threshold"]}
    except Exception as error:
        logger.exception("Selected model could not be loaded")
        state.model_error = str(error)
    yield
    state.pipeline = None


app = FastAPI(title="CustomerPulse AI", version="1.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"],
)


def require_model(request):
    state = request.app.state
    if state.pipeline is None:
        raise HTTPException(status_code=503, detail="Prediction model is unavailable. Select a valid model and restart the API.")
    return state


def selected_state(settings):
    try:
        return get_artifact_manager(settings).get_manifest()["model_version"], None
    except Exception as error:
        return None, str(error)


@app.get("/")
def root():
    return {"message": "CustomerPulse AI API is running"}


@app.get("/health")
def health(request: Request):
    state = request.app.state
    try:
        count = db.prediction_count()
        database_error = state.database_error
    except Exception as error:
        count, database_error = None, str(error)
    selected, selection_error = selected_state(state.settings)
    loaded = state.manifest["model_version"] if state.manifest else None
    ready = state.pipeline is not None and database_error is None and state.prediction_error is None
    return {
        "status": "ok" if ready and selection_error is None else "degraded",
        "ready": ready, "uptimeSeconds": round(time.monotonic() - state.started, 1),
        "version": app.version, "model_version": loaded, "selected_model_version": selected,
        "reload_required": loaded is not None and selected is not None and loaded != selected,
        "predictionCount": count,
        "services": {
            "model": {"status": "ready" if state.pipeline is not None else "unavailable",
                      "detail": state.model_error},
            "database": {"status": "connected" if database_error is None else "disconnected"},
            "selection": {"status": "valid" if selection_error is None else "invalid"},
        },
    }


@app.get("/mlflow-info")
def mlflow_info(request: Request):
    result = probe_tracking(request.app.state.settings)
    result["ui_url"] = os.getenv("MLFLOW_UI_URL", "http://127.0.0.1:8088")
    return result


@app.get("/model-info")
def model_info(request: Request):
    state = require_model(request)
    manifest = state.manifest
    display_name = manifest["best_model"].replace("_", " ").title()
    timestamp = manifest.get("updated_at")
    if not timestamp:
        timestamp = datetime.fromtimestamp(
            (BASE_DIR / manifest["model_path"]).stat().st_mtime, tz=timezone.utc
        ).isoformat()
    return {
        "name": f"{display_name} Churn Classifier", "version": manifest["model_version"],
        "predictionThreshold": manifest["prediction_threshold"],
        "trainingStatus": "trained", "lastUpdated": timestamp,
        "pipelineHealth": "healthy" if health(request)["status"] == "ok" else "degraded", "datasetSize": manifest["dataset_size"],
        "features": len(manifest["feature_names"]), "algorithm": display_name,
    }


@app.get("/metrics")
def metrics(request: Request):
    return require_model(request).evaluation


@app.get("/pipeline-status")
def pipeline_status(request: Request):
    state = request.app.state
    try:
        recorded = read_latest_run(state.settings)
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(status_code=503, detail="Recorded pipeline status is unavailable") from error
    selected, _ = selected_state(state.settings)
    return {"run": recorded,
            "serving_model_version": state.manifest["model_version"] if state.manifest else None,
            "selected_model_version": selected}


@app.get("/recent-predictions")
def recent_predictions(limit: int = Query(default=10, ge=1, le=100)):
    try:
        return {"items": get_recent_predictions(limit=limit)}
    except Exception as error:
        logger.exception("Prediction history is unavailable")
        raise HTTPException(status_code=503, detail="Prediction history is unavailable") from error


@app.get("/stream-analytics")
def get_stream_analytics():
    try:
        return stream_analytics()
    except Exception as error:
        logger.exception("Stream analytics is unavailable")
        raise HTTPException(status_code=503, detail="Stream analytics is unavailable") from error


@app.post("/predict", response_model=PredictionResponse)
def predict(customer: CustomerInput, request: Request):
    state = require_model(request)
    try:
        features = customer.model_dump(exclude={"customer_id"})
        result = predict_single(state.pipeline, features,
                                state.manifest["prediction_threshold"])
        risk_level = get_risk_level(result["probability"])
        event_id = save_prediction(
            model_name=state.manifest["best_model"], model_version=state.manifest["model_version"],
            prediction=result["prediction"], probability=result["probability"],
            risk_level=risk_level, customer_payload=features,
            customer_id=customer.customer_id, source="api",
        )
        state.prediction_error = None
        return {**result, "model": state.manifest["best_model"],
                "model_version": state.manifest["model_version"], "risk_level": risk_level,
                "event_id": event_id, "customer_id": customer.customer_id, "source": "api"}
    except Exception as error:
        state.prediction_error = str(error)
        logger.exception("Prediction failed")
        raise HTTPException(status_code=503, detail="Prediction could not be completed") from error
