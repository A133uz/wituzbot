#!/bin/bash
set -e

if [ "$SKIP_MIGRATIONS" != "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
    
    if [ $? -eq 0 ]; then
        echo "✅ Migrations completed successfully"
    else
        echo "❌ Migrations failed!"
        exit 1
    fi
else
    echo "⏭️  Skipping migrations (SKIP_MIGRATIONS=true)"
fi

echo "Starting FastAPI application..."
exec "$@"