# Manon & Obi — GHCR deployment on the Pi

Both Telegram bots use the same deployment pattern: GitHub push → GitHub Actions builds `linux/arm64` → GHCR `:latest` → Pi scheduled updater pulls → redeploy only when the image digest changes.

## Architecture

```text
GitHub push (main / master)
  -> GitHub Actions docker-build.yml
  -> ghcr.io/canopyflick/{manon,obi}-pa-bot:latest
  -> Pi cron: update_container.sh
       -> ghcr-docker-login.sh
       -> ghcr-update-container.sh
            -> docker pull
            -> compare running container digest vs pulled image
            -> docker compose up -d --no-build  (only if changed)
```

| Bot | Repo branch | GHCR image | Deploy dir | Cron (Europe/Berlin) |
| --- | --- | --- | --- | --- |
| Manon | `main` | `ghcr.io/canopyflick/manon-pa-bot:latest` | `/home/ben/manon_deployer` | minute **22** each hour |
| Obi | `master` | `ghcr.io/canopyflick/obi-pa-bot:latest` | `/home/ben/obi_deployer` | minute **11** each hour |

Cron uses non-round minutes so jobs do not all fire at `:00`.

## Pi scripts

| Path | Role |
| --- | --- |
| `/home/ben/scripts/ghcr-docker-login.sh` | `docker login ghcr.io` via `gh auth token` (requires `read:packages`) |
| `/home/ben/scripts/ghcr-update-container.sh` | Shared pull, digest compare, conditional redeploy |
| `/home/ben/manon_deployer/update_container.sh` | Thin Manon wrapper (sets env, calls shared helper) |
| `/home/ben/obi_deployer/update_container.sh` | Thin Obi wrapper (sets env + `LOCK_FILE`, calls shared helper) |

Canonical source for the shared scripts: `ops/raspberry-pi/scripts/` in this repo. Wrappers live in each bot repo under `deployment/update_container.sh`.

### Normal update flow (cron)

1. Log in to GHCR (`ghcr-docker-login.sh`) — **exit 1** on failure
2. `docker pull` the `:latest` image — **exit 1** on failure
3. Compare full `sha256:` digests (running container vs pulled image)
4. If unchanged → log `already up to date`, `redeploy=no`, **no restart**
5. If changed → `docker compose up -d --no-build <service>` — **no** `compose down`, **no** `docker rm -f`, **no** local build

Structured log example:

```text
[2026-06-17T16:43:44+02:00] image=ghcr.io/canopyflick/obi-pa-bot:latest container=obi old=sha256:d410… new=sha256:d410… redeploy=no
```

### Obi vault-lock safety

Before redeploying Obi when the digest changed, the helper checks `/home/ben/obi/state/vault.lock`. If another process holds the lock (nightly backup, sync, or confirmed write), the update is **skipped**:

```text
Obi vault operation in progress; skipping update.
```

Cron logs `redeploy=no reason=vault-lock` and exits 0 (defer until the next hour).

### Flags (manual use)

| Flag | Behavior |
| --- | --- |
| `--dry-run` | Login + pull + compare + log whether redeploy would happen; never restarts |
| `--build-fallback` | If GHCR login/pull fails: `git pull` in repo clone + `docker compose build` + `up -d` |

**Scheduled cron never uses `--build-fallback`.** GHCR failure during cron logs the error and exits nonzero.

```bash
# Preview without restart
cd /home/ben/obi_deployer && ./update_container.sh --dry-run

# Manual recovery when GHCR is down
cd /home/ben/obi_deployer && ./update_container.sh --build-fallback
```

## GHCR authentication on the Pi

Private GHCR images require the Pi `gh` CLI token to include **`read:packages`**.

One-time (or when pulls return 403):

```bash
ssh ben@raspberrypi
gh auth refresh -h github.com -s read:packages
# complete device login in browser
/home/ben/scripts/ghcr-docker-login.sh
docker pull ghcr.io/canopyflick/manon-pa-bot:latest
```

Verify scopes:

```bash
gh auth status   # should list read:packages
```

## GitHub Actions (build side)

| Bot | Workflow | Registry login |
| --- | --- | --- |
| Manon | `Manon-PA_bot/.github/workflows/docker-build.yml` | `secrets.GHCR_PAT` |
| Obi | `Obi-PA_bot/.github/workflows/docker-build.yml` | `secrets.GITHUB_TOKEN` |

Both push `linux/arm64` to `ghcr.io/canopyflick/<bot>-pa-bot:latest` on push to the default branch.

## Crontab (current)

```cron
17 3 * * * /home/ben/backup_services.sh >> /home/ben/backups/backup.log 2>&1
05 3 * * * /home/ben/manon_healthcheck.sh >> /home/ben/healthchecks/cron.log 2>&1
0 4 * * * /home/ben/manon_deployer/weekly_restart.sh >> /home/ben/manon_deployer/weekly_restart.log 2>&1
30 3 * * * /home/ben/obsidian/scripts/obsidian-nightly-backup.sh
22 * * * * cd /home/ben/manon_deployer && ./update_container.sh >> /home/ben/manon_deployer/update_container.log 2>&1
11 * * * * cd /home/ben/obi_deployer && ./update_container.sh >> /home/ben/obi_deployer/update_container.log 2>&1
```

`weekly_restart.sh` and `manon_healthcheck.sh` are separate from GHCR updates (restart/recovery, not image pull).

## Manual commands

```bash
# Trigger update now
cd /home/ben/manon_deployer && ./update_container.sh
cd /home/ben/obi_deployer && ./update_container.sh

# Tail update logs
tail -30 /home/ben/manon_deployer/update_container.log
tail -30 /home/ben/obi_deployer/update_container.log

# Confirm running image digests
docker inspect -f '{{.Name}} {{.Image}} {{.State.StartedAt}}' manon obi
```

From Windows:

```powershell
ssh ben@raspberrypi "cd ~/manon_deployer && ./update_container.sh"
ssh ben@raspberrypi "cd ~/obi_deployer && ./update_container.sh --dry-run"
```

## Deploy script changes to the Pi

After editing scripts in git on Windows:

```powershell
scp .\ops\raspberry-pi\scripts\ghcr-docker-login.sh ben@raspberrypi:/home/ben/scripts/
scp .\ops\raspberry-pi\scripts\ghcr-update-container.sh ben@raspberrypi:/home/ben/scripts/
scp .\deployment\update_container.sh ben@raspberrypi:/home/ben/manon_deployer/
# Obi wrapper from Obi-PA_bot repo:
scp <path-to-Obi-PA_bot>\deployment\update_container.sh ben@raspberrypi:/home/ben/obi_deployer/

ssh ben@raspberrypi "chmod +x /home/ben/scripts/*.sh /home/ben/manon_deployer/update_container.sh /home/ben/obi_deployer/update_container.sh"
```

Or `git pull` in `/home/ben/Obi-PA_bot` on the Pi (requires `gh auth` with `repo` scope) and copy wrappers from there.

## First-time bot deploy

**Manon:** see `Manon-PA_bot/deployment/README.md` — copy `docker-compose.yml`, `.env`, and `update_container.sh` to `~/manon_deployer`, then `./update_container.sh`.

**Obi:** see `docs/obi-vault-bot.md` — copy from `Obi-PA_bot/deployment/`, configure `.env`, run `./update_container.sh`.

## Related docs

- `context.md` — service inventory, cron, known failure modes
- `runbooks.md` — diagnostics and recovery commands
- `docs/obi-vault-bot.md` — Obi-specific vault, lock, and preflight details
