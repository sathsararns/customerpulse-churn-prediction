# CustomerPulse AI

An AI-powered customer churn prediction platform that combines a trained machine learning model, a FastAPI backend, a React dashboard, and MLflow experiment tracking — all orchestrated with Docker Compose.

CustomerPulse AI predicts whether a customer is likely to **churn** (cancel their subscription/service) based on their profile and usage data, and gives risk scores that support proactive retention decisions.

---

## Table of Contents

1. [Key Features](#key-features)
2. [Tech Stack](#tech-stack)
3. [Project Architecture / How It Works](#project-architecture--how-it-works)
4. [Folder Structure](#folder-structure)
5. [Setup and Installation](#setup-and-installation)
6. [How to Run the Project](#how-to-run-the-project)
7. [API Endpoints](#api-endpoints)
8. [MLflow Usage](#mlflow-usage)
9. [Screenshots](#screenshots)
10. [Future Improvements](#future-improvements)
11. [License](#license)

---

## Key Features

- **Churn prediction API** — submit a customer profile and get a churn prediction with a probability score and risk level (Low / Medium / High).
- **End-to-end ML pipeline** — automated data ingestion, cleaning, outlier handling, encoding, scaling, splitting, training, and evaluation.
- **Model comparison & selection** — trains Logistic Regression, Random Forest, and Gradient Boosting, and automatically promotes the best performer (by F1 score) to production.
- **Experiment tracking with MLflow** — every training run, its parameters, and its metrics are logged and browsable in the MLflow UI.
- **Interactive dashboard** — a React/TypeScript UI for running predictions, viewing model metrics, and reviewing recent prediction activity.
- **Prediction history** — every prediction is persisted (SQLite) and retrievable via the API for auditing and the "Recent Activity" view.
- **Fully containerized** — one `docker compose` command brings up MLflow, the backend API, and the frontend together.

## Tech Stack

**Frontend**
- React 19 + TypeScript + Vite
- Tailwind CSS with Radix UI primitives (shadcn/ui-style components)
- React Hook Form + Zod for form validation
- Recharts for metrics visualizations
- Axios for API communication

**Backend**
- FastAPI (Python)
- Pydantic for request/response validation
- Uvicorn ASGI server
- scikit-learn (Logistic Regression, Random Forest, Gradient Boosting)
- pandas, joblib for data handling and model persistence

**ML Ops / Infrastructure**
- MLflow for experiment tracking and model metrics
- SQLite for prediction history and lightweight local storage
- Docker & Docker Compose for containerized orchestration

## Project Architecture / How It Works

```
┌─────────────┐        HTTP (axios)        ┌──────────────────┐
│   Frontend   │ ───────────────────────▶ │   FastAPI Backend  │
│ (React/Vite) │ ◀─────────────────────── │                     │
└─────────────┘        JSON responses      └──────────┬──────────┘
                                                        │
                                     loads model/scaler │  logs runs
                                                        ▼
                                          ┌──────────────────────┐
                                          │  Trained ML Artifacts │
                                          │ (models/, artifacts/) │
                                          └──────────┬───────────┘
                                                      │
                                                      ▼
                                          ┌──────────────────────┐
                                          │      MLflow Server     │
                                          │ (tracking + registry)  │
                                          └──────────────────────┘
```

**Data flow:**

1. **Training pipeline** (`backend/pipelines/training_pipeline.py`) ingests raw churn data, cleans it, handles outliers, encodes categorical features, scales numeric features, and splits it into train/test sets.
2. Three candidate models are trained and evaluated (accuracy, precision, recall, F1, ROC-AUC). The best model (by F1 score) is saved to `backend/models/` along with the fitted scaler, and every run is logged to **MLflow**.
3. **FastAPI backend** loads the latest saved model/scaler at request time and serves predictions via `POST /predict`, storing each result in a local SQLite database.
4. **React frontend** talks to the backend over a REST API to run predictions, and to display model metrics, training status, and recent prediction history.

## Folder Structure

```
CustomerPulse-AI/
├── docker-compose.yml          # Orchestrates mlflow, backend, frontend
├── mlflow-data/                # MLflow's SQLite DB + artifact store (bind-mounted)
│
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app & API routes
│   │   └── schemas.py          # Pydantic request/response models
│   ├── pipelines/
│   │   ├── training_pipeline.py    # Full training pipeline entrypoint
│   │   └── inference_pipeline.py   # Standalone inference example
│   ├── src/                    # Pipeline building blocks (ingestion, cleaning,
│   │                             encoding, scaling, training, inference, DB helpers)
│   ├── data/                   # Raw & processed datasets (raw/, processed/)
│   ├── models/                 # Saved trained model artifacts (.pkl)
│   ├── artifacts/               # Scaler and other supporting artifacts
│   ├── reports/                 # model_metrics.json, evaluation_report.json
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── pages/               # Landing, Predict, Metrics, Activity, Model Info
│   │   ├── components/          # UI primitives, dashboard widgets, charts, forms
│   │   ├── services/            # Axios API client
│   │   └── hooks/                # Data-fetching hooks
│   ├── package.json
│   └── Dockerfile
│
└── README.md
```

## Setup and Installation

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose (v2+)
- Git

Optional, for running services outside Docker:
- Python 3.11+ and `pip` (backend)
- Node.js 20+ and `npm` (frontend)

### Clone the repository

```bash
git clone <your-repository-url>
cd CustomerPulse-AI
```

No `.env` file is required to run the default setup — the ports and service URLs below are pre-configured in `docker-compose.yml`.

## How to Run the Project

### Option A — Run everything with Docker Compose (recommended)

```bash
docker compose up -d --build
```

This starts three services:

| Service   | URL                      | Description                  |
|-----------|--------------------------|-------------------------------|
| Frontend  | http://localhost:5173    | React dashboard               |
| Backend   | http://localhost:8000    | FastAPI churn prediction API  |
| MLflow    | http://localhost:5000    | Experiment tracking UI        |

To stop everything:

```bash
docker compose down
```

To rebuild after changing code or dependencies:

```bash
docker compose up -d --build
```

### Option B — Run the training pipeline

The Docker image ships with a pre-trained model, but you can re-train it at any time:

```bash
docker compose exec backend python -m pipelines.training_pipeline
```

### Option C — Run services locally without Docker

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env   # set VITE_API_BASE_URL if needed
npm run dev
```

**MLflow** (local, no Docker)
```bash
mlflow server --host 0.0.0.0 --port 5000
```

## API Endpoints

Base URL: `http://localhost:8000`

| Method | Endpoint             | Description                                             |
|--------|-----------------------|-----------------------------------------------------------|
| GET    | `/`                   | API status/health message                                 |
| GET    | `/health`             | Simple health check                                       |
| GET    | `/mlflow-info`        | MLflow connection info (experiment name, tracking URI)     |
| GET    | `/model-info`         | Metadata about the currently deployed model                |
| GET    | `/metrics`            | Evaluation metrics of the trained model                    |
| GET    | `/recent-predictions` | Recent prediction history (supports `?limit=`)              |
| POST   | `/predict`            | Submit a customer profile and receive a churn prediction   |

**Example — `POST /predict`**

```json
{
  "gender": "Female",
  "SeniorCitizen": 0,
  "Partner": "Yes",
  "Dependents": "No",
  "tenure": 12,
  "PhoneService": "Yes",
  "MultipleLines": "No",
  "InternetService": "DSL",
  "OnlineSecurity": "Yes",
  "OnlineBackup": "No",
  "DeviceProtection": "Yes",
  "TechSupport": "No",
  "StreamingTV": "Yes",
  "StreamingMovies": "No",
  "Contract": "Month-to-month",
  "PaperlessBilling": "Yes",
  "PaymentMethod": "Electronic check",
  "MonthlyCharges": 70.35,
  "TotalCharges": 845.2
}
```

**Response**

```json
{
  "model": "gradient_boosting",
  "prediction": 1,
  "probability": 0.78,
  "risk_level": "High"
}
```

Interactive API documentation (Swagger UI) is available at `http://localhost:8000/docs` whenever the backend is running.

## MLflow Usage

CustomerPulse AI uses **MLflow** to track every model training run under the experiment name `CustomerPulse-AI`, including:

- Model type and hyperparameters
- Evaluation metrics: accuracy, precision, recall, F1 score, ROC-AUC
- Trained model artifacts

**Access the MLflow UI:**

```
http://localhost:5000
```

**How it's wired up:**
- The `mlflow` service in `docker-compose.yml` runs `mlflow server` with a SQLite backend store (`mlflow-data/mlflow.db`) and a local artifact root (`mlflow-data/artifacts`).
- The `backend` service points at it via the `MLFLOW_TRACKING_URI` environment variable (`http://mlflow:5000` inside Docker, or `http://127.0.0.1:5000` when running locally).
- Each run of `pipelines/training_pipeline.py` logs a new MLflow run automatically — no extra setup required.

## Screenshots

> _Add screenshots or a short demo GIF of the dashboard here._

| Landing / Overview | Prediction Form | Model Metrics |
|---|---|---|
| _placeholder_ | _placeholder_ | _placeholder_ |

## Future Improvements

- [ ] Add authentication/authorization for the API and dashboard
- [ ] Move from SQLite to a production-grade database (e.g. PostgreSQL) for prediction history
- [ ] Add automated model retraining on a schedule or via a trigger endpoint
- [ ] Add CI/CD pipeline (lint, test, build, deploy)
- [ ] Add batch prediction support (CSV upload)
- [ ] Promote the MLflow Model Registry for versioned model promotion (staging → production)
- [ ] Add unit/integration test coverage reporting
- [ ] Deploy to a cloud environment (AWS/GCP/Azure) with managed storage for artifacts

## License

This project does not yet include a formal license file.

> _Placeholder — add a `LICENSE` file (e.g. [MIT License](https://choosealicense.com/licenses/mit/)) to specify how others may use, modify, and distribute this project._
