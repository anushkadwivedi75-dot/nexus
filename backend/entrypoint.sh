#!/bin/sh
set -e

echo "[Nexus Backend] Starting container initialization..."

# Wait for PostgreSQL to be ready if POSTGRES_HOST is set
if [ -n "$POSTGRES_HOST" ]; then
    echo "[Nexus Backend] Waiting for PostgreSQL at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
    timeout=60
    while ! nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}" 2>/dev/null; do
        timeout=$((timeout - 1))
        if [ "$timeout" -le 0 ]; then
            echo "[Nexus Backend] ERROR: Timed out waiting for PostgreSQL."
            exit 1
        fi
        sleep 1
    done
    echo "[Nexus Backend] PostgreSQL is available."
fi

# Run database migrations if configured
if [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "[Nexus Backend] Running Alembic database migrations (upgrade head)..."
    alembic upgrade head
    echo "[Nexus Backend] Migrations applied successfully."
fi

echo "[Nexus Backend] Launching Uvicorn production server on 0.0.0.0:8000..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WEB_CONCURRENCY:-2}" \
    --proxy-headers \
    --forwarded-allow-ips="*" \
    --log-level "${LOG_LEVEL:-info}"

