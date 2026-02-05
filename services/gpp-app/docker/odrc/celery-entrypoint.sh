#!/bin/bash
set -e

echo "Applying ODRC patches for Celery worker..."

# Apply all Python patches (same as main entrypoint)
for patch in /app/patches/*.py; do
    if [ -f "$patch" ]; then
        echo "Applying patch: $(basename $patch)"
        python "$patch" || echo "Warning: Patch $(basename $patch) failed"
    fi
done

echo "Patches applied."

# Start the celery worker
echo "Starting Celery worker..."
exec /celery_worker.sh
