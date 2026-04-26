#!/bin/sh
set -e

# ── Skip DB wait on Render (Supabase is always available) ────
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

# ── Collect static files ──────────────────────────────────────
echo "==> Collecting static files..."
python manage.py collectstatic --noinput

# ── Run migrations ────────────────────────────────────────────
echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Starting Gunicorn on port ${PORT}..."
exec gunicorn core.wsgi:application \
    --bind     "0.0.0.0:${PORT}" \
    --workers  2 \
    --timeout  120 \
    --access-logfile - \
    --error-logfile  -
  
