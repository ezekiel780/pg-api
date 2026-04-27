#!/bin/sh
set -e

if [ -z "$DATABASE_URL" ]; then
    DB_HOST="${DB_HOST:-db}"
    DB_PORT="${DB_PORT:-5432}"
    echo "==> Waiting for database at ${DB_HOST}:${DB_PORT}..."
    while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; do
        sleep 1
    done
    echo "==> Database is ready."
else
    echo "==> Using DATABASE_URL — skipping wait."
fi

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Starting Celery worker in background..."
celery -A core worker \
    --loglevel=info \
    --concurrency=1 \
    --queues=reconciliation,celery &

echo "==> Starting Gunicorn on port ${PORT}..."
exec gunicorn core.wsgi:application \
    --bind     "0.0.0.0:${PORT}" \
    --workers  2 \
    --timeout  120 \
    --access-logfile - \
    --error-logfile  -
    