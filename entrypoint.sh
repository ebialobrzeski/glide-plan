#!/bin/sh
# Container entrypoint — runs pending DB migrations then starts the app.
set -e

echo "[entrypoint] Running database migrations…"
python -m backend.migrate

echo "[entrypoint] Starting gunicorn…"
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --threads 2 \
    --timeout 120 \
    app:app
