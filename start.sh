#!/bin/bash

set -e

echo "Starting backend..."

cd /app/apps/api
PYTHONPATH=/app/apps/api:/app/libs/rag/src python3 server.py &


echo "Starting frontend..."

cd /app/apps/web
npm run start -- -p ${PORT:-3000}

wait
