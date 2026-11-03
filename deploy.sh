#!/bin/sh
# One-command deploy: Docker if available, otherwise plain Python.
set -e
cd "$(dirname "$0")"
if command -v docker >/dev/null 2>&1; then
  echo "Building and starting Couch Clash in Docker ..."
  docker compose up -d --build
  echo "Ready: http://localhost:8000/  (health: /api/health)"
else
  echo "Docker not found — running directly with Python."
  exec python3 server.py
fi
