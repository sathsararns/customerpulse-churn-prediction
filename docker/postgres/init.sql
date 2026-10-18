-- Prediction history and MLflow metadata have separate databases.
-- The official Postgres entrypoint runs this only for a fresh data volume.
CREATE DATABASE mlflow OWNER customerpulse;
