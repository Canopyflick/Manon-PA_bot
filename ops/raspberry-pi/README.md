# Raspberry Pi Ops Workspace

This directory is the starting point for future work on Ben's Raspberry Pi services.

It is intentionally secret-free. Keep live tokens, passwords, private keys, Cloudflare tunnel credentials, and `.env` values on the Pi or in a password manager, not in this repo.

## Current Pi

- SSH target: `ben@raspberrypi`
- Host timezone: `Europe/Berlin`
- Main deploy directory: `/home/ben/manon_deployer`
- n8n deploy directory: `/home/ben/n8n`
- Obsidian vault directory: `/home/ben/obsidian`
- Local backup root: `/home/ben/backups`

## Services

- `manon`: Telegram bot container, image `ghcr.io/canopyflick/manon-pa-bot:latest` (auto-updated via cron, see `docs/bot-ghcr-deploy.md`)
- `manon_db`: Postgres 17 container for Manon
- `obi`: Obsidian vault Telegram bot, image `ghcr.io/canopyflick/obi-pa-bot:latest` (auto-updated via cron)
- `n8n-n8n-1`: n8n container, exposed through Cloudflare Tunnel
- `cloudflared`: systemd service for `n8n.bentenberge.com`
- `cron`: local scheduled backups and health checks
- `onedrive`: Docker container syncing Obsidian vault from OneDrive

## Useful Entry Points

- `context.md`: high-level architecture, known gotchas, and recovery notes.
- `docs/bot-ghcr-deploy.md`: Manon & Obi GHCR build/pull/redeploy pattern (cron, scripts, auth).
- `docs/obsidian-vault-backup.md`: Obsidian vault sync and GitHub backup runbook.
- `docs/obi-vault-bot.md`: Obi vault bot paths, lock contract, and runtime behavior.
- `obsidian-vault/`: Windows-side vault tooling (Diary analysis, git snapshots). See `obsidian-vault/README.md`.
- `runbooks.md`: commands for diagnosis, restart, backups, restore, and updates.
- `scripts/quick-check.ps1`: Windows-side SSH health check.
- `scripts/tail-logs.ps1`: Windows-side SSH log tail helper.
- `private-notes.example.md`: template for private notes that should not be committed.
- `.env.example`: placeholder keys for local Cursor/n8n automation (copy to `.env`; gitignored).

## Cursor + n8n Automation

Ben's n8n instance (`https://n8n.bentenberge.com`) can be managed from Cursor via two tools:

| Tool | Use for |
| --- | --- |
| **n8n MCP** (`user-n8n-mcp`) | Build/validate/update workflows with the Workflow SDK; search nodes; assign credentials; pin-data tests |
| **n8n REST API** (`N8N_API_KEY` in local `.env`) | Create token-based credentials (Telegram, OpenRouter); full workflow JSON; executions |

**Pattern:** MCP builds workflows → REST API creates credentials from `.env` secrets → MCP assigns credential IDs to nodes.

Workflow build pipeline: `get_sdk_reference` → `search_nodes` → `get_node_types` → `validate_workflow` → `create_workflow_from_code`.

OAuth credentials (e.g. Google Calendar) must be connected in the n8n UI; neither MCP nor API can complete browser OAuth.

See `context.md` (n8n section) for credentials inventory, existing workflows, and Chat Hub vs Telegram bot patterns.

## Cursor + Obsidian Vault

Daily notes and vault edits from Cursor use `obsidian-vault/` (Windows git mirror + read-only Diary analyzer). Always git-snapshot before and after vault mutations. See `obsidian-vault/README.md` and `.cursor/skills/obsidian-vault/SKILL.md`.

## First Commands For Future Agents

From the repo root on Windows:

```powershell
.\ops\raspberry-pi\scripts\quick-check.ps1
.\ops\raspberry-pi\scripts\tail-logs.ps1 -Service manon -Lines 120
```

If SSH host keys changed after a rebuild:

```powershell
ssh-keygen -R raspberrypi
ssh -o StrictHostKeyChecking=accept-new ben@raspberrypi hostname
```

## Current Limitations

- Obsidian vault GitHub backup is configured; live OneDrive sync on the Pi requires completing one-time device auth (`docs/obsidian-vault-backup.md`).
- n8n was rebuilt fresh after SD-card data loss. Old workflows/credentials were not recoverable unless an external n8n volume backup appears. Post-rebuild workflows and credentials are documented in `context.md`.
