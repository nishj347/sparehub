#!/bin/sh
set -e

# ==============================================================================
# SpareHub Render Production Entrypoint
# Runs database migrations and starts Uvicorn web server
# ==============================================================================

echo "[STARTUP] Running database migrations (alembic upgrade head)..."
python -m alembic upgrade head

echo "[STARTUP] Starting FastAPI backend with Uvicorn..."
exec python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-1}" \
    --proxy-headers \
    --forwarded-allow-ips '*'
