"""Create history, or adopt the existing SQLite history without replacing rows."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "predictions" not in inspector.get_table_names():
        op.create_table(
            "predictions",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("created_at", sa.Text, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("model_name", sa.Text, nullable=False),
            sa.Column("prediction", sa.Text, nullable=False),
            sa.Column("probability", sa.Float, nullable=False),
            sa.Column("risk_level", sa.Text, nullable=False),
            sa.Column("customer_payload", sa.Text, nullable=False),
            sa.Column("model_version", sa.Text),
        )
    elif "model_version" not in {c["name"] for c in inspector.get_columns("predictions")}:
        op.add_column("predictions", sa.Column("model_version", sa.Text))


def downgrade():
    raise RuntimeError("History migrations are forward-only to preserve prediction records")
