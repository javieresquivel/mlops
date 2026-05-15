FROM python:3.12-slim-trixie

# [api] Install uv by copying static binaries from the official image (no curl)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /usr/local/bin/uvx

WORKDIR /app

# Install deps using pyproject (uvicorn must be listed in pyproject)
COPY pyproject.toml /app/pyproject.toml
RUN uv pip install --system .

# Copy the rest of the API source
COPY . /app
ENV PORT=8014

EXPOSE 8014
CMD ["streamlit", "run", "streamlit_predict_app.py","--server.port","8014"]