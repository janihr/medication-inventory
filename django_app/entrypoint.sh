#!/bin/sh
set -e

echo "Waiting for database..."
while ! python -c "
import os, psycopg2
conn = psycopg2.connect(
    dbname=os.environ.get('POSTGRES_DB'),
    user=os.environ.get('POSTGRES_USER'),
    password=os.environ.get('POSTGRES_PASSWORD'),
    host=os.environ.get('DATABASE_HOST', 'db'),
    port=os.environ.get('DATABASE_PORT', '5432'),
)
conn.close()
" 2>/dev/null; do
    echo "Database not ready, waiting..."
    sleep 2
done
echo "Database is ready!"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating default admin user..."
python manage.py create_default_admin --username admin --email admin@example.com --password admin123

# Setup cron for scheduled backups
echo "Setting up backup cron job..."
mkdir -p /app/backups

# Write environment variables to a file for cron to use
printenv | grep -E '^(POSTGRES_|DJANGO_|DATABASE_|PATH=)' > /app/.env.cron

# Create cron job that runs every hour to check if backup is due
echo "0 * * * * cd /app && export \$(cat /app/.env.cron | xargs) && /usr/local/bin/python manage.py run_scheduled_backup >> /var/log/cron.log 2>&1" > /etc/cron.d/backup-cron
chmod 0644 /etc/cron.d/backup-cron
crontab /etc/cron.d/backup-cron

# Start cron in background
cron

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -