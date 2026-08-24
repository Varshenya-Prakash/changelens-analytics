#!/usr/bin/env bash
set -e

echo "Running database migrations..."
alembic upgrade head

# Seed demo data automatically on first run (idempotent: seed-demo-data no-ops
# if sites already exist).
echo "Ensuring demo data is present..."
python -m app.cli seed-demo-data || true

exec "$@"
