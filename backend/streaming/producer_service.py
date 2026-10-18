"""Replay raw telecom customers; keep one replay UUID to resume without duplicates."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from uuid import UUID, uuid4, uuid5

import pandas as pd

from src.preprocessing import FEATURE_COLUMNS, normalize_features
from streaming.contracts import CustomerEvent
from streaming.runtime import StreamSettings, create_producer, publish_confirmed
from utils.config import load_config


def replay_events(path, replay_id, limit=10, start=0):
    if limit < 1 or start < 0:
        raise ValueError("limit must be positive and start must be non-negative")
    data = pd.read_csv(path, dtype={"customerID": "string"})
    if start >= len(data):
        raise ValueError("start is outside the dataset")
    selected = data.iloc[start:start + limit]
    normalized = normalize_features(selected)
    features = json.loads(normalized.to_json(orient="records", double_precision=15))
    for offset, values in enumerate(features, start=start):
        for name in ["tenure", "SeniorCitizen"]:
            value = values[name]
            if value is not None and float(value).is_integer():
                values[name] = int(value)
        raw_id = data.iloc[offset].get("customerID")
        customer_id = None if pd.isna(raw_id) else str(raw_id).strip()
        event = CustomerEvent(
            event_id=uuid5(replay_id, str(offset)), customer_id=customer_id,
            occurred_at=datetime.now(timezone.utc), features={name: values[name] for name in FEATURE_COLUMNS},
        )
        yield event.model_dump(mode="json", exclude={"features": {"customer_id"}})


def replay(path=None, replay_id=None, limit=10, start=0, interval=0.5, settings=None):
    if interval < 0:
        raise ValueError("interval must be non-negative")
    replay_id = UUID(str(replay_id)) if replay_id else uuid4()
    settings = settings or StreamSettings.from_env()
    producer = create_producer(settings)
    print(f"Replay ID: {replay_id}; reuse it with the same input to replay the same events", flush=True)
    count = 0
    try:
        for event in replay_events(path or load_config().data_path, replay_id, limit, start):
            for attempt in range(settings.attempts):
                try:
                    publish_confirmed(producer, settings.customer_topic, event["event_id"], event,
                                      settings.delivery_timeout)
                    break
                except Exception:
                    if attempt + 1 == settings.attempts:
                        raise
                    time.sleep(settings.retry_delay * 2 ** attempt)
            count += 1
            print(f"Published {event['event_id']} for {event['customer_id']}", flush=True)
            if interval:
                time.sleep(interval)
    finally:
        producer.flush(settings.delivery_timeout)
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", dest="path", type=Path)
    parser.add_argument("--replay-id", type=UUID)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--interval", type=float, default=0.5)
    replay(**vars(parser.parse_args()))
