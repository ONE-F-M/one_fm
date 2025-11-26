#!/bin/bash

set -e

echo "Stopping ONE FM Docker Compose..."
docker compose down

echo "Removing Docker volumes starting with 'one_fm'..."
volumes=$(docker volume ls -q | grep '^one_fm')

if [ -n "$volumes" ]; then
    docker volume rm -f $volumes
    echo "Removed volumes: $volumes"
else
    echo "No volumes found starting with 'one_fm'."
fi
