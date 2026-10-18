"""Manual-only approval workflow; task payloads contain versions, never datasets."""

from datetime import timedelta
import json
import os
import subprocess

import pendulum
from airflow.sdk import dag, get_current_context, task
from airflow.sdk.exceptions import AirflowFailException


def execute_phase(phase, context=None, **arguments):
    command = [os.environ["CUSTOMERPULSE_PYTHON"], "-s", "-m", "pipelines.approval_pipeline", phase]
    if context is not None:
        command += ["--context-json", json.dumps(context)]
    for key, value in arguments.items():
        if value is not None:
            command += ["--" + key.replace("_", "-"), str(value)]
    result = subprocess.run(command, cwd="/app", text=True, capture_output=True, check=False)
    print(result.stdout, flush=True)
    if result.stderr:
        print(result.stderr, flush=True)
    if result.returncode in {2, 3}:
        raise AirflowFailException(f"{phase} rejected input or candidate; approved model unchanged")
    if result.returncode:
        raise RuntimeError(f"{phase} failed with exit {result.returncode}; task will retry")
    lines = [line for line in result.stdout.splitlines() if line.startswith("WORKFLOW_RESULT=")]
    if len(lines) != 1:
        raise RuntimeError("Task did not return one explicit version handoff")
    return json.loads(lines[0].split("=", 1)[1])


@dag(dag_id="customerpulse_approved_training", schedule=None,
     start_date=pendulum.datetime(2026, 1, 1, tz="UTC"), catchup=False, max_active_runs=1,
     default_args={"retries": 2, "retry_delay": timedelta(seconds=15)},
     tags=["customerpulse", "manual", "acceptance-gates"])
def approved_training():
    @task(task_id="validate_dataset")
    def validate():
        context = get_current_context()
        conf = context["dag_run"].conf or {}
        return execute_phase("validate", data_path=conf.get("data_path", "/app/data/raw/churn.csv"),
                             run_key=context["dag"].dag_id + ":" + context["run_id"])

    @task(task_id="prepare_splits")
    def prepare(version):
        return execute_phase("prepare", version)

    @task(task_id="train_candidates", execution_timeout=timedelta(minutes=20))
    def train(version):
        return execute_phase("train", version)

    @task(task_id="evaluate_candidate")
    def evaluate(version):
        return execute_phase("evaluate", version)

    @task(task_id="apply_acceptance_gate")
    def gate(version):
        return execute_phase("gate", version)

    @task(task_id="publish_approved_version")
    def publish(version):
        return execute_phase("publish", version)

    publish(gate(evaluate(train(prepare(validate())))))


approved_training()
