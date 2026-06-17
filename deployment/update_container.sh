#!/usr/bin/env bash
set -euo pipefail

export GHCR_IMAGE=ghcr.io/canopyflick/manon-pa-bot:latest
export COMPOSE_SERVICE=manon
export CONTAINER_NAME=manon
export COMPOSE_DIR=/home/ben/manon_deployer
export REPO_DIR=/home/ben/Manon-PA_bot
export GIT_BRANCH=main

exec /home/ben/scripts/ghcr-update-container.sh "$@"
