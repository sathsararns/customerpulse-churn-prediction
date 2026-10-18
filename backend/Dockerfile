FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt constraints.txt ./
RUN pip install -r requirements.txt -c constraints.txt
COPY requirements-streaming.txt ./
RUN pip install -r requirements-streaming.txt
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
COPY --chown=app:app . .
RUN mkdir -p /app/artifacts /app/reports /app/mlartifacts /app/data \
    && chown -R app:app /app/artifacts /app/reports /app/mlartifacts /app/data
USER app
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
