# Obi — Obsidian Vault Telegram Bot

Obi (`@Obi_obsidianPA_bot`) is a Python Telegram bot that reads and updates the Pi's OneDrive-synced Obsidian vault mirror.

Source repo: `https://github.com/Canopyflick/Obi-PA_bot`

## Architecture

```text
Telegram long polling
  -> obi container
  -> obsidian-sync-onedrive.sh (shared with nightly backup)
  -> onedrive container
  -> /home/ben/obsidian/vault
  -> git commit/push (confirmed writes only)
  -> Canopyflick/obsidian-vault-backup
```

Obi uses the same vault lock file as the nightly backup (`/home/ben/obi/state/vault.lock`, bind-mounted as `/app/state/vault.lock` in the container).

### Vault lock contract

| Caller | Lock holder | Scope |
| --- | --- | --- |
| `obsidian-sync-onedrive.sh` (standalone) | Bash `flock` on `vault.lock` | OneDrive sync only |
| `obsidian-nightly-backup.sh` | Bash `flock -n` at start | sync → git align → commit → push |
| Obi read (`/daily`, `/search`, messages) | Sync script subprocess | OneDrive sync only |
| Obi write (Confirm) | Python `fcntl.flock` in container | sync (`--no-lock`) → append → git commit/push |

### Sync script exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `2` | Generic script error |
| `10` | OneDrive container start/restart failure |
| `124` | OneDrive sync wait timeout |
| `75` | Lock busy (`EX_TEMPFAIL`) |

Stderr includes machine-readable tags, e.g. `OBI_SYNC_ERROR: LOCK_BUSY`. Obi maps these to user-facing Telegram messages.

### Startup preflight

On container start, Obi validates vault/state paths, lock file, sync script (exists, executable, LF line endings), git dir, SSH key, and `APPROVED_USER_IDS`. On failure it logs the checklist, POSTs to the Manon error webhook, and exits without polling.

## Paths

| Item | Path |
| --- | --- |
| Deploy directory | `/home/ben/obi_deployer` |
| App source | `/home/ben/Obi-PA_bot` |
| State (pending confirmations) | `/home/ben/obi/state` |
| Vault mirror | `/home/ben/obsidian/vault` |
| Git metadata | `/home/ben/obsidian/backup-git/vault.git` |
| Sync script | `/home/ben/obsidian/scripts/obsidian-sync-onedrive.sh` |
| Container | `obi` |

## Environment (`.env` in `obi_deployer`)

Copy from `Obi-PA_bot/.env.example`. Required:

- `TELEGRAM_API_KEY` — @Obi_obsidianPA_bot token
- `APPROVED_USER_IDS` — comma-separated Telegram user IDs
- `BEN_ID` — Ben's Telegram user ID
- `OPENROUTER_API_KEY` — agent + search summarization

Optional:

- `OBI_ERROR_WEBHOOK_URL` — default `http://127.0.0.1:5678/webhook/obi-error-notify`
- `OBI_OPENROUTER_MODEL` — default `@preset/manon-fast`

## Deploy / update

### Automatic (recommended)

Push to `master` triggers GitHub Actions → GHCR image `ghcr.io/canopyflick/obi-pa-bot:latest`.

On the Pi, `update_container.sh` (hourly cron) pulls the new image and redeploys. If GHCR pull fails (403), it falls back to `git pull` in `/home/ben/Obi-PA_bot` + local build.

```bash
cd /home/ben/obi_deployer && ./update_container.sh
tail -20 /home/ben/obi_deployer/update_container.log
```

Cron line (install once):

```bash
0 * * * * cd /home/ben/obi_deployer && ./update_container.sh >> update_container.log 2>&1
```

### Manual

```bash
ssh ben@raspberrypi

cd /home/ben/Obi-PA_bot && git pull
cd /home/ben/obi_deployer && ./update_container.sh
docker logs -f obi --tail 50
```

First-time setup:

```bash
mkdir -p /home/ben/obi_deployer /home/ben/obi/state
git clone https://github.com/Canopyflick/Obi-PA_bot.git /home/ben/Obi-PA_bot
cp /home/ben/Obi-PA_bot/docker-compose.yml /home/ben/obi_deployer/
cp /home/ben/Obi-PA_bot/.env.example /home/ben/obi_deployer/.env
# edit .env with secrets
cd /home/ben/obi_deployer && docker compose build && docker compose up -d
```

Ensure `obsidian-sync-onedrive.sh` is deployed to `/home/ben/obsidian/scripts/` (from this ops repo).

## Commands

| Command | Purpose |
| --- | --- |
| `/start` | Introduction |
| `/daily` | Sync + read today's daily note |
| `/search <query>` | Keyword search + LLM summary |
| Natural language | Agent with tools (read, search, propose append) |

All writes require inline **Confirm** / **Cancel**.

## n8n integration

| Workflow | Purpose |
| --- | --- |
| **Obi Error Notify** (`lIAXPYiqqpaUZIIo`) | Webhook → Send Message via Manon (runtime errors from Obi) |

Webhook URL (Pi local): `http://127.0.0.1:5678/webhook/obi-error-notify`

## Manual tests

```bash
# Vault sync only
/home/ben/obsidian/scripts/obsidian-sync-onedrive.sh

# Obi logs (expect "Preflight OK" on healthy start)
docker logs obi --tail 100

# Vault status
/home/ben/obsidian/scripts/obsidian-sync-status.sh
```

From Telegram:

1. `/daily` — should match today's Obsidian diary after OneDrive sync
2. `/search workout` — summarized hits with note paths
3. "Add to my diary: test from Obi" — preview → Confirm → check Android Obsidian + GitHub commit
4. Ask to delete a line — should refuse without `CONFIRM DELETE`

## Safety rules (v0)

- OneDrive sync before every read/write
- Append to today's daily note only (automatic writes)
- No delete/rewrite without explicit `CONFIRM DELETE`
- Git commit only after user confirms a proposal
- Shares flock with nightly backup
