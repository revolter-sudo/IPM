#!/bin/sh

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until nc -z -v -w30 147.93.31.224 5432; do
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

# Create uploads directory if it doesn't exist
mkdir -p /app/uploads
mkdir -p /app/uploads/payments
mkdir -p /app/uploads/admin
mkdir -p /app/uploads/khatabook_files

# Start FastAPI
echo "Starting FastAPI..."
exec uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --workers 4
