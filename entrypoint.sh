#!/bin/sh

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h db -p 5432 -U "$POSTGRES_USER"; do
  sleep 2
done

# Run database migrations
echo "Running Alembic migrations..."
alembic upgrade head

# Start FastAPI
echo "Starting FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
