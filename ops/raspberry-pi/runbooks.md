# Raspberry Pi Runbooks

Run these from Windows unless noted otherwise.

## Quick Status

```powershell
.\ops\raspberry-pi\scripts\quick-check.ps1
```

Manual equivalent:

```powershell
ssh ben@raspberrypi "date -Is; uptime; df -h /; free -h; docker ps -a; crontab -l"
```

## Logs

```powershell
.\ops\raspberry-pi\scripts\tail-logs.ps1 -Service manon -Lines 160
.\ops\raspberry-pi\scripts\tail-logs.ps1 -Service manon_db -Lines 100
.\ops\raspberry-pi\scripts\tail-logs.ps1 -Service n8n -Lines 100
.\ops\raspberry-pi\scripts\tail-logs.ps1 -Service health -Lines 100
.\ops\raspberry-pi\scripts\tail-logs.ps1 -Service backup -Lines 100
.\ops\raspberry-pi\scripts\tail-logs.ps1 -Service obsidian -Lines 100
.\ops\raspberry-pi\scripts\tail-logs.ps1 -Service onedrive -Lines 100
```

## Obsidian Vault Status

```powershell
ssh ben@raspberrypi "~/obsidian/scripts/obsidian-sync-status.sh"
```

## Run Obsidian Git Backup Now

```powershell
ssh ben@raspberrypi "~/obsidian/scripts/obsidian-nightly-backup.sh"
ssh ben@raspberrypi "tail -30 ~/obsidian/logs/obsidian-nightly-backup.log"
```

Sends a Manon Telegram ping every run — success, skip reason, or failure (via n8n **Obsidian Backup Notify** webhook).

## Test Obsidian Backup Telegram Notify

```powershell
ssh ben@raspberrypi '~/obsidian/scripts/obsidian-backup-notify.sh "📓 No Obsidian backup: no vault changes."'
```

## OneDrive Obsidian Sync

Check container:

```powershell
ssh ben@raspberrypi "docker ps -f name=onedrive; docker logs onedrive --tail 50"
```

One-time or re-authentication (interactive):

```powershell
ssh -t ben@raspberrypi "~/obsidian/scripts/obsidian-onedrive-auth.sh"
```

Start monitor after auth:

```powershell
ssh ben@raspberrypi "cd ~/obsidian && docker compose up -d"
```

## Restart Manon

```powershell
ssh ben@raspberrypi "cd ~/manon_deployer && docker compose up -d manon"
```

If the bot is stuck but still running:

```powershell
ssh ben@raspberrypi "docker restart manon"
```

## Restart The Manon Stack

```powershell
ssh ben@raspberrypi "cd ~/manon_deployer && docker compose up -d --remove-orphans"
```

## Restart n8n

```powershell
ssh ben@raspberrypi "cd ~/n8n && docker compose up -d"
ssh ben@raspberrypi "docker restart n8n-n8n-1"
```

## Run Health Check

```powershell
ssh ben@raspberrypi "~/manon_healthcheck.sh"
```

Check output:

```powershell
ssh ben@raspberrypi "tail -100 ~/healthchecks/manon_healthcheck.log"
```

## Run Backup Now

```powershell
ssh ben@raspberrypi "~/backup_services.sh"
```

List recent backups:

```powershell
ssh ben@raspberrypi "find ~/backups -maxdepth 2 -type f -printf '%TY-%Tm-%Td %TH:%TM %p %s bytes\n' | sort | tail -30"
```

## Restore Manon From A SQL Dump

Use care. This can overwrite data depending on the SQL dump contents.

For a plain SQL dump produced by `backup_services.sh`:

```powershell
scp .\path\to\manon_db.sql ben@raspberrypi:/tmp/manon_db.sql
ssh ben@raspberrypi "docker exec -i manon_db psql -v ON_ERROR_STOP=1 -U manon -d manon_db < /tmp/manon_db.sql"
```

For targeted restores, generate a SQL file with explicit `INSERT ... ON CONFLICT ...` statements and inspect it before running.

## Restore n8n Volume From A Tarball

Stop n8n first:

```powershell
ssh ben@raspberrypi "cd ~/n8n && docker compose down"
```

Then restore the tarball into the Docker volume:

```powershell
scp .\path\to\n8n_data.tar.gz ben@raspberrypi:/tmp/n8n_data.tar.gz
ssh ben@raspberrypi "docker run --rm -v n8n_n8n_data:/data -v /tmp:/backup alpine sh -c 'cd /data && rm -rf ./* && tar -xzf /backup/n8n_data.tar.gz'"
ssh ben@raspberrypi "cd ~/n8n && docker compose up -d"
```

The n8n `N8N_ENCRYPTION_KEY` in compose must match the key used when the backup was created.

## Update Manon Or Obi From GHCR

Full pattern: `docs/bot-ghcr-deploy.md`. Both bots auto-update hourly via cron (Manon :22, Obi :11).

```powershell
# Trigger update now
ssh ben@raspberrypi "cd ~/manon_deployer && bash update_container.sh"
ssh ben@raspberrypi "cd ~/obi_deployer && bash update_container.sh"

# Preview without restart
ssh ben@raspberrypi "cd ~/obi_deployer && bash update_container.sh --dry-run"

# Tail update logs
ssh ben@raspberrypi "tail -30 ~/manon_deployer/update_container.log"
ssh ben@raspberrypi "tail -30 ~/obi_deployer/update_container.log"
```

If GHCR is down, manual recovery only (not cron):

```powershell
ssh ben@raspberrypi "cd ~/obi_deployer && bash update_container.sh --build-fallback"
```

## Build Bot Locally On The Pi (GHCR fallback)

Use only when GHCR pull fails and you need `--build-fallback` or a manual build:

```powershell
ssh ben@raspberrypi "cd ~/manon_deployer && bash update_container.sh --build-fallback"
ssh ben@raspberrypi "cd ~/obi_deployer && bash update_container.sh --build-fallback"
```

Or build Manon image directly:

```powershell
ssh ben@raspberrypi "cd ~/Manon-PA_bot && git pull origin main && docker build -t ghcr.io/canopyflick/manon-pa-bot:latest ."
ssh ben@raspberrypi "cd ~/manon_deployer && docker compose up -d --no-build manon"
```

If the source directory does not exist, clone it first.

## Check GHCR Pull

```powershell
ssh ben@raspberrypi "/home/ben/scripts/ghcr-docker-login.sh"
ssh ben@raspberrypi "docker pull ghcr.io/canopyflick/manon-pa-bot:latest"
ssh ben@raspberrypi "docker pull ghcr.io/canopyflick/obi-pa-bot:latest"
```

Pi `gh` must include `read:packages` (`gh auth refresh -h github.com -s read:packages`). See `docs/bot-ghcr-deploy.md`.

## Check Public n8n

```powershell
Invoke-WebRequest -UseBasicParsing https://n8n.bentenberge.com/ | Select-Object -ExpandProperty StatusCode
ssh ben@raspberrypi "systemctl is-active cloudflared && curl -I --max-time 10 http://localhost:5678/"
```

## Common Diagnostics

```powershell
ssh ben@raspberrypi "systemctl is-active docker cron cloudflared"
ssh ben@raspberrypi "docker inspect manon --format 'Status={{.State.Status}} Exit={{.State.ExitCode}} RestartCount={{.RestartCount}} Policy={{.HostConfig.RestartPolicy.Name}}'"
ssh ben@raspberrypi "docker exec manon_db pg_isready -U manon -d manon_db"
ssh ben@raspberrypi "getent hosts api.telegram.org; curl -I --max-time 10 https://api.telegram.org"
```
