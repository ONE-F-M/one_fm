#!/bin/bash

set -e

echo "Force stopping ALL running containers..."
docker kill $(docker ps -q) 2>/dev/null || true

echo "Bringing down ONE FM Docker Compose (ignore errors)..."
docker compose down -v --remove-orphans || true

echo "Finding Docker volumes starting with 'one_fm'..."
volumes=$(docker volume ls -q | grep '^one_fm')

if [ -n "$volumes" ]; then
    echo "Force removing volumes..."
    docker volume rm -f $volumes
    echo "Removed volumes:"
    echo "$volumes"
else
    echo "No volumes found starting with 'one_fm'."
fi

echo "Cleanup complete."
