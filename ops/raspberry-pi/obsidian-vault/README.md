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

Requires GitHub SSH access to `Canopyflick/obsidian-vault-backup`. Your personal GitHub SSH key (`~/.ssh/id_ed25519` or similar, already on your GitHub account) is sufficient — you do not need the Pi deploy key.

## Git snapshots (before/after vault edits)

```powershell
# Before any mutation
.\ops\raspberry-pi\obsidian-vault\scripts\vault-git-snapshot.ps1 -Message "pre: diary header fixes"

# After changes (optional -Push for immediate remote backup)
.\ops\raspberry-pi\obsidian-vault\scripts\vault-git-snapshot.ps1 -Message "post: diary header fixes" -Push
```

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
4. Phase 1 is read-only analysis only; no auto-fix without review.

## Docs

- [`docs/diary-structure.md`](docs/diary-structure.md) — canonical daily note scaffold
- [`docs/analysis-taxonomy.md`](docs/analysis-taxonomy.md) — issue categories from analyzer runs

Cursor skill: `.cursor/skills/obsidian-vault/SKILL.md`
