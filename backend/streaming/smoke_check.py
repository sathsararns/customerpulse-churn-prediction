"""Check real Kafka replay, DLQ, API parity and PostgreSQL deduplication."""

import argparse
import base64
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen
from uuid import uuid4

from confluent_kafka import ConsumerGroupState, ConsumerGroupTopicPartitions, TopicPartition
from confluent_kafka.admin import AdminClient
from sqlalchemy import select

from src.db import get_engine
from src.db_models import predictions
from src.stream_store import stream_analytics
from streaming.producer_service import replay_events
from streaming.runtime import StreamSettings, create_consumer, create_producer, publish_confirmed
from utils.config import load_config


def request_json(url, payload=None):
    request = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def wait_for_commits(settings, timeout=90):
    probes = [(create_consumer(settings, group), topic) for group, topic in [
        (settings.inference_group, settings.customer_topic), (settings.analytics_group, settings.prediction_topic)]]
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            complete = True
            for consumer, topic in probes:
                metadata = consumer.list_topics(topic, timeout=5)
                partitions = [TopicPartition(topic, p) for p in metadata.topics[topic].partitions]
                for position in consumer.committed(partitions, timeout=5):
                    _, high = consumer.get_watermark_offsets(position, timeout=5)
                    if max(0, position.offset) < high:
                        complete = False
            if complete:
                return
            time.sleep(1)
        raise AssertionError("Stream consumer offsets did not catch up")
    finally:
        for consumer, _ in probes:
            consumer.close()


def selected_rows(event_ids):
    with get_engine().connect() as connection:
        rows = connection.execute(select(predictions).where(predictions.c.event_id.in_(event_ids))).mappings().all()
    assert len(rows) == len(event_ids), f"Expected {len(event_ids)} unique rows, found {len(rows)}"
    assert all(row["source"] == "stream" for row in rows)
    return sorted([dict(row) for row in rows], key=lambda row: row["event_id"])


def check_dead_letter(settings, bad_id):
    consumer = create_consumer(settings, "smoke-dlq-" + str(uuid4()))
    consumer.subscribe([settings.dead_letter_topic])
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            message = consumer.poll(1)
            if message is None:
                continue
            if message.error():
                raise RuntimeError(str(message.error()))
            dead = json.loads(message.value())
            original = json.loads(base64.b64decode(dead["value_base64"]))
            if original.get("event_id") == bad_id:
                assert dead["stage"] == "inference"
                return dead["dead_letter_id"]
        raise AssertionError("Invalid event did not reach the dead-letter topic")
    finally:
        consumer.close()


def rewind_analytics(settings):
    """The CLI can print an error with exit 0; verify offsets with the client API."""
    admin = AdminClient({"bootstrap.servers": settings.bootstrap_servers})
    group = settings.analytics_group
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        description = admin.describe_consumer_groups([group])[group].result(timeout=10)
        if description.state == ConsumerGroupState.EMPTY:
            break
        time.sleep(1)
    else:
        raise AssertionError("Stop analytics and wait for its consumer group to become empty")
    probe = create_consumer(settings, "smoke-offset-probe-" + str(uuid4()))
    try:
        topic = settings.prediction_topic
        metadata = probe.list_topics(topic, timeout=10)
        offsets = []
        for partition in metadata.topics[topic].partitions:
            low, _ = probe.get_watermark_offsets(TopicPartition(topic, partition), timeout=5)
            offsets.append(TopicPartition(topic, partition, low))
        result = admin.alter_consumer_group_offsets([ConsumerGroupTopicPartitions(group, offsets)])[group].result(timeout=15)
        assert all(not position.error for position in result.topic_partitions)
        checked = admin.list_consumer_group_offsets([ConsumerGroupTopicPartitions(group)])[group].result(timeout=15)
        actual = {(position.topic, position.partition): position.offset for position in checked.topic_partitions}
        assert all(actual[(position.topic, position.partition)] == position.offset for position in offsets)
        return [{"partition": position.partition, "offset": position.offset} for position in offsets]
    finally:
        probe.close()


def main(phase, api_url):
    settings, model_settings = StreamSettings.from_env(), load_config()
    path = model_settings.base_dir / "artifacts" / "phase5-stream-verification.json"
    if phase == "rewind":
        state = json.loads(path.read_text(encoding="utf-8"))
        state["rewound_offsets"] = rewind_analytics(settings)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(json.dumps({"phase": phase, "verified_offsets": state["rewound_offsets"]}), flush=True)
        return
    if phase == "prepare":
        replay_id, bad_id = str(uuid4()), str(uuid4())
        state = {"replay_id": replay_id, "bad_event_id": bad_id,
                 "baseline_stream_count": stream_analytics()["total_predictions"]}
    else:
        state = json.loads(path.read_text(encoding="utf-8"))
    from uuid import UUID
    events = list(replay_events(model_settings.data_path, UUID(state["replay_id"]), limit=5))
    producer = create_producer(settings)
    try:
        for event in events:
            publish_confirmed(producer, settings.customer_topic, event["event_id"], event)
        if phase == "prepare":
            publish_confirmed(producer, settings.customer_topic, state["bad_event_id"],
                              {"event_id": state["bad_event_id"], "features": {"Churn": "Yes"}})
    finally:
        producer.flush(20)
    wait_for_commits(settings)
    rows = selected_rows([event["event_id"] for event in events])
    analytics = stream_analytics()
    assert analytics["total_predictions"] == state["baseline_stream_count"] + 5
    for groups in analytics["groups"].values():
        assert sum(group["count"] for group in groups) == analytics["total_predictions"]
    if phase == "prepare":
        state["dead_letter_id"] = check_dead_letter(settings, state["bad_event_id"])
        first = next(row for row in rows if row["event_id"] == events[0]["event_id"])
        api = request_json(api_url + "/predict", {**events[0]["features"], "customer_id": events[0]["customer_id"]})
        assert api["model_version"] == first["model_version"]
        assert api["probability"] == first["probability"]
        assert api["risk_level"] == first["risk_level"] and api["prediction"] == first["prediction"]
        state["rows"] = rows
        state["analytics"] = analytics
        state["api_stream_probability_equal"] = True
    else:
        assert state.get("rewound_offsets"), "The deliberate analytics offset rewind was not verified"
        assert rows == state["rows"], "Replay changed persisted prediction records"
        assert analytics == state["analytics"], "Replay double-counted analytics"
        state["consumer_restart_and_offset_replay_verified"] = True
    recent = request_json(api_url + "/recent-predictions?limit=100")["items"]
    assert {row["event_id"] for row in rows}.issubset({row["event_id"] for row in recent})
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps({"phase": phase, "stream_rows": len(rows), "total_stream_predictions": analytics["total_predictions"],
                      "replay_id": state["replay_id"], "report": str(path)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "rewind", "verify"])
    parser.add_argument("--api-url", default="http://frontend:8080/api")
    arguments = parser.parse_args()
    main(arguments.phase, arguments.api_url.rstrip("/"))
