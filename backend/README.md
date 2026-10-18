# CustomerPulse AI backend

The backend has three separate entry points. Data preparation validates and
normalizes records and saves reproducible splits. Training learns transformations
inside CV folds and saves a versioned candidate. Inference scores a CSV using the
active or explicitly requested complete pipeline.

Run the commands below from `backend`, using your project's Python environment.
On Windows you can replace `python` with `.\.venv\Scripts\python.exe`.

## One-command training

```powershell
python -m pipelines.training_pipeline
```

This prepares the configured dataset, runs five-fold CV for Logistic Regression,
Random Forest and Gradient Boosting, evaluates the selected model on the held-out
set, logs to MLflow, and prints the new candidate version and bundle path.
The candidate is saved without changing the model currently served by the API.

To train and explicitly select the new version for inference in one command:

```powershell
python -m pipelines.training_pipeline --activate
```

Training options: `--data-path PATH`, `--config PATH`, `--output-dir PATH`,
`--cv-folds N`, `--tracking-uri URI`, `--dataset-version VERSION`, and `--activate`.
`--dataset-version` reuses verified saved splits and cannot be combined with
`--data-path`.

## Shared configuration

`config.yaml` controls the dataset path, split ratio, random seed, CV folds,
prediction threshold, artifact location and MLflow experiment/store. Dataset paths
resolve relative to the YAML file. Generated paths resolve under `backend` or the
explicit `--output-dir`.

`MLFLOW_TRACKING_URI` and `MLFLOW_ARTIFACT_ROOT` override the corresponding YAML
values; command-line overrides take precedence over loaded settings. The effective
configuration is saved with each candidate. Local storage is implemented; the
artifact-manager interface is the extension point for a future S3 provider.

## Data pipeline

```powershell
python -m pipelines.data_pipeline
```

Checks required telecom columns, allowed categories, numeric ranges, whole-number
flags/tenure, missing or invalid target labels, both target classes and duplicate
customer IDs when IDs are present. Missing feature values are retained for
training-fitted imputation. Blank `TotalCharges` becomes a numeric missing value.
No medians, outlier bounds, encoders or scalers are fitted at this stage.

The dataset version depends on the source checksum, normalized content, split
ratio and seed. Repeating the same preparation reuses the verified snapshot.
Changing the seed or dataset produces another version.

## Versioned outputs

```text
artifacts/
  datasets/DATASET_VERSION/
    source.csv
    normalized.csv
    X_train.csv, X_test.csv, y_train.csv, y_test.csv
    metadata.json
  models/MODEL_VERSION/
    pipeline.joblib
    manifest.json
    evaluation_report.json
    input_schema.json
    config.json
    source/                  # exact application/pipeline source snapshot
  active_model.json          # created only by explicit activation
  training/
    mlflow.db
    mlartifacts/
```

Each model manifest records the unique version, selected classifier, MLflow run ID
and tracking URI, dataset version and SHA-256, normalized-data SHA-256, Git commit,
working-tree dirty flag, source checksum, prediction threshold, feature names, CV
results and final test metrics. It also records checksums for every bundle file.
The source snapshot identifies the actual code even when changes are uncommitted.

A model version cannot be overwritten. Loading verifies bundle checksums before
unpickling. Dataset reloads verify the source and split files. Every version keeps
its classifier and fitted preprocessing together.

The API remains compatible with the previous complete Phase 1 pipeline until you
activate a versioned candidate. The old separate classifier/scaler and intermediate
encoded CSVs are not used by these pipelines.

## Select a model or roll back locally

```powershell
python -m utils.artifact_manager list
python -m utils.artifact_manager activate VERSION_FROM_TRAINING
```

Activation updates a small selection pointer after verifying the bundle. Selecting
an older version uses the same command. Compatibility summaries are also written
to `reports/model_metrics.json` and `reports/evaluation_report.json`; the API reads
its model and report from the selected version, rather than guessing the newest
folder.

## Batch prediction

```powershell
python -m pipelines.inference_pipeline --input data/raw/churn.csv --output artifacts/predictions/demo.csv
```

To score a candidate without activating it:

```powershell
python -m pipelines.inference_pipeline --model-version VERSION_FROM_TRAINING --input data/raw/churn.csv --output artifacts/predictions/candidate.csv
```

The output preserves `customerID` when provided and includes prediction,
probability, classifier name, model version and recorded decision threshold.
The input CSV needs customer features; `Churn` is optional and is never a feature.
With no arguments the configured dataset is scored as a local demonstration.

## API and evaluation

```powershell
python -m uvicorn app.main:app --reload --port 8000
python -m src.model_evaluation
```

The API uses the selected bundle's preprocessing and threshold. Prediction responses
include `model_version`; model information reports that version and its threshold.
The metrics endpoint returns the selected version's evaluation report. Manual
evaluation uses the dataset snapshot linked to that model and does not overwrite
immutable training evidence. Use `--model-version VERSION` to evaluate a candidate.

## MLflow

Without an override, training uses `artifacts/training/mlflow.db` and local
`artifacts/training/mlartifacts`. A running tracking server is optional.

```powershell
python -m mlflow server --backend-store-uri sqlite:///artifacts/training/mlflow.db --host 127.0.0.1 --port 8088
```

Runs distinguish training-CV scores from final `test_*` metrics. The selected run
also contains the complete manifest, schema, configuration and evaluation report.
An explicit nullable numeric input signature handles missing numeric values without
the previous integer-schema inference warning. MLflow can still print its standard
cloudpickle advisory when saving these locally trained Python pipelines.

## Tests

Install `requirements-dev.txt`, then run:

```powershell
python -m pytest tests -q
```

Tests cover fold-specific learning, binary/categorical preservation, validation,
reproducible splits, checksums, immutable versions, explicit activation, version-
specific preprocessing and thresholds, batch inference and offline/API agreement.

## API state and recorded runs

The API loads the approved pipeline, manifest and its evaluation report once in
its lifespan startup handler. `/predict`, `/model-info` and `/metrics` identify
that same loaded version. Activating another candidate takes effect after an API
restart. `/health` reports the loaded version, selected version and
`reload_required` so a pending switch is visible.

`/health` also checks prediction storage and reports readiness and the number of
stored predictions. A missing or invalid model keeps model-dependent endpoints
unavailable with HTTP 503. `/mlflow-info` checks the configured tracking store:
a bounded HTTP request for an MLflow server, or a read-only query for a local
SQLite tracking database. A readable SQLite store does not imply the optional
MLflow UI server is running.

Training writes actual stage transitions to `artifacts/runs/MODEL_VERSION.json`.
The `/pipeline-status` endpoint exposes the latest recorded run, including failed
stages and candidates awaiting activation. Existing model manifests remain
immutable. Runs created before status recording was added are not invented or
backfilled as completed jobs.

Customer validation enforces allowed categories, finite non-negative charges,
whole-number tenure and binary flags, and consistent phone/internet options.
Prediction history stores `model_version`; an additive migration leaves older
rows intact with an unrecorded version. API risk levels are Low below 0.4, Medium
from 0.4, and High from 0.7. The classifier decision threshold is recorded
separately in the model manifest.


## Docker and PostgreSQL

Use the repository [Docker setup guide](../README.md) for the four-service stack.
`DATABASE_URL=postgresql+psycopg://...` selects PostgreSQL. Native development
without this variable retains SQLite. Install the updated `requirements.txt`
before restarting a native backend; it now includes Alembic and psycopg.

Startup applies the versioned migrations under `migrations/`; `python -m src.db`
runs them explicitly. New prediction records include a UUID `event_id`, optional
`customer_id`, exact `model_version` and `source` (`api`, `batch`, `stream`).
Existing rows remain readable and use `legacy` when the source was unrecorded.
API requests accept optional `customer_id`; responses return its value and the
new event ID. Identity fields never enter feature preprocessing.

Batch inference now saves history in one transaction by default. Use
`--no-history` for a CSV-only export. To replay events without duplicates, supply
the same UUID `event_id` column in the raw input. Customer IDs are read as strings.
A conflicting event ID fails the transaction instead of overwriting an event.

`python -m src.migrate_history --sqlite PATH` copies old history read-only into
the configured database with repeatable event IDs. See the root guide for the
Docker mount command. The default container model volume starts empty, so train
inside the image rather than importing locally pickled models implicitly.

With the local Compose PostgreSQL service running, test both database dialects:

```powershell
$env:TEST_POSTGRES_URL = 'postgresql+psycopg://customerpulse:customerpulse_local@127.0.0.1:5433/customerpulse'
python -m pytest tests -q
Remove-Item Env:TEST_POSTGRES_URL
```

Adjust credentials/port for your root `.env`. Each PostgreSQL test creates and
removes an isolated schema; it does not replace the application's history table.


## Kafka services

See the root [streaming guide](../README.md#kafka-streaming) for broker setup,
producer replay, consumer groups, dead letters and the restart smoke check.
Install `requirements-streaming.txt` alongside the base requirements for native
streaming development. Docker includes both automatically.

Entry points are `python -m streaming.producer_service`,
`python -m streaming.inference_service` and `python -m streaming.analytics_service`.
Native clients default to `localhost:9095`; container clients use the overlay's
`KAFKA_BOOTSTRAP_SERVERS=stream-broker:9092`. Set `DATABASE_URL` to the application's
PostgreSQL database. Set `STREAM_API_URL` to the serving API to pin inference to its
loaded model version. Without it, native inference uses the locally active bundle.

The API exposes `/stream-analytics` from the unique persisted stream dimensions.
`source: stream` records are also returned by `/recent-predictions`.


## Approval and Airflow

Public activation now runs the acceptance policy in `config.yaml`; a rejected
candidate leaves the current pointer and compatibility reports unchanged.
`python -m pipelines.approval_pipeline run` exercises separate validation, split,
training, evaluation, gate and publication phases. A stable `--run-key` resumes
completed phases using explicit version handoffs.

The manual DAG and isolated runtime image are under `deployment/airflow/`.
See the root [Airflow guide](../README.md#manual-airflow-approval-workflow-and-ci)
for startup, local login, policy criteria, task retries and CI. Scheduling is unset.
After successful publication, restart serving explicitly to load the new version.
