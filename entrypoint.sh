#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head
echo "Database migrations completed successfully."
echo "Current database version:"
alembic current || true

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000