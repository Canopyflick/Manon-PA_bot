#!/usr/bin/env bash
set -euo pipefail

OBSIDIAN_BASE_DIR="${OBSIDIAN_BASE_DIR:-/home/ben/obsidian}"
OBSIDIAN_VAULT_DIR="${OBSIDIAN_VAULT_DIR:-${OBSIDIAN_BASE_DIR}/vault}"
OBSIDIAN_GIT_DIR="${OBSIDIAN_GIT_DIR:-${OBSIDIAN_BASE_DIR}/backup-git/vault.git}"
LOG_DIR="${OBSIDIAN_LOG_DIR:-${OBSIDIAN_BASE_DIR}/logs}"
LOCK_FILE="/tmp/obsidian-nightly-backup.lock"
DELETION_ABSOLUTE_THRESHOLD="${DELETION_ABSOLUTE_THRESHOLD:-100}"
DELETION_PERCENT_THRESHOLD="${DELETION_PERCENT_THRESHOLD:-20}"

mkdir -p "$LOG_DIR"
exec >> "${LOG_DIR}/obsidian-nightly-backup.log" 2>&1

log() {
  echo "[$(date --iso-8601=seconds)] $*"
}

GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -i /home/ben/.ssh/obsidian_vault_backup -o IdentitiesOnly=yes}"

git_cmd() {
  GIT_SSH_COMMAND="$GIT_SSH_COMMAND" git --git-dir="$OBSIDIAN_GIT_DIR" --work-tree="$OBSIDIAN_VAULT_DIR" "$@"
}

log "Starting Obsidian nightly backup"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "Another backup is already running; exiting"
  exit 0
fi

if [ ! -d "$OBSIDIAN_VAULT_DIR" ]; then
  log "Vault directory missing: $OBSIDIAN_VAULT_DIR"
  exit 1
fi

if [ ! -d "$OBSIDIAN_GIT_DIR" ]; then
  log "Git dir missing: $OBSIDIAN_GIT_DIR"
  exit 1
fi

if [ -e "${OBSIDIAN_VAULT_DIR}/.git" ]; then
  log "Refusing backup: .git found inside vault (would pollute OneDrive sync)"
  exit 1
fi

if [ -z "$(find -L "$OBSIDIAN_VAULT_DIR" -name "*.md" -type f -print -quit)" ]; then
  log "No Markdown files found in vault; refusing to back up suspicious path"
  exit 1
fi

if ! git_cmd remote get-url origin >/dev/null 2>&1; then
  log "Git remote 'origin' is not configured"
  exit 1
fi

if command -v docker >/dev/null 2>&1; then
  if ! docker ps --format '{{.Names}}' | grep -qx onedrive; then
    log "Warning: onedrive docker container is not running"
  fi
elif command -v systemctl >/dev/null 2>&1; then
  if ! systemctl --user is-active --quiet onedrive 2>/dev/null; then
    log "Warning: onedrive user service is not active"
  fi
fi

git_cmd add -A

deleted_count=$(git_cmd status --porcelain | awk '$1 ~ /^D/ { count++ } END { print count + 0 }')
added_count=$(git_cmd status --porcelain | awk '$1 ~ /^\?\?|^A/ { count++ } END { print count + 0 }')
modified_count=$(git_cmd status --porcelain | awk '$1 ~ /^M/ { count++ } END { print count + 0 }')
total_tracked=$(git_cmd ls-files | wc -l | tr -d ' ')

log "Changes: added=${added_count} modified=${modified_count} deleted=${deleted_count} tracked=${total_tracked}"

if [ "$total_tracked" -gt 0 ]; then
  percent_threshold=$(( (total_tracked * DELETION_PERCENT_THRESHOLD) / 100 ))
  deletion_threshold=$DELETION_ABSOLUTE_THRESHOLD
  if [ "$percent_threshold" -gt "$deletion_threshold" ]; then
    deletion_threshold=$percent_threshold
  fi
  if [ "$deleted_count" -gt "$deletion_threshold" ]; then
    log "Too many deletions (${deleted_count} > ${deletion_threshold}); refusing automatic backup"
    exit 1
  fi
fi

if git_cmd diff --cached --quiet; then
  log "No changes to commit"
  exit 0
fi

commit_msg="Nightly Obsidian backup $(date +%Y-%m-%d)"
git_cmd commit -m "$commit_msg"
git_cmd branch -M main
git_cmd push origin main
log "Backup complete: $(git_cmd rev-parse --short HEAD)"
