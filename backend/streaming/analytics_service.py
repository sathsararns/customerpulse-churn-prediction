"""Persist stream history and risk dimensions atomically before committing Kafka."""

from src.db import init_db
from src.prediction_store import prediction_record
from src.stream_store import save_stream_prediction
from streaming.contracts import PredictionEvent
from streaming.runtime import StreamSettings, run_consumer


def process_prediction(raw):
    event = PredictionEvent.model_validate_json(raw)
    record = prediction_record(
        event.model, event.prediction, event.probability, event.risk_level,
        event.customer_payload.model_dump(exclude={"customer_id"}), event.model_version,
        customer_id=event.customer_id, source="stream", event_id=event.event_id,
    )
    # Preserve scoring time across delayed delivery and replay.
    record["created_at"] = event.predicted_at.isoformat()
    save_stream_prediction(record)


def main():
    settings = StreamSettings.from_env()
    init_db()
    run_consumer(settings, settings.analytics_group, settings.prediction_topic, process_prediction, "analytics")


if __name__ == "__main__":
    main()
