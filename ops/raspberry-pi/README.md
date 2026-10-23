# Raspberry Pi Ops Workspace

This directory is the starting point for future work on Ben's Raspberry Pi services.

It is intentionally secret-free. Keep live tokens, passwords, private keys, Cloudflare tunnel credentials, and `.env` values on the Pi or in a password manager, not in this repo.

## Current Pi

- SSH user: `ben`
- From this PC, off the home network: public IP in `private-notes.md` (ssh config host `raspberrypi`). As of 2026-10-23 that address is `188.97.158.15`.
- Home LAN only: `192.168.178.127` (`raspberrypi-lan`). The name `raspberrypi` does not resolve here.
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

## Reaching the Pi

`192.168.178.127` and the hostname `raspberrypi` only work on the home Fritz network. From anywhere else, SSH to the public IP recorded in gitignored `private-notes.md`.

That address changes when the ISP lease changes. An old address can still answer ping after port 22 has moved. `188.97.154.147` is one of those: it pings, and SSH times out. The working address on 2026-10-23 is `188.97.158.15`.

Before trusting a new address, the host key must be `SHA256:cITJ7LDb7/6w8RNugVisFafcRUwLaj6skqCC/1gYYyo` (same key as the LAN address). `goals.bentenberge.com` and `n8n.bentenberge.com` are Cloudflare proxies, so they are not the Pi's IP.

This Windows user already has `~\.ssh\id_ed25519` in `ben`'s `authorized_keys`. Point ssh config host `raspberrypi` at the current public IP, then:

```powershell
ssh -o BatchMode=yes raspberrypi "hostname; date -Is"
```

The login password, the key path, and the current IP live in `private-notes.md`. Copy `private-notes.example.md` to that file on a new machine. Do not commit it.

## First Commands For Future Agents

From the repo root on Windows, after `ssh raspberrypi` reaches the public IP:

```powershell
.\ops\raspberry-pi\scripts\quick-check.ps1
.\ops\raspberry-pi\scripts\tail-logs.ps1 -Service manon -Lines 120
```

If the host key changed after a rebuild, remove the old line and accept the new key only when you recognize the fingerprint above:

```powershell
ssh-keygen -R 188.97.158.15
ssh -o StrictHostKeyChecking=accept-new ben@188.97.158.15 hostname
```

## Current Limitations

- Obsidian vault GitHub backup is configured; live OneDrive sync on the Pi requires completing one-time device auth (`docs/obsidian-vault-backup.md`).
- n8n was rebuilt fresh after SD-card data loss. Old workflows/credentials were not recoverable unless an external n8n volume backup appears. Post-rebuild workflows and credentials are documented in `context.md`.
