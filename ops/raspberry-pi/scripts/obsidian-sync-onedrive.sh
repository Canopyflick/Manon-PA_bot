#!/usr/bin/env bash
# Shared OneDrive sync for Obsidian vault operations.
#
# VAULT LOCK CONTRACT
# All sync / git / write critical sections must hold:
#   ${OBSIDIAN_LOCK_FILE:-/home/ben/obi/state/vault.lock}
# Nightly backup acquires the lock once and holds it through sync + git + push.
# Obi read paths run this script standalone (lock held for sync only).
# Obi write paths hold the lock in Python and call with --no-lock.
#
# Usage:
#   ./obsidian-sync-onedrive.sh [--wait-lock SECONDS]
#   ./obsidian-sync-onedrive.sh --no-lock
#   ./obsidian-sync-onedrive.sh --wait-lock 1200 --no-lock   # invalid: --no-lock skips lock
set -euo pipefail

readonly EXIT_SUCCESS=0
readonly EXIT_SCRIPT_ERROR=2
readonly EXIT_ONEDRIVE_ERROR=10
readonly EXIT_SYNC_TIMEOUT=124
readonly EXIT_LOCK_BUSY=75

OBSIDIAN_BASE_DIR="${OBSIDIAN_BASE_DIR:-/home/ben/obsidian}"
ONEDRIVE_CONTAINER="${ONEDRIVE_CONTAINER:-onedrive}"
ONEDRIVE_START_WAIT_SEC="${ONEDRIVE_START_WAIT_SEC:-60}"
ONEDRIVE_SYNC_TIMEOUT_SEC="${ONEDRIVE_SYNC_TIMEOUT_SEC:-900}"
OBSIDIAN_LOCK_FILE="${OBSIDIAN_LOCK_FILE:-/home/ben/obi/state/vault.lock}"

# State exported for callers that source this script
ONEDRIVE_OFFLINE_AT_START=false
ONEDRIVE_SYNC_FAILED=false
ONEDRIVE_ERROR_KIND=""

_obsidian_sync_log() {
  echo "[$(date --iso-8601=seconds)] $*" >&2
}

_obsidian_sync_fail() {
  local tag="$1"
  local exit_code="$2"
  _obsidian_sync_log "OBI_SYNC_ERROR: ${tag}"
  exit "$exit_code"
}

open_vault_lock_file() {
  exec 9>"$OBSIDIAN_LOCK_FILE"
}

acquire_vault_lock() {
  local wait_sec="${1:-1200}"
  open_vault_lock_file
  if ! flock -w "$wait_sec" 9; then
    _obsidian_sync_fail "LOCK_BUSY" "$EXIT_LOCK_BUSY"
  fi
}

acquire_vault_lock_nowait() {
  open_vault_lock_file
  if ! flock -n 9; then
    return 1
  fi
  return 0
}

ensure_onedrive_container() {
  if ! command -v docker >/dev/null 2>&1; then
    _obsidian_sync_log "Docker not available; cannot sync OneDrive"
    ONEDRIVE_SYNC_FAILED=true
    ONEDRIVE_ERROR_KIND="container"
    return 1
  fi

  if ! docker ps --format '{{.Names}}' | grep -qx "$ONEDRIVE_CONTAINER"; then
    ONEDRIVE_OFFLINE_AT_START=true
    _obsidian_sync_log "OneDrive container not running; starting"
    if ! (cd "$OBSIDIAN_BASE_DIR" && docker compose up -d onedrive); then
      _obsidian_sync_log "Failed to start OneDrive container"
      ONEDRIVE_SYNC_FAILED=true
      ONEDRIVE_ERROR_KIND="container"
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
  ONEDRIVE_ERROR_KIND="container"
  return 1
}

wait_for_onedrive_sync_complete() {
  local started_at elapsed=0

  _obsidian_sync_log "Restarting OneDrive container to pull latest vault changes from cloud"
  if ! docker restart "$ONEDRIVE_CONTAINER" >/dev/null 2>&1; then
    _obsidian_sync_log "Failed to restart OneDrive container"
    ONEDRIVE_SYNC_FAILED=true
    ONEDRIVE_ERROR_KIND="container"
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
    ONEDRIVE_ERROR_KIND="container"
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
  ONEDRIVE_ERROR_KIND="timeout"
  return 1
}

sync_onedrive_vault() {
  ONEDRIVE_OFFLINE_AT_START=false
  ONEDRIVE_SYNC_FAILED=false
  ONEDRIVE_ERROR_KIND=""
  if ! ensure_onedrive_container; then
    return 1
  fi
  if ! wait_for_onedrive_sync_complete; then
    return 1
  fi
  return 0
}

_run_sync_with_exit_codes() {
  if sync_onedrive_vault; then
    exit "$EXIT_SUCCESS"
  fi
  if [ "$ONEDRIVE_ERROR_KIND" = "timeout" ]; then
    _obsidian_sync_fail "SYNC_TIMEOUT" "$EXIT_SYNC_TIMEOUT"
  fi
  if [ "$ONEDRIVE_SYNC_FAILED" = true ]; then
    _obsidian_sync_fail "ONEDRIVE_CONTAINER_ERROR" "$EXIT_ONEDRIVE_ERROR"
  fi
  _obsidian_sync_fail "UNKNOWN_SCRIPT_ERROR" "$EXIT_SCRIPT_ERROR"
}

_obsidian_sync_main() {
  local wait_lock_sec=1200
  local skip_lock=false

  while [ $# -gt 0 ]; do
    case "$1" in
      --wait-lock)
        wait_lock_sec="${2:-1200}"
        shift 2
        ;;
      --no-lock)
        skip_lock=true
        shift
        ;;
      *)
        _obsidian_sync_log "Unknown argument: $1"
        _obsidian_sync_fail "UNKNOWN_SCRIPT_ERROR" "$EXIT_SCRIPT_ERROR"
        ;;
    esac
  done

  if [ "$skip_lock" = true ]; then
    _run_sync_with_exit_codes
  fi

  acquire_vault_lock "$wait_lock_sec"
  _run_sync_with_exit_codes
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  _obsidian_sync_main "$@"
fi
