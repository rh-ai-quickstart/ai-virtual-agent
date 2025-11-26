#!/bin/bash

# AI Virtual Agent - Backend Development Startup Script
# This script runs database migrations before starting the development server

set -e

echo "🚀 Starting backend with auto-migrations..."

# Change to backend directory for alembic
cd /app/backend

# Wait for database to be ready
echo "⏳ Waiting for database..."
while ! nc -z db 5432; do
    echo "Database not ready, waiting..."
    sleep 2
done

echo "✅ Database is ready!"

# Run database migrations
echo "🔄 Running migrations..."
alembic upgrade head

echo "✅ Migrations completed!"

# Start the development server
echo "🌟 Starting development server..."
cd /app

# Check if coverage is enabled (for integration tests)
if [ "${ENABLE_COVERAGE:-false}" = "true" ]; then
    echo "📊 Coverage collection enabled (reload disabled for accurate coverage)"
    exec coverage run --source=backend --data-file=/app/.coverage.integration -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
else
    echo "🔥 Hot reload enabled for development"
    exec uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
fi
