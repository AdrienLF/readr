FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev libxslt-dev gosu \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY app/ ./app/

RUN mkdir -p /app/data && \
    adduser --disabled-password --gecos "" --uid 1000 appuser && \
    chown -R appuser:appuser /app

EXPOSE 8000
CMD ["sh", "-c", "chown -R appuser:appuser /app/data && exec gosu appuser uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
