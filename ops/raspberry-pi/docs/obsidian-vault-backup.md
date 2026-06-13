# Obsidian Vault Sync and GitHub Backup

This document describes how the Raspberry Pi maintains a local copy of Ben's Obsidian vault from OneDrive and backs it up nightly to a private GitHub repository.

## Architecture

```text
Android Obsidian
  -> OneSync
  -> OneDrive (Obsidian/hej)
  -> abraunegg OneDrive client on Pi
  -> /home/ben/obsidian/vault
  -> nightly git backup (separate git-dir)
  -> Canopyflick/obsidian-vault-backup (private)
```

OneSync is Android-only. The Pi syncs the OneDrive folder that OneSync writes to, not OneSync itself.

## Paths

| Variable | Path |
| --- | --- |
| `OBSIDIAN_BASE_DIR` | `/home/ben/obsidian` |
| `OBSIDIAN_VAULT_DIR` | `/home/ben/obsidian/vault` (symlink) |
| Synced vault content | `/home/ben/obsidian/onedrive/Obsidian/hej` |
| `OBSIDIAN_GIT_DIR` | `/home/ben/obsidian/backup-git/vault.git` |
| `OBSIDIAN_LOG_DIR` | `/home/ben/obsidian/logs` |
| Backup script | `/home/ben/obsidian/scripts/obsidian-nightly-backup.sh` |
| OneDrive config | `~/.config/onedrive/config` |
| OneDrive sync_list | `~/.config/onedrive/sync_list` |

## OneDrive

- Client: [abraunegg/onedrive](https://github.com/abraunegg/onedrive) via Docker image `driveone/onedrive:debian`
- Container name: `onedrive`
- Compose file: `/home/ben/obsidian/docker-compose.yml`
- Remote folder: `Obsidian/hej` (OneDrive path; UI shows as `My files/Obsidian/hej`)
- Microsoft account: personal `ben_ten_berge@hotmail.com`
- Config dir: `/home/ben/obsidian/onedrive-conf/` (bind-mounted to `/onedrive/conf`)
- Service: `docker ps -f name=onedrive` or optional user systemd unit `systemctl --user status onedrive`
- Logs: `docker logs onedrive` and `/home/ben/obsidian/logs/onedrive*.log`

### One-time browser authentication

Personal Microsoft accounts (`@hotmail.com`, `@outlook.com`, etc.) **cannot** use device-code login (`login.microsoft.com/device`). Microsoft blocks that OAuth flow for third-party apps on personal accounts; approving the Authenticator number match immediately shows "The code you entered has expired" even when you tap promptly. Use interactive browser OAuth instead.

```bash
ssh -t ben@raspberrypi /home/ben/obsidian/scripts/obsidian-onedrive-auth.sh
```

The script prints an authorize URL. Open it, sign in as `ben_ten_berge@hotmail.com`, complete MFA, then copy the full redirect URL from the blank page (`https://login.microsoftonline.com/common/oauth2/nativeclient?code=...`) and paste it back at the prompt.

Then start monitor mode:

```bash
ssh ben@raspberrypi "cd ~/obsidian && docker compose up -d"
```

Optional user systemd (starts compose at boot):

```bash
install -m 644 ~/path/to/onedrive.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now onedrive
sudo loginctl enable-linger ben
```

Obsidian-friendly client settings:

- `force_session_upload = "true"`
- `delay_inotify_processing = "true"`
- `inotify_delay = "10"`

## GitHub backup

- Repo: `git@github.com:Canopyflick/obsidian-vault-backup.git` (private)
- Git metadata is stored outside the vault using `--git-dir` / `--work-tree`
- No `.git` directory inside the synced vault folder
- Auth: repo-scoped SSH deploy key at `~/.ssh/obsidian_vault_backup`
- Schedule: cron at 03:30 Europe/Berlin

## Manual commands

```bash
# Sync status summary
/home/ben/obsidian/scripts/obsidian-sync-status.sh

# OneDrive service
docker ps -f name=onedrive
docker logs onedrive --tail 100

# Manual backup
/home/ben/obsidian/scripts/obsidian-nightly-backup.sh
tail -50 /home/ben/obsidian/logs/obsidian-nightly-backup.log

# Vault spot-check
find /home/ben/obsidian/vault -name '*.md' | head
ls -la /home/ben/obsidian/vault/.obsidian 2>/dev/null || true

# Git status (separate git-dir)
git --git-dir=/home/ben/obsidian/backup-git/vault.git \
    --work-tree=/home/ben/obsidian/vault status --short
```

## Recovery

### Restore vault files from GitHub

```bash
git clone git@github.com:Canopyflick/obsidian-vault-backup.git /tmp/obsidian-restore
rsync -a /tmp/obsidian-restore/ /home/ben/obsidian/vault/
```

This restores backup content only. OneDrive remains the live sync layer for day-to-day use.

### Re-authenticate OneDrive

If sync stops due to token expiry:

```bash
docker stop onedrive
/home/ben/obsidian/scripts/obsidian-onedrive-auth.sh
cd /home/ben/obsidian && docker compose up -d
```

## Failure modes

| Symptom | Likely cause | Action |
| --- | --- | --- |
| Vault stale on Pi | OneDrive container down or auth expired | `docker ps -f name=onedrive`; re-run device auth |
| Backup skipped with deletion error | Incomplete sync or real mass delete | Inspect OneDrive logs and vault before overriding guard |
| Push failed | Deploy key or GitHub access issue | Test `GIT_SSH_COMMAND='ssh -i ~/.ssh/obsidian_vault_backup' git push` |
| `.git` in vault | Misconfigured git init | Remove immediately; never `git init` inside vault |

## Future Telegram bot integration

| Setting | Value |
| --- | --- |
| `OBSIDIAN_VAULT_DIR` | `/home/ben/obsidian/vault` |
| `OBSIDIAN_BACKUP_STATUS_LOG` | `/home/ben/obsidian/logs/obsidian-nightly-backup.log` |
| `OBSIDIAN_READ_ONLY_MODE` | `true` (initial version) |
| Future index dir | `/home/ben/obsidian/index` |

Design assumptions:

- Bot reads the local vault folder directly.
- Bot does not call OneDrive or Obsidian desktop APIs.
- Sync freshness is eventual: Android -> OneSync -> OneDrive -> Pi (minutes, not seconds).
- GitHub is backup/version history, not primary sync.
- Initial bot version is read-only.
- Later writes should target safe files only (`Inbox.md`, capture note, daily notes).
- Bot index/state should live outside the vault.
- Manon's existing `/diary` command generates text only and does not access this vault path.

## Deploy from repo

Copy scripts and systemd unit from this repo to the Pi:

```bash
mkdir -p ~/obsidian/scripts
install -m 755 obsidian-nightly-backup.sh ~/obsidian/scripts/
install -m 755 obsidian-sync-status.sh ~/obsidian/scripts/
install -m 755 obsidian-onedrive-auth.sh ~/obsidian/scripts/
install -m 644 docker-compose.yml ~/obsidian/
install -m 644 onedrive-config ~/obsidian/onedrive-conf/config
install -m 644 sync_list ~/obsidian/onedrive-conf/sync_list
install -m 644 onedrive.service ~/.config/systemd/user/
systemctl --user daemon-reload
```
