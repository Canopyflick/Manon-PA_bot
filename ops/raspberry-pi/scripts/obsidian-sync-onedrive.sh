#!/usr/bin/env bash
# Shared OneDrive sync for Obsidian vault operations.
# Source from other scripts, or run directly:
#   ./obsidian-sync-onedrive.sh [--wait-lock SECONDS]
set -euo pipefail

OBSIDIAN_BASE_DIR="${OBSIDIAN_BASE_DIR:-/home/ben/obsidian}"
ONEDRIVE_CONTAINER="${ONEDRIVE_CONTAINER:-onedrive}"
ONEDRIVE_START_WAIT_SEC="${ONEDRIVE_START_WAIT_SEC:-60}"
ONEDRIVE_SYNC_TIMEOUT_SEC="${ONEDRIVE_SYNC_TIMEOUT_SEC:-900}"
OBSIDIAN_LOCK_FILE="${OBSIDIAN_LOCK_FILE:-/home/ben/obi/state/vault.lock}"

# State exported for callers that source this script
ONEDRIVE_OFFLINE_AT_START=false
ONEDRIVE_SYNC_FAILED=false

_obsidian_sync_log() {
  echo "[$(date --iso-8601=seconds)] $*"
}

ensure_onedrive_container() {
  if ! command -v docker >/dev/null 2>&1; then
    _obsidian_sync_log "Docker not available; cannot sync OneDrive"
    ONEDRIVE_SYNC_FAILED=true
    return 1
  fi

  if ! docker ps --format '{{.Names}}' | grep -qx "$ONEDRIVE_CONTAINER"; then
    ONEDRIVE_OFFLINE_AT_START=true
    _obsidian_sync_log "OneDrive container not running; starting"
    if ! (cd "$OBSIDIAN_BASE_DIR" && docker compose up -d onedrive); then
      _obsidian_sync_log "Failed to start OneDrive container"
      ONEDRIVE_SYNC_FAILED=true
      return 1
    fi
  fi

  local waited=0
  while [ "$waited" -lt "$ONEDRIVE_START_WAIT_SEC" ]; do
    if docker ps --format '{{.Names}}' | grep -qx "$ONEDRIVE_CONTAINER"; then
      return 0
    fi
    sleep 2
    waited=$((waited + 2))
  done

  _obsidian_sync_log "OneDrive container did not become ready within ${ONEDRIVE_START_WAIT_SEC}s"
  ONEDRIVE_SYNC_FAILED=true
  return 1
}

wait_for_onedrive_sync_complete() {
  local started_at elapsed=0

  _obsidian_sync_log "Restarting OneDrive container to pull latest vault changes from cloud"
  if ! docker restart "$ONEDRIVE_CONTAINER" >/dev/null 2>&1; then
    _obsidian_sync_log "Failed to restart OneDrive container"
    ONEDRIVE_SYNC_FAILED=true
    return 1
  fi

  while [ "$elapsed" -lt "$ONEDRIVE_START_WAIT_SEC" ]; do
    if docker ps --format '{{.Names}}' | grep -qx "$ONEDRIVE_CONTAINER"; then
      break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  if ! docker ps --format '{{.Names}}' | grep -qx "$ONEDRIVE_CONTAINER"; then
    _obsidian_sync_log "OneDrive container did not restart"
    ONEDRIVE_SYNC_FAILED=true
    return 1
  fi

  started_at=$(docker inspect -f '{{.State.StartedAt}}' "$ONEDRIVE_CONTAINER")
  elapsed=0

  while [ "$elapsed" -lt "$ONEDRIVE_SYNC_TIMEOUT_SEC" ]; do
    if docker logs --since "$started_at" "$ONEDRIVE_CONTAINER" 2>&1 | grep -q "Sync with Microsoft OneDrive is complete"; then
      _obsidian_sync_log "OneDrive sync complete"
      return 0
    fi
    sleep 5
    elapsed=$((elapsed + 5))
  done

  _obsidian_sync_log "Timed out waiting for OneDrive sync after ${ONEDRIVE_SYNC_TIMEOUT_SEC}s"
  ONEDRIVE_SYNC_FAILED=true
  return 1
}

sync_onedrive_vault() {
  ONEDRIVE_OFFLINE_AT_START=false
  ONEDRIVE_SYNC_FAILED=false
  ensure_onedrive_container || return 1
  wait_for_onedrive_sync_complete || return 1
}

_obsidian_sync_main() {
  local wait_lock_sec=1200
  if [ "${1:-}" = "--wait-lock" ]; then
    wait_lock_sec="${2:-1200}"
    shift 2
  fi

  exec 9>"$OBSIDIAN_LOCK_FILE"
  if ! flock -w "$wait_lock_sec" 9; then
    _obsidian_sync_log "Could not acquire vault lock within ${wait_lock_sec}s"
    exit 3
  fi

  if sync_onedrive_vault; then
    exit 0
  fi
  exit 1
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  _obsidian_sync_main "$@"
fi
