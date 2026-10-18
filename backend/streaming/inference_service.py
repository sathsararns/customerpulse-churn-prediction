"""Score customer-events with the same pinned model bundle served by FastAPI."""

from datetime import datetime, timezone
import json
import logging
import os
from urllib.request import urlopen

from src.db import init_db
from src.model_inference import load_model_bundle, predict_single
from src.prediction_store import get_risk_level
from src.stream_store import get_inference_result, remember_inference
from streaming.contracts import CustomerEvent, PredictionEvent
from streaming.runtime import StreamSettings, create_producer, publish_confirmed, run_consumer
from utils.config import load_config


def serving_version(api_url):
    with urlopen(api_url.rstrip("/") + "/model-info", timeout=3) as response:
        return json.load(response)["version"]


class StreamInference:
    def __init__(self, pipeline, manifest, publisher, settings, api_url=None):
        self.pipeline, self.manifest = pipeline, manifest
        self.publisher, self.settings, self.api_url = publisher, settings, api_url

    def predict_event(self, raw):
        event = CustomerEvent.model_validate_json(raw)
        event_id, fingerprint = str(event.event_id), event.fingerprint()
        cached = get_inference_result(event_id, fingerprint)
        if cached is not None:
            return cached
        if self.api_url and serving_version(self.api_url) != self.manifest["model_version"]:
            raise RuntimeError("API model changed; restarting inference to load its serving version")
        result = predict_single(self.pipeline, event.feature_values(), self.manifest["prediction_threshold"])
        prediction = PredictionEvent(
            event_id=event.event_id, customer_id=event.customer_id, occurred_at=event.occurred_at,
            predicted_at=datetime.now(timezone.utc), model=self.manifest["best_model"],
            model_version=self.manifest["model_version"],
            prediction_threshold=self.manifest["prediction_threshold"],
            risk_level=get_risk_level(result["probability"]), customer_payload=event.feature_values(), **result,
        ).model_dump(mode="json", exclude={"customer_payload": {"customer_id"}})
        return remember_inference(event_id, fingerprint, prediction)

    def __call__(self, raw):
        prediction = self.predict_event(raw)
        publish_confirmed(self.publisher, self.settings.prediction_topic, prediction["event_id"],
                          prediction, self.settings.delivery_timeout)


def main():
    settings, model_settings = StreamSettings.from_env(), load_config()
    init_db()
    api_url = os.getenv("STREAM_API_URL")
    version = serving_version(api_url) if api_url else None
    pipeline, manifest = load_model_bundle(model_settings.base_dir, version, settings=model_settings)
    logging.basicConfig(level=logging.INFO)
    logging.info("Stream inference loaded model %s", manifest["model_version"])
    publisher = create_producer(settings)
    handler = StreamInference(pipeline, manifest, publisher, settings, api_url)
    try:
        run_consumer(settings, settings.inference_group, settings.customer_topic, handler, "inference")
    finally:
        publisher.flush(settings.delivery_timeout)


if __name__ == "__main__":
    main()
