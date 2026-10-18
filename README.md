# CustomerPulse AI

Telecom churn prediction with a React dashboard, FastAPI, scikit-learn pipelines,
MLflow tracking and PostgreSQL prediction history.

## Start from a fresh checkout

Install Docker Desktop and start its Linux engine. Run these commands from the
repository root in PowerShell:

```powershell
Copy-Item .env.example .env
docker compose build
docker compose up -d postgres mlflow
docker compose run --rm train
docker compose up -d backend frontend
```

The first build downloads images and packages. Training validates the included
`backend/data/raw/churn.csv`, compares complete pipelines using training-only
cross-validation, evaluates the winner on the held-out test set, saves its manifest
and report, applies the acceptance gate, and activates only a passing version. The API applies database
migrations and loads that complete pipeline at startup. Do not start a second
native Uvicorn/Vite process on the same ports.

| Service | Local address |
| --- | --- |
| Dashboard | http://localhost:5173 |
| API documentation | http://localhost:8000/docs |
| API readiness | http://localhost:8000/health |
| MLflow UI | http://localhost:8088 |
| PostgreSQL | localhost:5433, database/user `customerpulse` |

Ports and the local database password are configured in root `.env`. Keep the
password URL-safe (letters, digits, underscores). Compose services communicate by
service name. The browser calls `/api` on the dashboard's own origin; Nginx proxies
it to FastAPI. Docker always builds the frontend with live mode enabled.

## Make a prediction and verify persistence

Open the dashboard's Predict Churn page, enter an optional customer ID and submit
the form. History shows the stored customer ID, event ID, model version and source.
The API also returns these fields. Customer IDs are tracing metadata and never
enter the model features. A request without an ID retains `customer_id: null`.

```powershell
docker compose down
docker compose up -d
Invoke-RestMethod http://localhost:8000/recent-predictions
```

History, the selected model and MLflow runs survive container recreation through
named volumes. `docker compose down -v` deletes those volumes and their contents;
normal stops/restarts do not need `-v`.

The repeatable end-to-end check builds, trains, predicts, recreates the services,
and asserts the same event/customer/model remain in history:

```powershell
.\scripts\smoke-docker.ps1
# Or skip an already completed image build:
.\scripts\smoke-docker.ps1 -SkipBuild
```

The smoke script reads the effective Compose configuration, including port
overrides in root `.env` or your shell environment.

## Retraining and batch scoring

```powershell
# Save a candidate only:
docker compose run --rm train --cv-folds 5
# Train, activate and restart serving:
docker compose run --rm train --activate
docker compose restart backend
# Score the included dataset and save batch history:
docker compose exec backend python -m pipelines.inference_pipeline
```

The training service uses the same image and model volumes as the API. MLflow
receives runs and artifact uploads through its HTTP server; its own PostgreSQL
metadata database is separate from application history. Models trained outside
Docker are not silently copied into the container volume: train inside Docker to
keep Python and library versions consistent.

Batch CSVs may include `customerID` or `customer_id`. These remain strings, including
leading zeroes. Output contains `event_id`, `customer_id`, `source`, `model_version`,
probability, label and risk. Batch predictions are persisted by default; use
`--no-history` for export only. To replay a batch, retain its original event IDs in
the input CSV. New events without IDs receive fresh UUIDs.

## Database migrations and existing local history

`DATABASE_URL` selects PostgreSQL; direct Python usage without it keeps the existing
SQLite file at `backend/data/customerpulse.db`. SQLAlchemy uses parameterized
queries and Alembic records schema revisions in `alembic_version`. Startup upgrades
the schema; the same operation can be run explicitly:

```powershell
docker compose exec backend python -m src.db
```

Migration 0001 creates/adopts prediction history; 0002 adds unique event IDs,
customer IDs and a constrained source. Older records retain their original model
version when known and use `source: legacy` when their origin was never recorded.
New writers support `api`, `batch` and `stream`. Stream workers can use
`src.prediction_store.save_prediction(..., source="stream", event_id=...)` with
stable UUIDs. Replaying the same event is idempotent; conflicting reuse is rejected.
The optional Kafka setup below supplies the producer and consumers for stream events.

To copy your existing SQLite history into PostgreSQL, mount the source read-only:

```powershell
docker compose run --rm --volume "${PWD}/backend/data:/legacy:ro" --entrypoint python train -m src.migrate_history --sqlite /legacy/customerpulse.db
```

This copies rows in one transaction, preserves known customer/version/event values,
assigns stable IDs to old events, and leaves the source unchanged. Rerunning the
import does not duplicate events. Container IDs are separate from source row IDs.
Your existing native model selection is also unchanged by Docker training.

## Storage and operations

| Named volume | Contents |
| --- | --- |
| `postgres_data` | Prediction history and MLflow metadata databases |
| `model_artifacts` | Versioned pipelines, datasets, manifests, active selection and run status |
| `model_reports` | Compatibility evaluation summaries |
| `mlflow_artifacts` | Uploaded experiment/model artifacts |

```powershell
docker compose ps
docker compose logs --tail 100 backend mlflow postgres
docker compose stop
```

A fresh API without an activated model reports degraded readiness. Build and run
training first, or restart the API after activating a candidate. Changes to
application code require rebuilding the image. Changes to PostgreSQL's initial
password do not change an already initialized database volume's credentials.

## Development checks

See [backend instructions](backend/README.md) and
[frontend instructions](frontend/README.md) for native development and tests.
Container dependency constraints pin the core training/serving package versions;
the frontend installs from `package-lock.json`.

Backend tests cover leakage prevention, artifacts, API agreement, validation,
migrations, event replay, atomic writes, legacy import and restart persistence.
Set `TEST_POSTGRES_URL` to a disposable PostgreSQL database to run the database
tests against PostgreSQL as well as SQLite; each test uses and removes its own
isolated schema. Frontend contract tests verify real risk/version and identifiers.

The service startup follows [Docker health dependencies](https://docs.docker.com/compose/how-tos/startup-order/).
MLflow uses its [artifact proxy](https://mlflow.org/docs/latest/self-hosting/architecture/tracking-server/)
so training clients do not need its artifact filesystem mounted.


## Kafka streaming

Kafka is opt-in through `docker-compose.kafka.yml`. First complete the base Docker
setup and activate a trained model. Then run from the repository root:

```powershell
docker compose build backend frontend
docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d backend frontend stream-inference stream-analytics
docker compose -f docker-compose.yml -f docker-compose.kafka.yml run --rm stream-producer --limit 10 --interval 0.5
```

The replay producer prints its replay UUID. Each row receives a UUID derived from
that replay UUID and its row position. Reuse the UUID with the same input to resume
or replay without creating another prediction for each event:

```powershell
docker compose -f docker-compose.yml -f docker-compose.kafka.yml run --rm stream-producer --limit 10 --interval 0 --replay-id REPLAY_UUID_FROM_OUTPUT
```

Use a new replay UUID for a genuinely new simulation. Other options are `--start N`
and `--input PATH_IN_CONTAINER`. Input preserves telecom `customerID` strings,
including leading zeroes. `Churn` and identifiers are excluded from model features.
Events that include `Churn` in features are rejected by the consumer's contract.

```text
Producer -> customer-events -> Inference -> churn-predictions -> Analytics
                                                                    |
                                                               PostgreSQL
                                                                    |
                                                             Recent Activity
Invalid events -> customerpulse-dead-letter
```

The broker has a dedicated `stream_kafka_data` volume and listens on host port
9095 (override `KAFKA_PORT`), or `stream-broker:9092` inside Docker. It is separate
from older Kafka containers that may exist on this computer. A one-shot volume
initialization gives the broker's non-root user write access. Another one-shot
service creates all three topics with three partitions, seven-day retention and
replication factor one for this local single-broker environment.

Inference loads the exact model version currently served by FastAPI from the
shared model volume. Both paths use `src.model_inference.predict_single` and the
same fitted preprocessing, threshold and risk boundaries. For new events it checks
that the API still serves that version; a mismatch makes the worker restart and
load the API's current bundle. Restart inference after switching models:

```powershell
docker compose -f docker-compose.yml -f docker-compose.kafka.yml restart backend stream-inference
```

The service groups are stable: `customerpulse-inference-v1` and
`customerpulse-analytics-v1`. Automatic commits and automatic offset storage are
disabled. Inference commits only after the prediction is acknowledged by Kafka.
Analytics commits only after a transaction saves prediction history and its risk
dimensions. Producer idempotence and broker retries are enabled. Transient failures
receive bounded application retries and then stop the process with the offset
uncommitted; Docker restarts it. An unavailable database or broker does not cause a
valid customer event to be discarded into the dead-letter topic.

Malformed events and conflicting event-ID reuse go to `customerpulse-dead-letter`.
The dead letter includes original topic, partition, offset, key/value bytes encoded
as base64, and the error. The original offset is committed only after Kafka confirms
the dead letter. To fix an invalid event, correct its input and publish a new event
ID. Do not send the dead-letter envelope directly into `customer-events`.

Migration 0003 adds `stream_inference_results` and
`stream_prediction_dimensions`. The first stores the scored output before Kafka
publishing; a replay retains the original output and model version even after a
worker/model restart. The second stores one contract/internet/tenure grouping row
per unique prediction event. A unique `predictions.event_id` prevents duplicate
history. A crash after DB commit and before Kafka commit safely replays the same
write. Conflicting content for an existing event ID is rejected, never overwritten.

This is at-least-once message delivery with idempotent database effects. Prediction
messages can appear more than once in Kafka after a crash; history and grouped
counts remain unique. This follows [Kafka's delivery semantics](https://kafka.apache.org/11/design/design/)
and the client's [manual commit and delivery acknowledgement APIs](https://docs.confluent.io/kafka-clients/python/current/overview.html).

Open Recent Activity at http://localhost:5173/app/activity. It refreshes every five
seconds and displays `source: stream`, the actual customer ID, event ID and model
version. Native frontend clients need to use the Docker API port configured in root
`.env`; the Docker dashboard uses its own `/api` proxy automatically.

`GET /stream-analytics` returns risk counts and average probabilities grouped by
contract type (`Contract`), internet service (`InternetService`) and tenure band
(`0-12`, `13-24`, `25-48`, `49+` months). Groups also include model version, so results
from different models remain identifiable. These counts derive from unique saved
stream events and do not increase on redelivery.

```powershell
Invoke-RestMethod http://localhost:8001/stream-analytics
# Use API_PORT from .env if it differs.
docker compose -f docker-compose.yml -f docker-compose.kafka.yml logs --tail 50 stream-inference stream-analytics
docker compose -f docker-compose.yml -f docker-compose.kafka.yml exec stream-broker /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server stream-broker:9092 --all-groups --describe
```

A repeatable local verification publishes five customers plus one invalid event,
checks API/stream probability agreement and dead-letter delivery, restarts both
consumers, deliberately rewinds the stopped analytics group's offsets, then replays
the same producer events. It asserts one unchanged history record per event and
unchanged analytics counts:

```powershell
.\scripts\smoke-kafka.ps1
# If the images are already current:
.\scripts\smoke-kafka.ps1 -SkipBuild
```

The report is saved inside the shared model volume at
`/app/artifacts/phase5-stream-verification.json`. The check deliberately replays the
local analytics group; run it against this development stack. For native Python
development, also install `backend/requirements-streaming.txt`.

Stop the new consumers/broker with the same two Compose files and `stop
stream-inference stream-analytics stream-broker`; retain the named volumes. Base
four-service commands can still be used independently. Existing older Kafka/Airflow
containers are not part of this overlay and are not removed by these commands.


## Manual Airflow approval workflow and CI

The optional Airflow overlay adds this six-task, manual-only workflow:

```text
Validate dataset -> Prepare splits -> Train candidates -> Evaluate
                  -> Apply acceptance gate -> Publish approved version
```

Every task passes a small JSON handoff containing explicit dataset/model versions,
and eventually the gate receipt ID. Raw data, splits, fitted candidates, evaluation
reports and approval receipts live in versioned artifacts, not XCom. Validation
freezes the input before splitting. Training only receives the training split and
selects by CV F1; the evaluation task is the first task to score the held-out split.
Task retries reuse the same immutable input and model version. Invalid inputs and
rejected candidates fail without retries; transient task failures retry twice.
There is no schedule, catchup is disabled, and only one DAG run/task runs at a time.

Build the application image first, then its isolated Airflow runtime:

```powershell
docker compose build backend
docker compose -f docker-compose.yml -f docker-compose.airflow.yml build orchestration
docker compose -f docker-compose.yml -f docker-compose.airflow.yml up -d orchestration
```

Open http://localhost:8090. Local login: `admin`, password `customerpulse_local`
(or `AIRFLOW_ADMIN_PASSWORD` from root `.env`). The DAG is
`customerpulse_approved_training`. Unpause it and use Trigger DAG. No recurring
runs are created. The default input is `/app/data/raw/churn.csv`; an optional trigger
configuration can specify another available CSV:

```json
{"data_path": "/app/data/raw/churn.csv"}
```

Airflow's metadata has its own PostgreSQL service and persistent volume. The local
container uses Airflow 3.3.2 with LocalExecutor, adapting the
[official Docker learning setup](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html).
The application's Python runtime is copied into a separate path, so installing ML
libraries cannot change Airflow dependencies. No Docker socket is mounted. The
Airflow overlay disables MLflow's unused background job executor to keep memory
available for local training; experiment tracking and artifacts remain enabled.
This setup is intended for local learning. Official Airflow guidance recommends at
least 4 GB of Docker memory, ideally 8 GB, for its Compose environment.

The base services and Kafka can remain running. To manage everything together:

```powershell
docker compose -f docker-compose.yml -f docker-compose.kafka.yml -f docker-compose.airflow.yml ps
```

Publishing selects the approved version atomically. The API keeps its already
loaded bundle until an explicit restart; `/health` exposes `reload_required` and
the dashboard reports the pending selection. After reviewing a successful run:

```powershell
docker compose -f docker-compose.yml -f docker-compose.kafka.yml restart backend stream-inference
```

A failed validation, training, evaluation or acceptance task never changes the
selection pointer. The API and streaming consumers continue using their loaded
approved model. A successful new selection also retains previous immutable model
bundles for traceability.

### Initial acceptance policy

`backend/config.yaml` contains the policy. The corrected logistic-regression
baseline had F1 0.6040, churn recall 0.5588, precision 0.6572 and ROC-AUC 0.8418.
The initial retention objective is to preserve churn detection while limiting
unnecessary retention actions. These are initial technical criteria; business cost
and retention-budget data can later justify a reviewed policy change.

| Gate | Required |
| --- | --- |
| Held-out F1 | >= 0.60 |
| Churn recall | >= 0.55 |
| Precision | >= 0.63 |
| ROC-AUC | >= 0.83 |
| F1 drop from approved model | <= 0.005 |
| Recall drop from approved model | <= 0.01 |
| Evaluation dataset version | Same as approved model by default |
| Integrity | Verified bundle/dataset checksums, both target classes, matching report/manifest and confusion-matrix metrics |

Dataset changes require an explicit policy review rather than comparing unrelated
holdouts automatically. Candidates are still selected solely by training-only CV;
the holdout gate makes a publication decision. Reports must contain finite metrics.
Each gate receipt binds the candidate manifest, policy checksum and current
approved reference. Publication rechecks these under a process lock; a changed
policy, changed candidate, rejected receipt or stale reference blocks publication.
The pass/fail receipt remains under `artifacts/gates/MODEL_VERSION/`.

The existing `training_pipeline --activate` and `utils.artifact_manager activate`
commands now enforce this same policy. Saving a candidate without activation still
works. Rollback through the public activation command also has to pass the gate.
A rejected candidate does not overwrite the approved compatibility reports.

The full workflow can also be exercised without Airflow, from `backend`:

```powershell
python -m pipelines.approval_pipeline run
```

Use a unique `--run-key` to identify a run; reusing it resumes the original immutable
input/model version. `--config` and `--output-dir` allow isolated local experiments.
A new run is required after changing the workflow configuration.

### GitHub Actions

`.github/workflows/ci.yml` runs on pushes, pull requests and manual dispatch. It:

- Runs Python tests against SQLite and a PostgreSQL service, including preprocessing,
  categorical consistency, invalid data, API/offline agreement, Kafka replay and
  keeping the approved model when promotion fails.
- Runs frontend contract tests, lint and the production build.
- Builds backend, frontend and Airflow images, checks the six-task manual DAG and
  validates the combined Compose configuration.

The workflow builds images without publishing them. It uses the
[GitHub Python test workflow](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)
pattern. GitHub executes it after these files are committed and pushed; adding the
workflow locally does not create a remote CI run.


### Verify Airflow failure handling locally

With an existing approved model, run from the repository root:

```powershell
.\scripts\smoke-airflow.ps1
# Or, when both images are current:
.\scripts\smoke-airflow.ps1 -SkipBuild
```

This uses the real scheduler/API to trigger three manual runs: the corrected
baseline passes and publishes; a missing target fails validation; shuffled target
labels produce a weak model that fails the gate. It checks application readiness
throughout and verifies that both failing runs preserve the approved selection
and the currently served model. The report is stored in the shared model volume
at `/app/artifacts/phase6-airflow-verification.json`. The successful run intentionally
publishes a new approved version; load it with the explicit serving restart above.
The failed verification runs remain visible in Airflow as expected examples.
