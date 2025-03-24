#!/usr/bin/env bash

# Pull the latest image first
docker pull ghcr.io/canopyflick/manon-pa-bot:latest

# Find the running container(s) based on the image name.
container_id=$(docker ps --filter "ancestor=ghcr.io/canopyflick/manon-pa-bot" --format "{{.ID}}" | head -n 1)

# Get the new image ID
new_image=$(docker images ghcr.io/canopyflick/manon-pa-bot:latest --format "{{.ID}}" | head -n 1)

if [ -z "$container_id" ]; then
  echo "No running container found. Starting container with latest image..."
  docker compose up -d
  exit 0
fi

# Get the image ID of the active running container.
current_image=$(docker inspect --format='{{.Image}}' "$container_id")
short_current_image=$(echo "$current_image" | sed 's/^sha256://' | cut -c1-12)

# Compare
if [ "$short_current_image" != "$new_image" ]; then
    echo "New image detected. Restarting container..."
    docker compose down --remove-orphans
    docker compose up -d
else
    echo "No new image detected."
fi