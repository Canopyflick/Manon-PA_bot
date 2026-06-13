# What Future Agents Need

This is the short list of things that would make future Raspberry Pi help faster and safer.

## Highest Value

1. Off-Pi backups configured and documented.
   - Current backups are local at `/home/ben/backups`.
   - Pick OneDrive, NAS, or another target.
   - Add the remote name, sync command, and restore test date to `private-notes.md`.

2. GHCR package access fixed.
   - Current workaround is a local image build on the Pi.
   - Future agents need either working `docker pull ghcr.io/canopyflick/manon-pa-bot:latest` or clear instructions for the local build path.

3. Private notes file.
   - Copy `private-notes.example.md` to `private-notes.md`.
   - Fill in where secrets live, not the secrets themselves.
   - Add any non-obvious SSH/IP details and backup destination details.

4. A project inventory as the Pi grows.
   - For each new project: path, repo, compose file, containers, public URL, volumes, backup method, recovery command.

5. n8n workflow inventory kept current.
   - Document new workflows in `context.md` (name, trigger type, credentials used).
   - Note which bots use Telegram Trigger vs Chat Trigger.
   - OAuth credentials (Google Calendar) need a one-time UI connect — flag when a workflow depends on them.

## Helpful But Optional

- A restore drill log: date, backup file, command used, result.
- A short “known good state” snapshot after major changes.
- Notes on which services are okay to restart blindly and which are not.
- A decision on whether n8n should be behind Cloudflare Access or basic auth.
- Pin-data test fixtures for key n8n workflows (stored in n8n, not the repo).

## n8n automation quick reference

- **Build workflows:** n8n MCP (`user-n8n-mcp`) — always read SDK reference before writing workflow code.
- **Create token credentials:** REST API with `N8N_API_KEY` from `ops/raspberry-pi/.env`.
- **OAuth credentials:** n8n UI only.
- **Telegram bots:** Telegram Trigger workflow, not Chat Hub Personal Agent.

## Avoid

- Do not commit live `.env` files, tokens, private keys, Cloudflare credential JSON, SQL dumps, or backup archives.
- Do not rely on SD-card-only backups for stateful Docker volumes.
