#!/bin/bash

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
mkdir -p /app/uploads/payments/users
mkdir -p /app/uploads/admin
mkdir -p /app/uploads/khatabook_files

# Create logs directory if it doesn't exist (using LOG_DIR env var or default)
LOG_DIR=${LOG_DIR:-/app/logs}
mkdir -p "$LOG_DIR"
echo "Logs directory created: $LOG_DIR"

# Create all log files with proper permissions to prevent Docker recreation issues
touch "$LOG_DIR/ipm.log"
touch "$LOG_DIR/ipm_api.log"
touch "$LOG_DIR/ipm_database.log"
touch "$LOG_DIR/ipm_performance.log"
touch "$LOG_DIR/ipm_errors.log"

# Set proper permissions for log files
chmod 666 "$LOG_DIR"/*.log
chown -R 1000:1000 "$LOG_DIR" 2>/dev/null || true

echo "Log files initialized with proper permissions"

# Start FastAPI
echo "Starting FastAPI..."
exec uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --workers 4
