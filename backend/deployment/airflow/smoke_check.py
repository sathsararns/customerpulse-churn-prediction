"""Exercise successful and blocked manual DAG runs against the live application."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

import pandas as pd

DAG = "customerpulse_approved_training"
AIRFLOW = "http://orchestration:8080"
API = "http://frontend:8080/api"
ROOT = Path("/app/artifacts")


def request_json(url, payload=None, method=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                      method=method, headers=headers)
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"HTTP {error.code}: {error.read().decode()}") from error


def wait_run(run_id, token, expected):
    deadline, previous = time.monotonic() + 900, None
    url = f"{AIRFLOW}/api/v2/dags/{DAG}/dagRuns/{quote(run_id, safe='')}"
    while time.monotonic() < deadline:
        run = request_json(url, token=token)
        state = run["state"]
        if state != previous:
            print(f"{run_id}: {state}", flush=True)
            previous = state
        # The API must remain ready with its original loaded pipeline throughout.
        health = request_json(API + "/health")
        assert health["ready"], "Application became unavailable during orchestration"
        if state in {"success", "failed"}:
            assert state == expected, run
            return run
        time.sleep(2)
    raise AssertionError("Airflow run did not finish within 15 minutes")


def trigger(run_id, token, data_path):
    return request_json(f"{AIRFLOW}/api/v2/dags/{DAG}/dagRuns", {
        "dag_run_id": run_id, "logical_date": datetime.now(timezone.utc).isoformat(),
        "conf": {"data_path": str(data_path)},
    }, token=token)


def workflow_context(run_id):
    version = "churn-wf-" + hashlib.sha256((DAG + ":" + run_id).encode()).hexdigest()[:24]
    return json.loads((ROOT / "workflows" / version / "state.json").read_text(encoding="utf-8"))["context"]


def main():
    token = request_json(AIRFLOW + "/auth/token", {"username": "admin", "password": os.environ["AIRFLOW_ADMIN_PASSWORD"]})["access_token"]
    deadline = time.monotonic() + 90
    while True:
        try:
            request_json(f"{AIRFLOW}/api/v2/dags/{DAG}", token=token)
            break
        except RuntimeError:
            if time.monotonic() > deadline:
                raise
            time.sleep(2)
    request_json(f"{AIRFLOW}/api/v2/dags/{DAG}", {"is_paused": False}, method="PATCH", token=token)
    fixtures = ROOT / "airflow-checks"
    fixtures.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv("/app/data/raw/churn.csv")
    invalid = raw.head(20).copy()
    invalid.loc[invalid.index[0], "Churn"] = None
    invalid.to_csv(fixtures / "invalid.csv", index=False)
    weak = raw.copy()
    weak["Churn"] = weak["Churn"].sample(frac=1, random_state=4217).to_numpy()
    weak.to_csv(fixtures / "weak.csv", index=False)
    baseline = request_json(API + "/health")
    suffix = uuid4().hex[:12]
    success_id = "check-approved-" + suffix
    trigger(success_id, token, "/app/data/raw/churn.csv")
    wait_run(success_id, token, "success")
    approved = request_json(API + "/health")["selected_model_version"]
    success_context = workflow_context(success_id)
    assert approved == success_context["published_model_version"]
    for label in ["invalid", "weak"]:
        run_id = f"check-{label}-{suffix}"
        trigger(run_id, token, fixtures / f"{label}.csv")
        wait_run(run_id, token, "failed")
        health = request_json(API + "/health")
        assert health["selected_model_version"] == approved
        assert health["model_version"] == baseline["model_version"]
        context = workflow_context(run_id)
        status = json.loads((ROOT / "runs" / f"{context['model_version']}.json").read_text(encoding="utf-8"))
        failed = [stage["id"] for stage in status["stages"] if stage["status"] == "failed"]
        assert failed == (["validation"] if label == "invalid" else ["gate"]), failed
        print(f"PASS: {label} blocked at {failed[0]}; approved and served versions preserved", flush=True)
    report = {"successful_run": success_id, "approved_model_version": approved,
              "serving_model_version": baseline["model_version"], "invalid_data_blocked": True,
              "weak_model_blocked": True, "application_stayed_ready": True,
              "reload_required": request_json(API + "/health")["reload_required"]}
    (ROOT / "phase6-airflow-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
