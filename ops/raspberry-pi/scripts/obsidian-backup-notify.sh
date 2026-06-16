#!/usr/bin/env bash
set -euo pipefail

OBSIDIAN_BASE_DIR="${OBSIDIAN_BASE_DIR:-/home/ben/obsidian}"
NOTIFY_ENV="${OBSIDIAN_NOTIFY_ENV:-${OBSIDIAN_BASE_DIR}/notify.env}"
NOTIFY_WEBHOOK_URL="${OBSIDIAN_NOTIFY_WEBHOOK_URL:-http://127.0.0.1:5678/webhook/obsidian-backup-notify}"

if [ -f "$NOTIFY_ENV" ]; then
  # shellcheck source=/dev/null
  source "$NOTIFY_ENV"
fi

text="${1:-}"
if [ -z "$text" ]; then
  echo "Usage: obsidian-backup-notify.sh MESSAGE" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

payload=$(jq -n --arg text "$text" '{text: $text}')

curl -fsS --max-time 30 -X POST "$NOTIFY_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$payload"
