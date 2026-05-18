#!/usr/bin/env bash
# Restart the Manon bot container (recovers from hung event loops).
set -euo pipefail

DEPLOY_DIR="${MANON_DEPLOY_DIR:-$HOME/manon_deployer}"
CONTAINER_NAME="${MANON_CONTAINER_NAME:-manon}"

cd "$DEPLOY_DIR"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "$(date -Is) ERROR: container '$CONTAINER_NAME' is not running"
  exit 1
fi

echo "$(date -Is) Restarting $CONTAINER_NAME..."
docker restart "$CONTAINER_NAME"
echo "$(date -Is) Restart complete."
