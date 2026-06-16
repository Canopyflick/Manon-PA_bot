#!/usr/bin/env bash
set -euo pipefail

OBSIDIAN_BASE_DIR="${OBSIDIAN_BASE_DIR:-/home/ben/obsidian}"
OBSIDIAN_VAULT_DIR="${OBSIDIAN_VAULT_DIR:-${OBSIDIAN_BASE_DIR}/vault}"
OBSIDIAN_GIT_DIR="${OBSIDIAN_GIT_DIR:-${OBSIDIAN_BASE_DIR}/backup-git/vault.git}"
LOG_DIR="${OBSIDIAN_LOG_DIR:-${OBSIDIAN_BASE_DIR}/logs}"
LOCK_FILE="/tmp/obsidian-nightly-backup.lock"
DELETION_ABSOLUTE_THRESHOLD="${DELETION_ABSOLUTE_THRESHOLD:-100}"
DELETION_PERCENT_THRESHOLD="${DELETION_PERCENT_THRESHOLD:-20}"
REPO_URL="${OBSIDIAN_BACKUP_REPO_URL:-https://github.com/Canopyflick/obsidian-vault-backup}"

mkdir -p "$LOG_DIR"
exec >> "${LOG_DIR}/obsidian-nightly-backup.log" 2>&1

NOTIFY_TEXT=""
EXIT_CODE=0
ONEDRIVE_OFFLINE_AT_START=false

log() {
  echo "[$(date --iso-8601=seconds)] $*"
}

GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -i /home/ben/.ssh/obsidian_vault_backup -o IdentitiesOnly=yes}"

git_cmd() {
  GIT_SSH_COMMAND="$GIT_SSH_COMMAND" git --git-dir="$OBSIDIAN_GIT_DIR" --work-tree="$OBSIDIAN_VAULT_DIR" "$@"
}

onedrive_context() {
  if [ "$ONEDRIVE_OFFLINE_AT_START" = true ]; then
    echo " OneDrive was offline at backup time."
  fi
}

send_nightly_notify() {
  local notify_script="${OBSIDIAN_BASE_DIR}/scripts/obsidian-backup-notify.sh"
  if [ -z "$NOTIFY_TEXT" ]; then
    NOTIFY_TEXT="📓 Obsidian nightly backup finished with unknown status"
  fi
  if [ ! -x "$notify_script" ]; then
    log "Warning: notify script missing or not executable: ${notify_script}"
    return 0
  fi
  if "$notify_script" "$NOTIFY_TEXT"; then
    log "Nightly notification sent"
  else
    log "Warning: nightly notification failed"
  fi
}

on_exit() {
  send_nightly_notify
  exit "$EXIT_CODE"
}
trap on_exit EXIT

log "Starting Obsidian nightly backup"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "Another backup is already running; exiting"
  NOTIFY_TEXT="📓 Obsidian backup skipped: another run already in progress"
  exit 0
fi

if [ ! -d "$OBSIDIAN_VAULT_DIR" ]; then
  log "Vault directory missing: $OBSIDIAN_VAULT_DIR"
  NOTIFY_TEXT="📓 Obsidian backup failed: vault directory missing"
  EXIT_CODE=1
  exit 1
fi

if [ ! -d "$OBSIDIAN_GIT_DIR" ]; then
  log "Git dir missing: $OBSIDIAN_GIT_DIR"
  NOTIFY_TEXT="📓 Obsidian backup failed: git metadata missing"
  EXIT_CODE=1
  exit 1
fi

if [ -e "${OBSIDIAN_VAULT_DIR}/.git" ]; then
  log "Refusing backup: .git found inside vault (would pollute OneDrive sync)"
  NOTIFY_TEXT="📓 Obsidian backup failed: .git found inside vault"
  EXIT_CODE=1
  exit 1
fi

if [ -z "$(find -L "$OBSIDIAN_VAULT_DIR" -name "*.md" -type f -print -quit)" ]; then
  log "No Markdown files found in vault; refusing to back up suspicious path"
  NOTIFY_TEXT="📓 Obsidian backup failed: no Markdown files in vault$(onedrive_context)"
  EXIT_CODE=1
  exit 1
fi

if ! git_cmd remote get-url origin >/dev/null 2>&1; then
  log "Git remote 'origin' is not configured"
  NOTIFY_TEXT="📓 Obsidian backup failed: git remote not configured"
  EXIT_CODE=1
  exit 1
fi

if command -v docker >/dev/null 2>&1; then
  if ! docker ps --format '{{.Names}}' | grep -qx onedrive; then
    ONEDRIVE_OFFLINE_AT_START=true
    log "Warning: onedrive docker container is not running; attempting start"
    if (cd "$OBSIDIAN_BASE_DIR" && docker compose up -d onedrive); then
      log "onedrive container start requested (vault may still be stale until sync completes)"
    else
      log "Warning: failed to start onedrive container"
    fi
  fi
elif command -v systemctl >/dev/null 2>&1; then
  if ! systemctl --user is-active --quiet onedrive 2>/dev/null; then
    ONEDRIVE_OFFLINE_AT_START=true
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
    NOTIFY_TEXT="📓 Obsidian backup refused: too many deletions (${deleted_count})"
    EXIT_CODE=1
    exit 1
  fi
fi

if git_cmd diff --cached --quiet; then
  log "No changes to commit"
  NOTIFY_TEXT="📓 No Obsidian backup: no vault changes.$(onedrive_context)"
  exit 0
fi

commit_msg="Nightly Obsidian backup $(date +%Y-%m-%d)"
git_cmd commit -m "$commit_msg"
git_cmd branch -M main
if ! git_cmd push origin main; then
  log "Git push failed"
  NOTIFY_TEXT="📓 Obsidian backup failed: git push to GitHub"
  EXIT_CODE=1
  exit 1
fi

commit_sha=$(git_cmd rev-parse --short HEAD)
commit_url="${REPO_URL}/commit/${commit_sha}"
log "Backup complete: ${commit_sha}"
NOTIFY_TEXT="📓 Obsidian vault backed up ([${commit_sha}](${commit_url}))"
exit 0
