#!/bin/sh
set -e

APP_MODULE="${GUNICORN_APP_MODULE:-core.wsgi:application}"
BIND_ADDR="${GUNICORN_BIND:-0.0.0.0:8000}"
WORKERS="${GUNICORN_WORKERS:-3}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "Starting gunicorn on ${BIND_ADDR} (${WORKERS} workers)..."
exec gunicorn "$APP_MODULE" \
  --bind "$BIND_ADDR" \
  --workers "$WORKERS" \
  --timeout "$TIMEOUT" \
  --access-logfile - \
  --error-logfile -
  