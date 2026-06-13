# Raspberry Pi Context

This file captures operational context learned during the June 2026 rebuild.

## Architecture

```text
Telegram long polling
  -> manon container
  -> manon_db Postgres container
  -> Docker volume manon-pa_bot_pgdata

n8n.bentenberge.com
  -> Cloudflare Tunnel
  -> localhost:5678
  -> n8n-n8n-1 container
  -> Docker volume n8n_n8n_data
```

Manon does not use a public webhook. It uses Telegram `run_polling()`.

## Manon

- Deploy directory: `/home/ben/manon_deployer`
- Compose file: `/home/ben/manon_deployer/docker-compose.yml`
- Env file: `/home/ben/manon_deployer/.env`
- Containers:
  - `manon`
  - `manon_db`
- Postgres DB:
  - database: `manon_db`
  - user: `manon`
  - container hostname from Manon: `manon_db` in the deployed `.env`
- Docker volume: `manon-pa_bot_pgdata`
- App source on Pi, if present: `/home/ben/Manon-PA_bot`

Manon creates/updates its own schema at startup in `utils/db.py`.

Important tables:

- `manon_users`
- `manon_goals`
- `manon_reminders`
- `day_snapshots`
- `manon_stats_snapshots`

`/wassup` reads open-ended goals from `manon_goals` with `status = 'prepared'`.

## n8n

- Deploy directory: `/home/ben/n8n`
- Compose file: `/home/ben/n8n/docker-compose.yml`
- Container: `n8n-n8n-1`
- Docker volume: `n8n_n8n_data`
- Public URL: `https://n8n.bentenberge.com`
- Tunnel service: `cloudflared`
- Tunnel config: `/etc/cloudflared/config.yml`

The `N8N_ENCRYPTION_KEY` must remain stable for existing encrypted credentials. Do not rotate it casually.

### Cursor automation (local Windows repo)

Local secrets for Cursor agents live in `ops/raspberry-pi/.env` (gitignored via `*.env`). Copy `.env.example` and fill in values.

| Variable | Purpose |
| --- | --- |
| `N8N_API_KEY` | REST API at `https://n8n.bentenberge.com/api/v1` |
| `NATHAN_TELEGRAM_BOT_API_KEY` | Telegram bot token for Nathan (@Nathan_PA_bot) credential creation |
| `MANON_TELEGRAM_BOT_API_KEY` | Telegram bot token for Manon (@Manon_PA_bot) — outbound sub-workflow |
| `TELEGRAM_USER_ID_BEN` | Default chat ID for Manon test sends |

### n8n MCP (`user-n8n-mcp`)

Official n8n Workflow SDK MCP, connected to `https://n8n.bentenberge.com`.

**Can:** create/update/publish/execute workflows via SDK code; search nodes; validate workflows; list/assign credentials; test with pin data; manage data tables.

**Cannot:** create credentials that contain secrets (MCP only lists credential metadata).

**Workflow build pipeline:**

1. `get_sdk_reference` (read SDK patterns first)
2. `search_nodes` / `get_suggested_nodes`
3. `get_node_types` (exact parameter names — do not guess)
4. `validate_workflow`
5. `create_workflow_from_code` or `update_workflow`

### n8n REST API

Uses `N8N_API_KEY` from local `.env`. Base URL: `https://n8n.bentenberge.com/api/v1`.

**Can:** `POST /credentials` for token-based creds (Telegram `telegramApi`, OpenRouter `openRouterApi`); full workflow JSON import/export; list/trigger executions.

**Cannot:** OAuth credential creation (Google Calendar requires browser OAuth in n8n UI).

**Pattern:** MCP builds workflow structure and assigns credential IDs → REST API creates credentials from `.env` secrets when MCP cannot.

Example credential create (PowerShell):

```powershell
$headers = @{ "X-N8N-API-KEY" = $env:N8N_API_KEY; "Content-Type" = "application/json" }
$body = @{ name = "Nathan"; type = "telegramApi"; data = @{ accessToken = $env:NATHAN_TELEGRAM_BOT_API_KEY } } | ConvertTo-Json
Invoke-RestMethod -Uri "https://n8n.bentenberge.com/api/v1/credentials" -Method Post -Headers $headers -Body $body
```

### Credentials (post-rebuild inventory)

| Name | Type | Notes |
| --- | --- | --- |
| Nathan | `telegramApi` | Telegram bot @Nathan_PA_bot |
| Manon | `telegramApi` | Telegram bot @Manon_PA_bot — outbound only |
| OpenRouter Persoonlijk | `openRouterApi` | LLM routing |
| Google Calendar | OAuth | User must connect in n8n UI — not automatable via MCP/API |

### Workflows (created in recent sessions)

| Workflow | Purpose |
| --- | --- |
| MCP Connection Test | Manual trigger — verifies MCP connectivity |
| Nathan Telegram Test | Manual trigger — sends a Telegram test message |
| Nathan Calendar Bot | Telegram Trigger → AI Agent + Google Calendar tools → Telegram reply |
| **Send Message via Manon** (`zCzJmgdkSZwCKWo3`) | Sub-workflow — call via **Execute Sub-workflow** to send Telegram messages from @Manon_PA_bot |
| Test Send Message via Manon (`EU17ZwFO5PSBxd9s`) | Manual test harness for the Manon sub-workflow |

**Send Message via Manon** input contract (all fields optional except `text`):

```json
{ "chatId": "1875436366", "text": "Your message", "parseMode": "Markdown" }
```

Defaults: `chatId` → Ben's Telegram user ID, `parseMode` → `Markdown`.

Workflow names/IDs may drift; search in n8n UI or via MCP/API if IDs are needed.

### Chat Hub vs Telegram workflow agents

These are different surfaces — do not confuse them.

| Surface | URL / trigger | Callable from Telegram? |
| --- | --- | --- |
| **Chat Hub** (Personal Agent) | `/home/chat?agentId=...` | No — browser-only n8n chat UI |
| **Telegram bot workflow** | Telegram Trigger node + AI Agent | Yes |

To expose a workflow in Chat Hub: use a **Chat Trigger** with "Make Available in n8n Chat" plus a streaming **AI Agent** node.

Telegram bots need a workflow with **Telegram Trigger** (not Chat Trigger) plus an **AI Agent** node.

## Scheduled Jobs

User crontab on the Pi:

```cron
17 3 * * * /home/ben/backup_services.sh >> /home/ben/backups/backup.log 2>&1
05 3 * * * /home/ben/manon_healthcheck.sh >> /home/ben/healthchecks/cron.log 2>&1
0 4 * * * /home/ben/manon_deployer/weekly_restart.sh >> /home/ben/manon_deployer/weekly_restart.log 2>&1
```

## Health And Recovery Scripts

- `/home/ben/manon_healthcheck.sh`
  - checks Docker, DNS, Telegram reachability, Postgres readiness, and Manon state
  - starts/recreates Manon if needed
  - logs to `/home/ben/healthchecks/manon_healthcheck.log`
- `/home/ben/backup_services.sh`
  - writes a Manon SQL dump
  - archives the n8n Docker volume
  - archives deploy config files
  - keeps local backups for 30 days
- `/home/ben/manon_deployer/weekly_restart.sh`
  - restarts the Manon container

Despite the old name, `weekly_restart.sh` is currently scheduled daily at 04:00.

## Known Failure Modes

### Manon Exited Cleanly After DNS Failure

Observed problem:

- `manon` exited with `ExitCode=0`
- logs showed `telegram.error.NetworkError: httpx.ConnectError: [Errno -3] Temporary failure in name resolution`
- Docker did not restart it because compose used `restart: on-failure:5`

Fix applied:

- compose restart policy changed to `unless-stopped`
- daily healthcheck added
- daily restart added

### GHCR Pull 403

Observed problem:

- pulling `ghcr.io/canopyflick/manon-pa-bot:latest` returned `403 Forbidden`

Workaround used:

- cloned `https://github.com/Canopyflick/Manon-PA_bot`
- built locally on the Pi
- tagged the local image as `ghcr.io/canopyflick/manon-pa-bot:latest`

Long-term fix:

- fix GitHub Container Registry package visibility/permissions or PAT scopes
- then restore update automation using `/home/ben/manon_deployer/update_container.sh`

### Timezone Drift

Observed problem:

- fresh Pi was set to `Europe/London`
- app internals still used Berlin, but cron followed host timezone

Fix applied:

- host timezone changed to `Europe/Berlin`

## Security Notes

The backup used during rebuild contained live secrets: `.env`, SSH keys, GHCR/GitHub tokens, Cloudflare credentials, Telegram/OpenAI tokens. Rotate secrets when practical.

Do not commit:

- `.env`
- Cloudflare tunnel credential JSON
- SSH private keys
- Docker config files with auth tokens
- backup tarballs or SQL dumps
