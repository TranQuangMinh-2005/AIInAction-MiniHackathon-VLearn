#!/bin/bash

set -e

echo "Starting backend..."

cd /app/src/agent
python3 server.py &


echo "Starting frontend..."

cd /app/src/frontend
npm run start -- -p ${PORT:-3000}

wait
