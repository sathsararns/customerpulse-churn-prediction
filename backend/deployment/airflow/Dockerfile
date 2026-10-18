ARG BACKEND_IMAGE=customerpulse-backend:local
FROM ${BACKEND_IMAGE} AS application
FROM apache/airflow:3.3.2-python3.13

USER root
# Isolate ML/application dependencies from Airflow's dependency constraints.
COPY --from=application /usr/local /opt/customerpulse-runtime
COPY --from=application --chown=10001:0 /app /app
COPY --chown=10001:0 deployment/airflow /app/deployment/airflow
COPY --chown=10001:0 deployment/airflow/dags /opt/airflow/dags
COPY --chown=10001:0 deployment/airflow/initialize.py /opt/airflow/initialize.py
ENV CUSTOMERPULSE_PYTHON=/opt/customerpulse-runtime/bin/python3.13 \
    PYTHONDONTWRITEBYTECODE=1
USER 10001:0
