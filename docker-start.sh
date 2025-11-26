#!/bin/bash

set -e

echo "Building ONE FM Docker image..."
docker build -t one-fm:latest .

echo "Starting Docker Compose..."
docker compose up
