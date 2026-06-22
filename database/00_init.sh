#!/bin/bash
set -e

echo "=== NeuroDB Database Initialization ==="

for f in /docker-entrypoint-initdb.d/*.sql; do
  echo "Running: $f"
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$f"
done

echo "=== Database initialization complete ==="
