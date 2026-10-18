"""Predict a customer CSV with the active or explicitly requested model version."""

import argparse
import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd

from src.data_validation import validate_and_normalize
from src.model_inference import load_model_bundle
from src.db import init_db
from src.prediction_store import prediction_record, save_predictions, get_risk_level
from utils.config import load_config


def run_inference_pipeline(input_path=None, output_path=None, model_version=None,
                           output_dir=None, config_path=None, persist=True):
    settings = load_config(config_path, output_dir)
    # With no arguments, score the configured dataset as a local demonstration.
    source = Path(input_path or settings.data_path)
    data = pd.read_csv(source, dtype={"customerID": "string", "customer_id": "string", "event_id": "string"})
    if "customer_id" in data:
        if "customerID" in data and not data.customerID.equals(data.customer_id):
            raise ValueError("customerID and customer_id must agree")
        data["customerID"] = data.customer_id
    features, _ = validate_and_normalize(data, require_target=False)
    pipeline, manifest = load_model_bundle(settings.base_dir, model_version, settings=settings)
    probabilities = pipeline.predict_proba(features)[:, 1]
    payloads = json.loads(features.to_json(orient="records"))
    records = [prediction_record(
        manifest["best_model"],
        "Churn" if probability >= manifest["prediction_threshold"] else "Not Churn",
        round(float(probability), 4), get_risk_level(round(float(probability), 4)),
        payload, manifest["model_version"], source="batch",
        customer_id=data.iloc[index]["customerID"] if "customerID" in data else None,
        event_id=data.iloc[index]["event_id"] if "event_id" in data else None,
    ) for index, (probability, payload) in enumerate(zip(probabilities, payloads))]
    result = pd.DataFrame({
        "prediction": ["Churn" if value >= manifest["prediction_threshold"] else "Not Churn"
                       for value in probabilities],
        "probability": probabilities.round(4),
        "model": manifest["best_model"], "model_version": manifest["model_version"],
        "prediction_threshold": manifest["prediction_threshold"],
        "event_id": [record["event_id"] for record in records],
        "customer_id": [record["customer_id"] for record in records],
        "source": "batch", "risk_level": [record["risk_level"] for record in records],
    })
    if "customerID" in data:
        result.insert(0, "customerID", data["customerID"].to_numpy())
    destination = Path(output_path) if output_path else settings.base_dir / "artifacts" / "predictions" / f"{manifest['model_version']}.csv"
    if destination.resolve() == source.resolve():
        raise ValueError("Prediction output must not overwrite its input CSV")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if persist:
        init_db()
        save_predictions(records)
    result.to_csv(destination, index=False)
    print(f"Scored {len(result)} customers with {manifest['model_version']}: {destination}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", dest="input_path", type=Path)
    parser.add_argument("--output", dest="output_path", type=Path)
    parser.add_argument("--model-version")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--config", dest="config_path", type=Path)
    parser.add_argument("--no-history", dest="persist", action="store_false",
                        help="Export predictions without saving database history")
    run_inference_pipeline(**vars(parser.parse_args()))


if __name__ == "__main__":
    main()
