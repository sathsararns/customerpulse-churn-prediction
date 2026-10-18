"""Durable inference decisions and one analytics dimension row per event."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"


def upgrade():
    op.create_table(
        "stream_inference_results",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("prediction_json", sa.Text, nullable=False),
    )
    op.create_table(
        "stream_prediction_dimensions",
        sa.Column("event_id", sa.String(36), sa.ForeignKey("predictions.event_id"), primary_key=True),
        sa.Column("contract_type", sa.String(32), nullable=False),
        sa.Column("internet_service", sa.String(32), nullable=False),
        sa.Column("tenure_band", sa.String(16), nullable=False),
    )


def downgrade():
    raise RuntimeError("Stream migrations are forward-only to preserve event decisions")
