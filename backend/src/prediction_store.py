"""Atomic, idempotent prediction history shared by API, batch and stream callers."""

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.db import get_engine
from src.db_models import predictions


class EventConflict(ValueError):
    """An immutable event ID was reused with different content."""


def get_risk_level(probability):
    return "High" if probability >= 0.7 else "Medium" if probability >= 0.4 else "Low"


def prediction_record(model_name, prediction, probability, risk_level, customer_payload,
                      model_version=None, *, customer_id=None, source="api", event_id=None):
    if source not in {"api", "batch", "stream"}:
        raise ValueError("Prediction source must be api, batch or stream")
    event_id = str(UUID(str(event_id))) if event_id else str(uuid4())
    if customer_id is not None:
        customer_id = str(customer_id).strip()
        if not customer_id or len(customer_id) > 128:
            raise ValueError("customer_id must contain 1 to 128 characters")
    return dict(event_id=event_id, customer_id=customer_id, source=source,
                model_name=model_name, model_version=model_version, prediction=prediction,
                probability=float(probability), risk_level=risk_level,
                created_at=datetime.now(timezone.utc).isoformat(),
                customer_payload=json.dumps(customer_payload, allow_nan=False, sort_keys=True))


def save_predictions(records, connection=None):
    """Commit a whole batch; replayed event IDs must describe the same prediction."""
    if not records:
        return
    if connection is None:
        with get_engine().begin() as transaction:
            save_predictions(records, connection=transaction)
        return
    insert = pg_insert if connection.dialect.name == "postgresql" else sqlite_insert
    for record in records:
        connection.execute(insert(predictions).values(**record).on_conflict_do_nothing(
            index_elements=["event_id"]))
        saved = connection.execute(select(predictions).where(
            predictions.c.event_id == record["event_id"])).mappings().one()
        if any(saved[key] != value for key, value in record.items() if key != "created_at"):
            raise EventConflict("event_id already belongs to a different prediction")


def save_prediction(model_name, prediction, probability, risk_level, customer_payload,
                    model_version=None, *, customer_id=None, source="api", event_id=None):
    record = prediction_record(model_name, prediction, probability, risk_level, customer_payload,
                               model_version, customer_id=customer_id, source=source, event_id=event_id)
    save_predictions([record])
    return record["event_id"]


def get_recent_predictions(limit=10):
    with get_engine().connect() as connection:
        rows = connection.execute(select(predictions).order_by(predictions.c.id.desc()).limit(limit)).mappings().all()
    result = []
    for row in rows:
        timestamp = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        result.append({**dict(row), "created_at": timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                       "customer_payload": json.loads(row["customer_payload"])})
    return result
