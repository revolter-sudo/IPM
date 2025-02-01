#!/bin/sh

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h db -p 5432 -U "$POSTGRES_USER"; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is up - running migrations"

# Run Alembic migrations
if alembic upgrade head; then
  echo "Migrations applied successfully"
else
  echo "Alembic migrations failed!" >&2
  exit 1
fi

# Start FastAPI
echo "Starting FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
