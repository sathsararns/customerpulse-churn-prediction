"""Bounded, read-only connectivity checks for the configured tracking store."""

import json
from pathlib import Path
import sqlite3
from urllib.request import Request, urlopen

from sqlalchemy.engine import make_url

from utils.artifact_manager import utc_now


def tracking_uri(settings):
    path = settings.base_dir / settings.artifacts_dir / "training" / "mlflow.db"
    return settings.tracking_uri or f"sqlite:///{path.as_posix()}"


def probe_tracking(settings, timeout=2.0):
    uri = tracking_uri(settings)
    result = {
        "status": "disconnected", "experiment_name": settings.experiment_name,
        "tracking_uri": uri, "checked_at": utc_now(), "detail": None,
    }
    try:
        if uri.startswith(("http://", "https://")):
            request = Request(
                uri.rstrip("/") + "/api/2.0/mlflow/experiments/search",
                data=b'{"max_results":1}',
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
                if not isinstance(payload, dict) or "experiments" not in payload:
                    raise ValueError("Endpoint did not return an MLflow experiment response")
            result.update(status="connected", kind="http", detail="Tracking server responded")
        elif uri.startswith("sqlite:"):
            database = make_url(uri).database
            if not database or database == ":memory:":
                raise ValueError("A persistent tracking database is required")
            path = Path(database).resolve()
            if not path.is_file():
                raise FileNotFoundError("Tracking database does not exist")
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=timeout) as connection:
                connection.execute("SELECT experiment_id FROM experiments LIMIT 1").fetchall()
            result.update(status="connected", kind="sqlite", detail="Local tracking database is readable")
        else:
            raise ValueError("This tracking URI is not supported by the connectivity check")
    except Exception as error:
        result["detail"] = f"Tracking check failed ({type(error).__name__})"
    return result
