FROM python:3.10-slim-trixie

# [api] Install uv by copying static binaries from the official image (no curl)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /usr/local/bin/uvx

WORKDIR /app

# Install deps using pyproject (uvicorn must be listed in pyproject)
COPY pyproject.toml /app/pyproject.toml
RUN uv pip install --system .

ENV MLFLOW_TRACKING_URI=http://mlflow:8003
ENV MLFLOW_EXPERIMENT_NAME=random_forest_experiment

# Copy the rest of the API source
COPY . /app

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]