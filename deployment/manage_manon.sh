#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="${MANON_DEPLOY_DIR:-$HOME/manon_deployer}"

show_logs() {
  docker logs -f --tail 100 manon
}

update() {
  cd "$DEPLOY_DIR"
  ./update_container.sh "${@:2}"
}

cleanup() {
  docker image prune -f
  find "$DEPLOY_DIR/logs" -type f -name "*.log*" -mtime +7 -delete 2>/dev/null || true
}

backup_db() {
  docker exec manon_db pg_dump -U manon manon_db > "$HOME/backups/manon_db_$(date +%Y%m%d).dump"
  echo "Database backed up to ~/backups/manon_db_$(date +%Y%m%d).dump"
}

case "${1:-}" in
  logs) show_logs ;;
  update) update "$@" ;;
  cleanup) cleanup ;;
  backup) backup_db ;;
  *)
    echo "Usage: $0 {logs|update|cleanup|backup}"
    echo "  update supports: ./update_container.sh [--dry-run] [--build-fallback]"
    exit 1
    ;;
esac
