#!/bin/bash

set -e

echo "Building ONE FM Docker image..."
docker build --no-cache --build-arg GITHUB_TOKEN=$GITHUB_TOKEN -t one-fm:latest .

echo "Starting Docker Compose..."
docker compose -f docker-compose.local.yml up 
