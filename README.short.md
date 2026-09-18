# CustomerPulse AI

AI-powered customer churn prediction system with a React frontend, FastAPI backend, and MLflow experiment tracking — fully containerized with Docker Compose.

## Key Features
- Predicts customer churn with a probability score and risk level
- Full ML pipeline: ingestion → cleaning → encoding → scaling → training → evaluation
- Trains and auto-selects the best of Logistic Regression, Random Forest, and Gradient Boosting
- Experiment tracking via MLflow
- Interactive React dashboard for predictions, metrics, and prediction history
- One-command startup with Docker Compose

## Tech Stack
**Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Radix UI
**Backend:** FastAPI, scikit-learn, pandas, joblib
**ML Ops:** MLflow, SQLite, Docker Compose

## How It Works
1. The training pipeline processes raw churn data and trains multiple models, logging each run to MLflow.
2. The best model (by F1 score) is saved and served by the FastAPI backend.
3. The React dashboard calls the backend to run predictions and display metrics/history.

## Run the Project

```bash
docker compose up -d --build
```

| Service  | URL                   |
|----------|-----------------------|
| Frontend | http://localhost:5173 |
| Backend  | http://localhost:8000 |
| MLflow   | http://localhost:5000 |

Re-train the model:
```bash
docker compose exec backend python -m pipelines.training_pipeline
```

## API Endpoints

| Method | Endpoint               | Description                    |
|--------|-------------------------|---------------------------------|
| GET    | `/health`               | Health check                    |
| GET    | `/model-info`           | Current model metadata          |
| GET    | `/metrics`              | Model evaluation metrics        |
| GET    | `/recent-predictions`   | Recent prediction history       |
| POST   | `/predict`              | Run a churn prediction          |

Full interactive docs: `http://localhost:8000/docs`

## MLflow

All training runs are logged under the `CustomerPulse-AI` experiment. Open the UI at `http://localhost:5000` to compare runs, metrics, and parameters.

## Screenshots

> _Add screenshots or a demo GIF here._

## Future Improvements
- Authentication for API/dashboard
- PostgreSQL instead of SQLite
- Scheduled/triggered retraining
- CI/CD pipeline
- MLflow Model Registry for staged promotions

## License
No license file yet — add one (e.g. MIT) to specify usage terms.
