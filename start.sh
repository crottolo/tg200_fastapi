#!/bin/bash
# Production startup script for TG200 FastAPI Gateway

set -e

echo "Starting TG200 FastAPI Gateway..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "WARNING: .env file not found. Using default configuration."
fi

# Run FastAPI with Uvicorn
# For Coolify, use port 3000 (default)
# For production, use multiple workers
# Enable proxy headers for reverse proxy support
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-3000} \
    --workers ${WORKERS:-1} \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --log-level info
