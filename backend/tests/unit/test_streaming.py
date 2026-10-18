"""Failure-boundary tests: publish, database commit, offset commit and replay."""

from datetime import datetime, timezone
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sklearn.linear_model import LogisticRegression

from src.db import init_db, prediction_count
from src.model_inference import predict_single
from src.prediction_store import EventConflict, get_recent_predictions
from src.preprocessing import build_pipeline
from src.stream_store import stream_analytics, tenure_band
from streaming.analytics_service import process_prediction
from streaming.contracts import CustomerEvent, PredictionEvent
from streaming.inference_service import StreamInference
from streaming.producer_service import replay_events
from streaming.runtime import StreamSettings, process_message


class Message:
    def __init__(self, value):
        self.raw = value
    def value(self): return self.raw
    def key(self): return b"key"
    def topic(self): return "input"
    def partition(self): return 0
    def offset(self): return 3


class Producer:
    def __init__(self, actions, fail=False):
        self.actions, self.fail = actions, fail
    def produce(self, topic, key, value, on_delivery):
        self.actions.append(("publish", topic, json.loads(value)))
        self.callback = on_delivery
    def flush(self, timeout):
        if self.fail:
            return 1
        self.actions.append("ack")
        self.callback(None, None)
        return 0


class Consumer:
    def __init__(self, actions, fail=False):
        self.actions, self.fail = actions, fail
    def commit(self, **kwargs):
        self.actions.append("commit")
        assert kwargs["asynchronous"] is False
        if self.fail:
            raise RuntimeError("Offset commit failed after processing")
        return []


@pytest.fixture
def stream_case(customers):
    X, y = customers
    init_db()
    pipeline = build_pipeline(LogisticRegression()).fit(X, y)
    manifest = {"model_version": "version-a", "best_model": "logistic_regression", "prediction_threshold": 0.5}
    raw = json.dumps({"event_id": str(uuid4()), "customer_id": "00001",
                      "occurred_at": datetime.now(timezone.utc).isoformat(), "features": X.iloc[1].to_dict()}).encode()
    return pipeline, manifest, raw


def test_inference_matches_offline_and_keeps_original_result_after_restart(stream_case):
    pipeline, manifest, raw = stream_case
    settings = StreamSettings()
    handler = StreamInference(pipeline, manifest, None, settings)
    first = handler.predict_event(raw)
    offline = predict_single(pipeline, CustomerEvent.model_validate_json(raw).feature_values())
    assert first["probability"] == offline["probability"]
    assert first["prediction"] == offline["prediction"]
    assert "Churn" not in first["customer_payload"] and "customer_id" not in first["customer_payload"]
    class UnusablePipeline:
        def predict_proba(self, _): raise AssertionError("Replay must use the durable decision")
    restarted = StreamInference(UnusablePipeline(), {**manifest, "model_version": "version-b"}, None, settings)
    assert restarted.predict_event(raw) == first
    changed = json.loads(raw)
    changed["features"]["tenure"] += 1
    with pytest.raises(EventConflict):
        restarted.predict_event(json.dumps(changed))


def test_cache_survives_failed_prediction_publish(stream_case):
    pipeline, manifest, raw = stream_case
    actions = []
    handler = StreamInference(pipeline, manifest, Producer(actions, fail=True), StreamSettings())
    with pytest.raises(RuntimeError, match="confirm delivery"):
        handler(raw)
    first = actions[0][2]
    handler = StreamInference(None, {}, Producer(actions), StreamSettings())
    handler(raw)
    assert actions[-2][2] == first


def test_database_replay_after_failed_offset_commit_does_not_double_count(stream_case):
    pipeline, manifest, raw = stream_case
    prediction = StreamInference(pipeline, manifest, None, StreamSettings()).predict_event(raw)
    message, actions = Message(json.dumps(prediction).encode()), []
    with pytest.raises(RuntimeError, match="Offset commit failed"):
        process_message(message, process_prediction, Consumer(actions, fail=True), Producer(actions),
                        StreamSettings(), "analytics")
    process_message(message, process_prediction, Consumer(actions), Producer(actions), StreamSettings(), "analytics")
    assert prediction_count() == 1
    row = get_recent_predictions()[0]
    assert row["source"] == "stream" and row["customer_id"] == "00001"
    analytics = stream_analytics()
    assert analytics["total_predictions"] == 1
    for groups in analytics["groups"].values():
        assert sum(group["count"] for group in groups) == 1


def test_invalid_prediction_customer_id_is_a_permanent_validation_error(stream_case):
    pipeline, manifest, raw = stream_case
    prediction = StreamInference(pipeline, manifest, None, StreamSettings()).predict_event(raw)
    prediction["customer_id"] = " "
    with pytest.raises(ValidationError):
        PredictionEvent.model_validate(prediction)


def test_invalid_event_is_committed_only_after_dead_letter_ack():
    actions = []
    def invalid(raw): CustomerEvent.model_validate_json(raw)
    process_message(Message(b"bad-json"), invalid, Consumer(actions), Producer(actions), StreamSettings(), "inference")
    assert actions[0][0] == "publish" and actions[0][1] == "customerpulse-dead-letter"
    assert actions[1:] == ["ack", "commit"]
    assert actions[0][2]["original_offset"] == 3


def test_dead_letter_failure_leaves_offset_uncommitted():
    actions = []
    def invalid(raw): CustomerEvent.model_validate_json(raw)
    with pytest.raises(RuntimeError):
        process_message(Message(b"bad-json"), invalid, Consumer(actions), Producer(actions, fail=True),
                        StreamSettings(), "inference")
    assert "commit" not in actions


def test_transient_outage_retries_and_leaves_offset_uncommitted():
    actions, attempts = [], []
    def offline(raw):
        attempts.append(raw)
        raise ConnectionError("Database offline")
    with pytest.raises(ConnectionError):
        process_message(Message(b"event"), offline, Consumer(actions), Producer(actions),
                        StreamSettings(), "analytics", sleep=lambda _: None)
    assert len(attempts) == 3
    assert actions == []


def test_input_target_is_rejected_and_replay_excludes_targets(stream_case, customers, tmp_path):
    _, _, raw = stream_case
    payload = json.loads(raw)
    payload["features"]["Churn"] = "Yes"
    with pytest.raises(ValidationError):
        CustomerEvent.model_validate(payload)
    X, y = customers
    path = tmp_path / "source.csv"
    X.assign(customerID=[f"{i:05d}" for i in X.index], Churn=y.map({0: "No", 1: "Yes"})).to_csv(path, index=False)
    replay_id = uuid4()
    first, second = list(replay_events(path, replay_id, limit=2)), list(replay_events(path, replay_id, limit=2))
    assert [v["event_id"] for v in first] == [v["event_id"] for v in second]
    assert first[0]["customer_id"] == "00000"
    assert "Churn" not in first[0]["features"] and "customerID" not in first[0]["features"]
    assert first[0]["features"]["TotalCharges"] is None


@pytest.mark.parametrize("months,band", [(0,"0-12"),(12,"0-12"),(13,"13-24"),(24,"13-24"),
                                         (25,"25-48"),(48,"25-48"),(49,"49+")])
def test_tenure_bands_use_months(months, band):
    assert tenure_band(months) == band
