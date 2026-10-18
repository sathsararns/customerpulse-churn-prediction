"""Add event identity, customer tracing and prediction origin."""

import json
from uuid import uuid4
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"


def upgrade():
    op.add_column("predictions", sa.Column("event_id", sa.String(36)))
    op.add_column("predictions", sa.Column("customer_id", sa.String(128)))
    op.add_column("predictions", sa.Column("source", sa.String(16)))
    connection = op.get_bind()
    table = sa.table("predictions", sa.column("id"), sa.column("customer_payload"),
                     sa.column("event_id"), sa.column("customer_id"), sa.column("source"))
    for row in connection.execute(sa.select(table.c.id, table.c.customer_payload)).mappings():
        payload = json.loads(row["customer_payload"])
        customer_id = payload.get("customer_id") or payload.get("customerID")
        connection.execute(table.update().where(table.c.id == row["id"]).values(
            event_id=str(uuid4()), customer_id=str(customer_id) if customer_id is not None else None,
            source="legacy",
        ))
    with op.batch_alter_table("predictions") as batch:
        batch.alter_column("event_id", existing_type=sa.String(36), nullable=False)
        batch.alter_column("source", existing_type=sa.String(16), nullable=False)
        batch.create_unique_constraint("uq_predictions_event_id", ["event_id"])
        batch.create_check_constraint("ck_predictions_source", "source IN ('api', 'batch', 'stream', 'legacy')")
        batch.create_index("ix_predictions_customer_id", ["customer_id"])


def downgrade():
    raise RuntimeError("History migrations are forward-only to preserve prediction records")
