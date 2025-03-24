#!/usr/bin/env bash

set -e

# Pull the latest image first
docker pull ghcr.io/canopyflick/manon-pa-bot:latest

# Get new image ID
new_image=$(docker images ghcr.io/canopyflick/manon-pa-bot:latest --format "{{.ID}}" | head -n 1)

# Check for existing running container
container_id=$(docker ps --filter "ancestor=ghcr.io/canopyflick/manon-pa-bot" --format "{{.ID}}" | head -n 1)

if [ -z "$container_id" ]; then
  echo "No running container found. Starting container with latest image..."
  docker compose down --remove-orphans || true
  docker compose up -d
  exit 0
fi

# Get running container's image
current_image=$(docker inspect --format='{{.Image}}' "$container_id")
short_current_image=$(echo "$current_image" | sed 's/^sha256://' | cut -c1-12)

# Compare
if [ "$short_current_image" != "$new_image" ]; then
    echo "New image detected. Restarting container..."

    echo "Stopping and removing existing containers..."
    docker compose down --remove-orphans || true

    # Also remove leftover containers by name (just in case)
    docker rm -f manon_db || true
    docker rm -f manon || true

    echo "Starting updated container..."
    docker compose up -d
else
    echo "No new image detected."
fi
