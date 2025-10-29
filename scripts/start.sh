#!/bin/bash

# Startup script for NearbyTix API
# This script waits for the database to be ready and runs migrations

set -e

echo "Waiting for database to be ready..."

# Wait for PostgreSQL
while ! nc -z db 5432; do
  sleep 0.1
done

echo "Database is ready!"

# Run Alembic migrations
echo "Running database migrations..."
python -m alembic upgrade head

echo "Starting FastAPI application..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
