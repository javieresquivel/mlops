FROM jupyter/datascience-notebook:latest

# Install uv by copying static binaries from the official image (no curl)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /usr/local/bin/uvx

# Jupyter notebooks live here in the base image
WORKDIR /home/jovyan/workspace

# Copy only project metadata to leverage Docker layer cache
COPY pyproject.toml ./pyproject.toml
# If you have a uv.lock produced by uv, copy it; otherwise, omit this line
COPY uv.lock ./uv.lock

RUN uv pip install --system .
