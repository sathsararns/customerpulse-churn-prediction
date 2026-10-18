"""SQLAlchemy storage and versioned migrations for PostgreSQL or local SQLite."""

from functools import lru_cache
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url

from src.db_models import predictions

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "customerpulse.db"


def database_url():
    value = os.getenv("DATABASE_URL")
    if not value:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{DB_PATH.resolve().as_posix()}"
    url = make_url(value)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    if url.get_backend_name() not in {"postgresql", "sqlite"}:
        raise ValueError("DATABASE_URL must use PostgreSQL or SQLite")
    return url.render_as_string(hide_password=False)


@lru_cache(maxsize=8)
def _engine(url):
    sqlite = make_url(url).get_backend_name() == "sqlite"
    return create_engine(url, pool_pre_ping=True, connect_args=(
        {"timeout": 5, "check_same_thread": False} if sqlite else {"connect_timeout": 3}
    ))


def get_engine():
    return _engine(database_url())


def init_db():
    """Upgrade in one transaction; serialize PostgreSQL startup migrations."""
    config = Config()
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    with get_engine().begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql("SELECT pg_advisory_xact_lock(754123890)")
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def prediction_count():
    with get_engine().connect() as connection:
        return connection.scalar(select(func.count()).select_from(predictions))


if __name__ == "__main__":
    init_db()
    print("Prediction database migrated to the latest revision")
