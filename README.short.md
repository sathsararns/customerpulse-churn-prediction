# CustomerPulse AI

React + FastAPI telecom churn prediction with MLflow and PostgreSQL.

From the repository root with Docker Desktop running:

```powershell
Copy-Item .env.example .env
docker compose build
docker compose up -d postgres mlflow
docker compose run --rm train
docker compose up -d backend frontend
```

Dashboard: http://localhost:5173. API docs: http://localhost:8000/docs.
MLflow: http://localhost:8088.

Models, experiment data and prediction history persist in named volumes.
See [the full guide](README.md) for migrations, existing history import,
batch scoring, retraining and the container recreation smoke check.
