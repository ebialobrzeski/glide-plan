#!/bin/sh
# Container entrypoint for GlideLog.
#
# Database migrations for the logbook tables (026-037) are owned by the main
# GlidePlan app and share the same schema_migrations ledger; init_db() applies
# any pending ones idempotently at app import, so we go straight to gunicorn.
set -e

echo "[entrypoint] Starting gunicorn…"
exec gunicorn \
    --bind 0.0.0.0:5001 \
    --workers 2 \
    --threads 2 \
    --timeout 120 \
    app:app
