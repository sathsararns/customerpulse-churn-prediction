"""Shared relational prediction schema; identifiers are tracing metadata."""

import sqlalchemy as sa

metadata = sa.MetaData()
predictions = sa.Table(
    "predictions", metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("created_at", sa.Text, nullable=False),
    sa.Column("model_name", sa.Text, nullable=False),
    sa.Column("prediction", sa.Text, nullable=False),
    sa.Column("probability", sa.Float, nullable=False),
    sa.Column("risk_level", sa.Text, nullable=False),
    sa.Column("customer_payload", sa.Text, nullable=False),
    sa.Column("model_version", sa.Text),
    sa.Column("event_id", sa.String(36), nullable=False),
    sa.Column("customer_id", sa.String(128)),
    sa.Column("source", sa.String(16), nullable=False),
    sa.UniqueConstraint("event_id", name="uq_predictions_event_id"),
    sa.CheckConstraint("source IN ('api', 'batch', 'stream', 'legacy')", name="ck_predictions_source"),
    sa.Index("ix_predictions_customer_id", "customer_id"),
)

# Persist the original inference decision before publishing to Kafka. Replays
# retain that decision, including its model version, across process restarts.
stream_inference_results = sa.Table(
    "stream_inference_results", metadata,
    sa.Column("event_id", sa.String(36), primary_key=True),
    sa.Column("input_sha256", sa.String(64), nullable=False),
    sa.Column("prediction_json", sa.Text, nullable=False),
)

stream_prediction_dimensions = sa.Table(
    "stream_prediction_dimensions", metadata,
    sa.Column("event_id", sa.String(36), sa.ForeignKey("predictions.event_id"), primary_key=True),
    sa.Column("contract_type", sa.String(32), nullable=False),
    sa.Column("internet_service", sa.String(32), nullable=False),
    sa.Column("tenure_band", sa.String(16), nullable=False),
)
