# Obi — Obsidian Vault Telegram Bot

Obi (`@Obi_PA_bot`) is a Python Telegram bot that reads and updates the Pi's OneDrive-synced Obsidian vault mirror.

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

Obi uses the same vault lock file as the nightly backup (`/tmp/obsidian-nightly-backup.lock`).

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

- `TELEGRAM_API_KEY` — @Obi_PA_bot token
- `APPROVED_USER_IDS` — comma-separated Telegram user IDs
- `BEN_ID` — Ben's Telegram user ID
- `OPENROUTER_API_KEY` — agent + search summarization

Optional:

- `OBI_ERROR_WEBHOOK_URL` — default `http://127.0.0.1:5678/webhook/obi-error-notify`
- `OBI_OPENROUTER_MODEL` — default `@preset/manon-fast`

## Deploy / update

```bash
ssh ben@raspberrypi

cd /home/ben/Obi-PA_bot && git pull
cd /home/ben/obi_deployer
docker compose build
docker compose up -d
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

# Obi logs
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
