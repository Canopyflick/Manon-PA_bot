# Private Raspberry Pi Notes Template

Copy this file to `private-notes.md` for local-only details.

Do not commit `private-notes.md`.

## SSH

- Host:
- User:
- Alternate IPs:
- Notes:

## Secrets Locations

- Password manager item:
- Telegram bot token (Manon):
- Telegram bot token (Nathan @Nathan_PA_bot):
- OpenAI keys:
- OpenRouter API key:
- Cloudflare tunnel credentials:
- GHCR/GitHub token:
- n8n encryption key (on Pi compose — do not rotate casually):
- n8n API key (Cursor local `.env` — `ops/raspberry-pi/.env`):

## Off-Pi Backups

- Obsidian vault GitHub backup: `Canopyflick/obsidian-vault-backup` (private)
- Pi deploy key path: `~/.ssh/obsidian_vault_backup`
- OneDrive account: `ben_ten_berge@hotmail.com`
- OneDrive remote path: `Obsidian/hej`
- Restore test date:

## Project Inventory

Use this section for future Pi projects beyond Manon/n8n.

| Project | Path | Containers/Services | Public URL | Backup Notes |
| --- | --- | --- | --- | --- |
| Manon | `/home/ben/manon_deployer` | `manon`, `manon_db` | Telegram polling | SQL dump |
| n8n | `/home/ben/n8n` | `n8n-n8n-1` | `n8n.bentenberge.com` | Docker volume tar |
| Obsidian vault | `/home/ben/obsidian` | `onedrive` Docker | — | GitHub `obsidian-vault-backup` nightly |
| Nathan (n8n bot) | n8n workflow | Telegram Trigger | Telegram @Nathan_PA_bot | — |
