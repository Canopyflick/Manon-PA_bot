#!/usr/bin/env bash
set -euo pipefail

OBSIDIAN_BASE_DIR="${OBSIDIAN_BASE_DIR:-/home/ben/obsidian}"

echo "Starting interactive OneDrive device authentication."
echo "A code and URL will appear below. Complete sign-in in your browser."
echo

docker rm -f onedrive-auth 2>/dev/null || true
docker run --rm -it \
  --name onedrive-auth \
  -e ONEDRIVE_UID="$(id -u)" \
  -e ONEDRIVE_GID="$(id -g)" \
  -e ONEDRIVE_SYNC_ONCE=1 \
  -v "${OBSIDIAN_BASE_DIR}/onedrive-conf:/onedrive/conf" \
  -v "${OBSIDIAN_BASE_DIR}/onedrive:/onedrive/data" \
  -v "${OBSIDIAN_BASE_DIR}/logs:/onedrive/logs" \
  driveone/onedrive:debian

echo
echo "Auth/sync finished. Start monitor with:"
echo "  cd ${OBSIDIAN_BASE_DIR} && docker compose up -d"
