"""The application supplies a connection so credentials never enter an ini file."""

from alembic import context
from src.db_models import metadata

connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Run migrations with python -m src.db")
context.configure(connection=connection, target_metadata=metadata, render_as_batch=True)
with context.begin_transaction():
    context.run_migrations()
