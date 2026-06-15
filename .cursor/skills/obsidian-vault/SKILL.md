---
name: obsidian-vault
description: >-
  Manage Ben's Obsidian vault (Diary daily notes, header fixes, git snapshots).
  Use when editing vault files, analyzing/fixing Diary headers, or running
  obsidian-vault scripts under ops/raspberry-pi/obsidian-vault/.
---

# Obsidian Vault

Vault: OneDrive `Obsidian/hej`. Daily notes: `Diary/`. Runbook in `ops/raspberry-pi/obsidian-vault/README.md`. Pi backup in `ops/raspberry-pi/docs/obsidian-vault-backup.md`. Path-scoped rule in `.cursor/rules/obsidian-vault.mdc`.

## Git safety (mandatory)

Before **any** vault mutation:

1. `.\ops\raspberry-pi\obsidian-vault\scripts\vault-git-snapshot.ps1 -Message "pre: <what>"`

After changes:

2. `.\ops\raspberry-pi\obsidian-vault\scripts\vault-git-snapshot.ps1 -Message "post: <what>" -Push`

One-time setup: copy `config.example.env` → `config.env`, then run `vault-git-bootstrap.ps1`.

Never create `.git` inside the OneDrive vault folder. Pi nightly backup (03:30 Europe/Berlin) is supplemental — do not rely on it alone when editing from Cursor.

## Diary work pipeline

1. `python ops/raspberry-pi/obsidian-vault/scripts/analyze-diary-headers.py --summary-only` — understand scope
2. Review `reports/` output; confirm fix categories with Ben when ambiguous
3. Git snapshot (pre)
4. Fix script with `--dry-run` first; `--apply` only after review (phase 2)
5. Git snapshot (post)

Scaffold reference: `ops/raspberry-pi/obsidian-vault/docs/diary-structure.md`. Issue taxonomy: `ops/raspberry-pi/obsidian-vault/docs/analysis-taxonomy.md`.

## Gotchas

- Vault is live OneDrive — changes sync to phone and Pi
- Skip sync-conflict files (`(conflict ...)`); resolve manually
- Old notes (2016–2025) have intentional format drift — don't normalize blindly
- "Headers" means YAML frontmatter + interval nav scaffold **and** markdown `#` headings in body; treat differently
- When in doubt, hold back — report only, ask Ben before bulk fixes
