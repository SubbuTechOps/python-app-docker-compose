#!/bin/bash
set -e

echo "🔄 Waiting for MySQL to be available at $DB_HOST:$DB_PORT..."

# Wait for MySQL to be ready before running the app
until mysqladmin ping -h"$DB_HOST" --silent; do
    echo "⏳ MySQL is unavailable - sleeping..."
    sleep 5
done

echo "✅ MySQL is up - Starting the application..."

# Start Gunicorn server with appropriate settings
exec gunicorn --bind 0.0.0.0:5000 \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --capture-output \
    "wsgi:app"
