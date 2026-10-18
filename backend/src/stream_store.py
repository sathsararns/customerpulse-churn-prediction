"""Durable replay protection and analytics built from unique stream events."""

import json
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.db import get_engine
from src.db_models import predictions, stream_inference_results as decisions, stream_prediction_dimensions as dimensions
from src.prediction_store import EventConflict, save_predictions


def _insert(connection, table):
    return (pg_insert if connection.dialect.name == "postgresql" else sqlite_insert)(table)


def get_inference_result(event_id, input_sha256):
    with get_engine().connect() as connection:
        row = connection.execute(select(decisions).where(decisions.c.event_id == event_id)).mappings().one_or_none()
    if row is None:
        return None
    if row["input_sha256"] != input_sha256:
        raise EventConflict("event_id already belongs to different customer input")
    return json.loads(row["prediction_json"])


def remember_inference(event_id, input_sha256, prediction):
    with get_engine().begin() as connection:
        connection.execute(_insert(connection, decisions).values(
            event_id=event_id, input_sha256=input_sha256,
            prediction_json=json.dumps(prediction, sort_keys=True, allow_nan=False),
        ).on_conflict_do_nothing(index_elements=["event_id"]))
        row = connection.execute(select(decisions).where(decisions.c.event_id == event_id)).mappings().one()
        if row["input_sha256"] != input_sha256:
            raise EventConflict("event_id already belongs to different customer input")
        return json.loads(row["prediction_json"])


def tenure_band(months):
    return "0-12" if months <= 12 else "13-24" if months <= 24 else "25-48" if months <= 48 else "49+"


def save_stream_prediction(record):
    payload = json.loads(record["customer_payload"])
    values = dict(event_id=record["event_id"], contract_type=payload["Contract"],
                  internet_service=payload["InternetService"], tenure_band=tenure_band(payload["tenure"]))
    with get_engine().begin() as connection:
        save_predictions([record], connection=connection)
        connection.execute(_insert(connection, dimensions).values(**values).on_conflict_do_nothing(
            index_elements=["event_id"]))
        saved = connection.execute(select(dimensions).where(dimensions.c.event_id == record["event_id"])).mappings().one()
        if dict(saved) != values:
            raise EventConflict("event_id already belongs to different analytics dimensions")


def stream_analytics():
    names = ["contract_type", "internet_service", "tenure_band"]
    columns = [dimensions.c[name] for name in names] + [predictions.c.model_version, predictions.c.risk_level]
    # One query gives every dimension the same snapshot while events arrive.
    query = select(*columns, func.count().label("count"), func.sum(predictions.c.probability).label("probability_sum"))
    query = query.select_from(dimensions.join(predictions, dimensions.c.event_id == predictions.c.event_id)).group_by(*columns)
    with get_engine().connect() as connection:
        rows = connection.execute(query).mappings().all()
    groups = {}
    for name in names:
        totals = {}
        for row in rows:
            key = (row[name], row["model_version"], row["risk_level"])
            count, total = totals.get(key, (0, 0.0))
            totals[key] = count + row["count"], total + row["probability_sum"]
        groups[name] = [{"value": key[0], "model_version": key[1], "risk_level": key[2],
                         "count": count, "mean_probability": round(total / count, 4)}
                        for key, (count, total) in sorted(totals.items())]
    count = sum(row["count"] for row in rows)
    return {"total_predictions": count, "source": "stream", "tenure_unit": "months", "groups": groups}
