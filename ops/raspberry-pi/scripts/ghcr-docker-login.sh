#!/usr/bin/env bash
# Log Docker into ghcr.io using the Pi's gh CLI token.
# Requires: gh auth login with read:packages scope (and repo for git pulls).
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found" >&2
  exit 1
fi

if ! gh auth status -h github.com >/dev/null 2>&1; then
  echo "gh not logged in to github.com" >&2
  echo "Run: gh auth login -h github.com -s read:packages,repo,read:org,gist" >&2
  exit 1
fi

status=$(gh auth status -h github.com 2>&1 || true)
if ! grep -q 'read:packages' <<<"$status"; then
  echo "gh token missing read:packages scope" >&2
  echo "Run: gh auth refresh -h github.com -s read:packages" >&2
  exit 1
fi

user=$(gh api user -q .login)
token=$(gh auth token)
echo "$token" | docker login ghcr.io -u "$user" --password-stdin >/dev/null
echo "GHCR docker login OK for ${user}"
