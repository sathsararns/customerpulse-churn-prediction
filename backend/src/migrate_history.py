"""Copy legacy SQLite history into DATABASE_URL without deleting the source."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import NAMESPACE_URL, uuid5
from sqlalchemy.engine import make_url

from src.db import database_url, init_db, prediction_count
from src.prediction_store import save_predictions


def import_sqlite(path):
    source = Path(path).resolve()
    target = make_url(database_url())
    if target.get_backend_name() == "sqlite" and Path(target.database).resolve() == source:
        raise ValueError("Source and target databases must be different")
    # Read-only even when the source has not received the new schema migration.
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM predictions ORDER BY id").fetchall()
    records = []
    for row in rows:
        row = dict(row)
        payload = json.loads(row["customer_payload"])
        stable_id = f"customerpulse:sqlite:{row['id']}:{row['created_at']}:{row['model_name']}:{row['customer_payload']}"
        timestamp = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        records.append({key: row[key] for key in ["model_name", "prediction", "probability", "risk_level"]} | {
            "model_version": row.get("model_version"),
            "event_id": row.get("event_id") or str(uuid5(NAMESPACE_URL, stable_id)),
            "customer_id": row.get("customer_id") or payload.get("customer_id") or payload.get("customerID"),
            "source": row.get("source") or "legacy",
            "created_at": timestamp.astimezone(timezone.utc).isoformat(),
            "customer_payload": json.dumps(payload, allow_nan=False, sort_keys=True),
        })
    init_db()
    before = prediction_count()
    save_predictions(records)
    added = prediction_count() - before
    print(f"Read {len(records)} legacy records; added {added}; source unchanged")
    return added


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", required=True, type=Path)
    import_sqlite(parser.parse_args().sqlite)
