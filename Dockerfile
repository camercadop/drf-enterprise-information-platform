# --- Stage 1: Builder ---
FROM python:3.14-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

RUN uv sync --no-dev --frozen

COPY . .

# --- Stage 2: Runtime ---
FROM python:3.14-slim

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

COPY --from=builder /app/.venv /app/.venv
COPY . .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live/')" || exit 1

CMD [".venv/bin/gunicorn", "--bind", "0.0.0.0:8000", "--log-level", "info", "--limit-request-line", "4094", "config.wsgi:application"]