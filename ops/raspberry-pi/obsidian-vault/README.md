# Obsidian Vault Management

Windows-side tooling for Ben's Obsidian vault (`Obsidian/hej` on OneDrive). Daily notes live in `Diary/`.

Pi sync and nightly GitHub backup are documented separately in [`docs/obsidian-vault-backup.md`](../docs/obsidian-vault-backup.md). This directory covers **local analysis and safe editing from Cursor**.

## Paths

| Environment | Vault | Git metadata |
| --- | --- | --- |
| Windows (OneDrive) | `C:\Users\Ben\OneDrive\Obsidian\hej` | `%USERPROFILE%\.obsidian-vault-backup\vault.git` |
| Raspberry Pi | `/home/ben/obsidian/vault` | `/home/ben/obsidian/backup-git/vault.git` |

Both use `--git-dir` / `--work-tree` — **never** create `.git` inside the OneDrive vault folder.

## Setup (one-time)

```powershell
copy ops\raspberry-pi\obsidian-vault\config.example.env ops\raspberry-pi\obsidian-vault\config.env
.\ops\raspberry-pi\obsidian-vault\scripts\vault-git-bootstrap.ps1
```

Requires GitHub access to `Canopyflick/obsidian-vault-backup`. On Windows, **HTTPS via `gh auth login`** is recommended (uses your token in the OS keyring — no SSH key needed). Pi uses SSH deploy key separately.

```powershell
gh auth status   # should show Canopyflick, protocol https
```

SSH alternative: add your public key to GitHub and set `GIT_REMOTE=git@github.com:Canopyflick/obsidian-vault-backup.git` in `config.env`.

## Safe edit workflow (mandatory)

**OneDrive is the source of truth.** Before any vault mutation from Cursor:

```powershell
.\ops\raspberry-pi\obsidian-vault\scripts\wait-onedrive-vault.ps1
```

`vault-git-snapshot.ps1` runs this automatically. It also `git fetch` + `git rebase` onto `origin/main` before commit/push so Windows edits do not fight the Pi nightly backup.

## Git snapshots (before/after vault edits)

```powershell
# Before any mutation (OneDrive wait + git rebase included)
.\ops\raspberry-pi\obsidian-vault\scripts\vault-git-snapshot.ps1 -Message "pre: diary header fixes"

# After changes
.\ops\raspberry-pi\obsidian-vault\scripts\vault-git-snapshot.ps1 -Message "post: diary header fixes" -Push
```

Use `-SkipOneDriveSync` or `-SkipPull` only for emergencies.

Pi nightly cron still runs at 03:30 Europe/Berlin; local snapshots are for immediate rollback when editing from Cursor.

## Diary header analysis (read-only)

```powershell
# Interval nav link validation (wrong prev/next day/week/month/quarter/year)
python ops\raspberry-pi\obsidian-vault\scripts\analyze-diary-headers.py --nav-only --limit 0 --summary-only

# Quick summary (default: 50 most recent daily notes)
python ops\raspberry-pi\obsidian-vault\scripts\analyze-diary-headers.py --summary-only

# Full scan since a date
python ops\raspberry-pi\obsidian-vault\scripts\analyze-diary-headers.py --since 2024-01-01 --limit 0
```

Reports land in `reports/` (gitignored). Issue taxonomy: [`docs/analysis-taxonomy.md`](docs/analysis-taxonomy.md).

## Fix interval nav dates

```powershell
# Dry-run (default)
python ops\raspberry-pi\obsidian-vault\scripts\fix-diary-nav.py --since 2024-01-01

# Apply (git snapshot pre/post recommended)
python ops\raspberry-pi\obsidian-vault\scripts\fix-diary-nav.py --since 2024-01-01 --apply --push
```

Use `--file "Diary/2026-05-07, Thu.md"` to test a single note. `--skip-git` only if vault git mirror is not bootstrapped yet.

## Safety rules

1. Always git-snapshot **before and after** vault mutations.
2. Skip sync-conflict files (`(conflict ...)`) — resolve manually.
3. Old notes (2016–2025) have intentional format drift — do not normalize blindly.
4. Nav fixes: existing lines only; never add missing nav lines.

## Docs

- [`docs/working-in-the-diary.md`](docs/working-in-the-diary.md) — **start here** — conventions and agent rules
- [`docs/diary-structure.md`](docs/diary-structure.md) — canonical daily note scaffold
- [`docs/analysis-taxonomy.md`](docs/analysis-taxonomy.md) — issue categories from analyzer runs

Cursor skill: `.cursor/skills/obsidian-vault/SKILL.md`
