#!/usr/bin/env bash
# Shared GHCR pull + conditional redeploy for Pi bot containers.
#
# Required env: GHCR_IMAGE, COMPOSE_SERVICE, CONTAINER_NAME
# Optional env: COMPOSE_DIR, LOCK_FILE, REPO_DIR, GIT_BRANCH, GHCR_LOGIN_SCRIPT
#
# Flags:
#   --dry-run         pull and compare only; never redeploy
#   --build-fallback  on GHCR failure: git pull + compose build (manual recovery)
set -euo pipefail

BUILD_FALLBACK=false
DRY_RUN=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-fallback) BUILD_FALLBACK=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--dry-run] [--build-fallback]" >&2
      exit 2
      ;;
  esac
done

: "${GHCR_IMAGE:?GHCR_IMAGE required}"
: "${COMPOSE_SERVICE:?COMPOSE_SERVICE required}"
: "${CONTAINER_NAME:?CONTAINER_NAME required}"

COMPOSE_DIR="${COMPOSE_DIR:-$(pwd)}"
GHCR_LOGIN_SCRIPT="${GHCR_LOGIN_SCRIPT:-/home/ben/ghcr-docker-login.sh}"

log() {
  echo "[$(date --iso-8601=seconds)] $*"
}

log_result() {
  local old_digest="$1"
  local new_digest="$2"
  local redeploy="$3"
  local extra="${4:-}"
  log "image=${GHCR_IMAGE} container=${CONTAINER_NAME} old=${old_digest:-none} new=${new_digest} redeploy=${redeploy}${extra}"
}

running_container_id() {
  docker ps -q -f "name=^${CONTAINER_NAME}$" | head -n 1
}

running_digest() {
  local cid
  cid=$(running_container_id)
  if [[ -z "$cid" ]]; then
    echo ""
    return 0
  fi
  docker inspect --format '{{.Image}}' "$cid"
}

image_digest() {
  docker image inspect "$GHCR_IMAGE" --format '{{.Id}}'
}

vault_lock_held() {
  [[ -z "${LOCK_FILE:-}" ]] && return 1
  exec 200>"$LOCK_FILE"
  if flock -n 200; then
    flock -u 200
    return 1
  fi
  return 0
}

redeploy_service() {
  cd "$COMPOSE_DIR"
  docker compose up -d --no-build "$COMPOSE_SERVICE"
}

build_fallback() {
  : "${REPO_DIR:?REPO_DIR required for --build-fallback}"
  : "${GIT_BRANCH:?GIT_BRANCH required for --build-fallback}"

  log "build-fallback: git pull in ${REPO_DIR}"
  git -C "$REPO_DIR" pull --ff-only origin "$GIT_BRANCH"
  cd "$COMPOSE_DIR"
  docker compose build "$COMPOSE_SERVICE"
  docker compose up -d "$COMPOSE_SERVICE"
}

ghcr_login_and_pull() {
  if [[ ! -x "$GHCR_LOGIN_SCRIPT" ]]; then
    log "GHCR login script missing or not executable: ${GHCR_LOGIN_SCRIPT}"
    return 1
  fi
  if ! "$GHCR_LOGIN_SCRIPT"; then
    log "GHCR login failed"
    return 1
  fi
  if ! docker pull "$GHCR_IMAGE"; then
    log "GHCR pull failed for ${GHCR_IMAGE}"
    return 1
  fi
  return 0
}

main() {
  local old_digest new_digest redeploy=false

  if ! ghcr_login_and_pull; then
    if [[ "$BUILD_FALLBACK" == true ]]; then
      log "GHCR unavailable; using --build-fallback"
      if [[ "$DRY_RUN" == true ]]; then
        log "dry-run: would run build-fallback for ${CONTAINER_NAME}"
        exit 0
      fi
      build_fallback
      new_digest=$(image_digest)
      log_result "" "$new_digest" "yes" " method=build-fallback"
      exit 0
    fi
    exit 1
  fi

  new_digest=$(image_digest)
  old_digest=$(running_digest)

  if [[ -z "$old_digest" ]]; then
    log "container ${CONTAINER_NAME} not running"
    if [[ "$DRY_RUN" == true ]]; then
      log_result "$old_digest" "$new_digest" "yes" " (dry-run)"
      exit 0
    fi
    redeploy_service
    log_result "$old_digest" "$new_digest" "yes" " reason=not-running"
    exit 0
  fi

  if [[ "$old_digest" == "$new_digest" ]]; then
    log "already up to date"
    log_result "$old_digest" "$new_digest" "no"
    exit 0
  fi

  if vault_lock_held; then
    log "Obi vault operation in progress; skipping update."
    log_result "$old_digest" "$new_digest" "no" " reason=vault-lock"
    exit 0
  fi

  if [[ "$DRY_RUN" == true ]]; then
    log_result "$old_digest" "$new_digest" "yes" " (dry-run)"
    exit 0
  fi

  redeploy_service
  log_result "$old_digest" "$new_digest" "yes"
}

main
