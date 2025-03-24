#!/bin/bash

function show_logs() {
  cd ~/manon_deployer
  docker logs manon -f
}

function update() {
  cd ~/manon_deployer
  ./update_container.sh
}

function cleanup() {
  # Remove dangling images
  docker image prune -f
  # Remove old logs that are older than 7 days
  find ~/manon_deployer/logs -type f -name "*.log*" -mtime +7 -delete
}

function backup_db() {
  cd ~/manon_deployer
  docker exec manon_db pg_dump -U manon manon_db > ~/backups/manon_db_$(date +%Y%m%d).dump
  echo "Database backed up to ~/backups/manon_db_$(date +%Y%m%d).dump"
}

case "$1" in
  logs) show_logs ;;
  update) update ;;
  cleanup) cleanup ;;
  backup) backup_db ;;
  *) echo "Usage: $0 {logs|update|cleanup|backup}" ;;
esac
EOF

chmod +x ~/manage_manon.sh