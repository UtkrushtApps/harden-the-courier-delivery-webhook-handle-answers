#!/usr/bin/env bash
set -e

docker compose up -d

echo "Waiting for PostgreSQL to be ready..."
until docker compose exec db pg_isready -U courier_user -d courier_db > /dev/null 2>&1; do
  sleep 1
done

echo "PostgreSQL is ready."
