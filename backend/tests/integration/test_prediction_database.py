"""Run on SQLite, plus PostgreSQL when TEST_POSTGRES_URL is configured."""

import hashlib
import os
import sqlite3
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from src import db
from src.migrate_history import import_sqlite
from src.prediction_store import get_recent_predictions, prediction_record, save_prediction, save_predictions


@pytest.fixture(params=["sqlite", "postgresql"])
def history_database(request, monkeypatch):
    if request.param == "sqlite":
        yield
        return
    url = os.getenv("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set TEST_POSTGRES_URL to run against PostgreSQL")
    engine = create_engine(url)
    schema = "test_history_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = make_url(url).update_query_dict({"options": f"-csearch_path={schema}"})
    monkeypatch.setenv("DATABASE_URL", scoped_url.render_as_string(hide_password=False))
    try:
        yield
    finally:
        db.get_engine().dispose()
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_migrations_replays_conflicts_and_restart_persistence(history_database):
    db.init_db()
    db.init_db()
    assert {c["name"] for c in inspect(db.get_engine()).get_columns("predictions")} >= {
        "event_id", "customer_id", "source", "model_version",
    }
    event = str(uuid4())
    args = ("classifier", "Churn", 0.8, "High", {"tenure": 1}, "version-a")
    save_prediction(*args, customer_id="00001", source="stream", event_id=event)
    save_prediction(*args, customer_id="00001", source="stream", event_id=event)
    assert db.prediction_count() == 1
    with pytest.raises(ValueError, match="different prediction"):
        save_prediction(*args, customer_id="another-customer", source="stream", event_id=event)
    # An error in a later row must roll back the entire batch.
    records = [prediction_record(*args, source="batch"),
               prediction_record(*args, source="batch", event_id=event)]
    with pytest.raises(ValueError):
        save_predictions(records)
    assert db.prediction_count() == 1
    db.get_engine().dispose()
    db.init_db()
    row = get_recent_predictions()[0]
    assert row["event_id"] == event
    assert row["customer_id"] == "00001"
    assert row["source"] == "stream"
    assert row["model_version"] == "version-a"
    assert row["created_at"].endswith("Z")


def test_legacy_sqlite_import_is_repeatable_and_preserves_source(history_database, tmp_path):
    source = tmp_path / "legacy-source.db"
    with sqlite3.connect(source) as connection:
        connection.execute("""CREATE TABLE predictions (
            id INTEGER PRIMARY KEY, created_at TEXT, model_name TEXT, prediction TEXT,
            probability REAL, risk_level TEXT, customer_payload TEXT)""")
        connection.execute("""INSERT INTO predictions VALUES
            (1, '2026-10-17 10:00:00', 'old', 'Churn', 0.8, 'High', '{"customerID":"00001"}')""")
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    assert import_sqlite(source) == 1
    assert import_sqlite(source) == 0
    assert hashlib.sha256(source.read_bytes()).hexdigest() == checksum
    row = get_recent_predictions()[0]
    assert row["customer_id"] == "00001"
    assert row["source"] == "legacy"
    assert row["model_version"] is None


def test_stream_cache_and_analytics_are_idempotent_in_both_databases(history_database):
    from src.stream_store import remember_inference, get_inference_result, save_stream_prediction, stream_analytics
    db.init_db()
    event = str(uuid4())
    result = {"model_version": "version-a", "probability": 0.8}
    assert remember_inference(event, "a" * 64, result) == result
    assert remember_inference(event, "a" * 64, {"model_version": "version-b"}) == result
    assert get_inference_result(event, "a" * 64) == result
    record = prediction_record("model", "Churn", 0.8, "High",
                               {"Contract": "One year", "InternetService": "DSL", "tenure": 13},
                               "version-a", event_id=event, customer_id="00001", source="stream")
    save_stream_prediction(record)
    save_stream_prediction(record)
    assert db.prediction_count() == 1
    summary = stream_analytics()
    assert summary["total_predictions"] == 1
    assert summary["groups"]["tenure_band"][0]["value"] == "13-24"
    assert summary["groups"]["contract_type"][0]["count"] == 1
