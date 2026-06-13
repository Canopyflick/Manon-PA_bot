#!/usr/bin/env bash
set -euo pipefail

OBSIDIAN_BASE_DIR="${OBSIDIAN_BASE_DIR:-/home/ben/obsidian}"
CONF_DIR="${OBSIDIAN_BASE_DIR}/onedrive-conf"
AUTH_URL_FILE="${CONF_DIR}/auth-url"
AUTH_RESPONSE_FILE="${CONF_DIR}/auth-response"
CONTAINER_NAME="onedrive-auth"

cleanup() {
  docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true
}

echo "Starting interactive OneDrive browser authentication."
echo "Personal Microsoft accounts (@hotmail.com etc.) cannot use device-code login."
echo

docker stop onedrive 2>/dev/null || true
cleanup
rm -f "${AUTH_URL_FILE}" "${AUTH_RESPONSE_FILE}"

docker run -d \
  --name "${CONTAINER_NAME}" \
  -e ONEDRIVE_UID="$(id -u)" \
  -e ONEDRIVE_GID="$(id -g)" \
  -e ONEDRIVE_VERBOSE=1 \
  -e ONEDRIVE_AUTHFILES="/onedrive/conf/auth-url:/onedrive/conf/auth-response" \
  -v "${CONF_DIR}:/onedrive/conf" \
  -v "${OBSIDIAN_BASE_DIR}/onedrive:/onedrive/data" \
  -v "${OBSIDIAN_BASE_DIR}/logs:/onedrive/logs" \
  driveone/onedrive:debian

echo "Waiting for authorize URL..."
for _ in $(seq 1 30); do
  if [[ -s "${AUTH_URL_FILE}" ]]; then
    break
  fi
  sleep 1
done

if [[ ! -s "${AUTH_URL_FILE}" ]]; then
  echo "Authorize URL was not written. Container logs:"
  docker logs "${CONTAINER_NAME}" 2>&1 | tail -20
  cleanup
  exit 1
fi

echo
echo "Open this URL in your browser, sign in, and approve MFA:"
cat "${AUTH_URL_FILE}"
echo
echo "After sign-in, the browser redirects to a blank page."
echo "Copy the full address bar URL (starts with https://login.microsoftonline.com/common/oauth2/nativeclient?code=...)"
echo
read -r -p "Paste redirect URL here: " auth_response

if [[ -z "${auth_response}" ]]; then
  echo "No redirect URL provided."
  cleanup
  exit 1
fi

printf '%s\n' "${auth_response}" > "${AUTH_RESPONSE_FILE}"

echo "Waiting for OneDrive client to finish authentication..."
if docker wait "${CONTAINER_NAME}" >/dev/null; then
  echo
  echo "Auth finished. Start monitor with:"
  echo "  cd ${OBSIDIAN_BASE_DIR} && docker compose up -d"
else
  echo "Auth container failed. Logs:"
  docker logs "${CONTAINER_NAME}" 2>&1 | tail -30
  cleanup
  exit 1
fi

cleanup
