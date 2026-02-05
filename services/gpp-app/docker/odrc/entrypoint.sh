#!/bin/bash
set -e

echo "Applying ODRC patches..."

# Apply all Python patches
for patch in /app/patches/*.py; do
    if [ -f "$patch" ]; then
        echo "Applying patch: $(basename $patch)"
        python "$patch" || echo "Warning: Patch $(basename $patch) failed"
    fi
done

echo "Patches applied."

# Wait for database to be ready
export PGHOST=${DB_HOST:-db}
export PGPORT=${DB_PORT:-5432}

until pg_isready; do
  echo "Waiting for database connection..."
  sleep 1
done

echo "Database is up."

# Run migrations and load custom fixtures before /start.sh runs
echo "Running database migrations..."
python /app/src/manage.py migrate --noinput

# Load custom fixtures (idempotent - safe to run multiple times)
if [ -d /app/fixtures ]; then
    echo "Loading custom fixtures..."
    for fixture in /app/fixtures/*.json; do
        if [ -f "$fixture" ]; then
            echo "Loading fixture: $(basename $fixture)"
            python /app/src/manage.py loaddata "$fixture" || echo "Warning: Failed to load $fixture"
        fi
    done
fi

echo "Starting application..."

# Execute the original command (skips DB wait/migrate in /start.sh since we did it)
exec "$@"
