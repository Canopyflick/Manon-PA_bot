#!/usr/bin/env bash
set -euo pipefail

OBSIDIAN_BASE_DIR="${OBSIDIAN_BASE_DIR:-/home/ben/obsidian}"
OBSIDIAN_VAULT_DIR="${OBSIDIAN_VAULT_DIR:-${OBSIDIAN_BASE_DIR}/vault}"
OBSIDIAN_GIT_DIR="${OBSIDIAN_GIT_DIR:-${OBSIDIAN_BASE_DIR}/backup-git/vault.git}"
BACKUP_LOG="${OBSIDIAN_BASE_DIR}/logs/obsidian-nightly-backup.log"
ONEDRIVE_LOG_DIR="${OBSIDIAN_BASE_DIR}/logs"

git_cmd() {
  git --git-dir="$OBSIDIAN_GIT_DIR" --work-tree="$OBSIDIAN_VAULT_DIR" "$@"
}

echo "== Obsidian vault sync status =="
echo "vault_dir=${OBSIDIAN_VAULT_DIR}"

if [ -L "$OBSIDIAN_VAULT_DIR" ]; then
  echo "vault_symlink_target=$(readlink -f "$OBSIDIAN_VAULT_DIR")"
fi

if [ -d "$OBSIDIAN_VAULT_DIR" ] || [ -L "$OBSIDIAN_VAULT_DIR" ]; then
  md_count=$(find -L "$OBSIDIAN_VAULT_DIR" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
  vault_mtime=$(find -L "$OBSIDIAN_VAULT_DIR" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1 || true)
  if [ -n "${vault_mtime:-}" ]; then
    echo "latest_vault_file_epoch=${vault_mtime}"
    echo "latest_vault_file_time=$(date -d "@${vault_mtime}" --iso-8601=seconds 2>/dev/null || date -r "${vault_mtime}" --iso-8601=seconds 2>/dev/null || echo unknown)"
  fi
  echo "markdown_file_count=${md_count}"
else
  echo "vault_dir_status=missing"
fi

if command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' | grep -qx onedrive; then
    echo "onedrive_service=active"
  else
    echo "onedrive_service=inactive"
  fi
elif command -v systemctl >/dev/null 2>&1; then
  if systemctl --user is-active --quiet onedrive 2>/dev/null; then
    echo "onedrive_service=active"
  else
    echo "onedrive_service=inactive"
  fi
else
  echo "onedrive_service=unknown"
fi

if [ -d "$OBSIDIAN_GIT_DIR" ]; then
  if git_cmd rev-parse HEAD >/dev/null 2>&1; then
    echo "last_backup_commit=$(git_cmd rev-parse --short HEAD)"
    echo "last_backup_commit_time=$(git_cmd log -1 --format=%cI)"
  else
    echo "last_backup_commit=none"
  fi
  if git_cmd remote get-url origin >/dev/null 2>&1; then
    echo "git_remote=$(git_cmd remote get-url origin)"
  fi
else
  echo "git_dir_status=missing"
fi

if [ -f "$BACKUP_LOG" ]; then
  echo "last_backup_log_line=$(tail -1 "$BACKUP_LOG")"
else
  echo "last_backup_log_line=none"
fi

onedrive_log=$(find "$ONEDRIVE_LOG_DIR" -maxdepth 1 -name 'onedrive*.log' -type f 2>/dev/null | sort | tail -1)
if [ -n "${onedrive_log:-}" ] && [ -f "$onedrive_log" ]; then
  echo "last_onedrive_log_file=${onedrive_log}"
  echo "last_onedrive_log_line=$(tail -1 "$onedrive_log")"
fi
