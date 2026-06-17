# Working in Ben's Diary

Concise conventions and agent rules learned from vault analysis (June 2026). Detail: [`diary-structure.md`](diary-structure.md), scan data: [`analysis-taxonomy.md`](analysis-taxonomy.md).

## What this is

- **Vault:** OneDrive `Obsidian/hej` (~3,600 daily notes in `Diary/`)
- **Source of truth:** OneDrive (phone, Windows, web). **Always confirm sync is current before agents edit or delete vault files.**
- **Live sync:** OneDrive → phone, Pi. Edits from Cursor propagate immediately.
- **Git backup:** separate `--git-dir` on Windows (`%USERPROFILE%\.obsidian-vault-backup\vault.git`); Pi has its own mirror. Never put `.git` inside the vault folder. Pull/rebase git before push — Pi nightly backup writes to the same GitHub repo.

## Daily note identity

| Item | Convention |
| --- | --- |
| Filename | `YYYY-MM-DD, ddd.md` (e.g. `2026-06-15, Mon.md`) |
| Obsidian setting | `format: YYYY-MM-DD, ddd`, `folder: Diary` |
| Layout | 2016–2025 often under `Diary/YYYY/`; 2026+ often flat at `Diary/` |
| Template | `_Templates/Daily Note.md` |

**Automation must skip:** `(conflict …)` files, device-suffix duplicates, `0_Legend & Diary Conventions.md`, `Archive*` paths.

## "Headers" — two different things

1. **Scaffold (top of note):** YAML frontmatter + five interval nav lines + `[[_The Hotseat]]<<` marker. This is what nav tooling targets.
2. **Body headings:** freeform `#` / `##` in journal content (`## #workoutlog`, ChatGPT sections, etc.). Do not bulk-normalize without explicit approval.

Metadata field meanings and scales: `Diary/0_Legend & Diary Conventions.md`.

## Interval nav lines (the important part)

Five lines after frontmatter, each:

```text
<< [[YYYY-MM-DD, ddd]] | [[YYYY-MM-DD, ddd]] >> day
```

Offsets are **fixed day counts** from the note's own date (Templater template), not calendar months/quarters:

| Label | Prev | Next |
| --- | ---: | ---: |
| day | −1 | +1 |
| week | −7 | +7 |
| month | −30 | +30 |
| quarter | −90 | +90 |
| year | −365 | +365 |

Wikilink text must be `YYYY-MM-DD, ddd` where `ddd` matches the date's weekday (`Mon`, `Tue`, …).

**Legacy cosmetic drift (report only unless asked):** `>> (day)` vs `>> day`; extra frontmatter fields (`Wellbeing`, `Work`, `Finished`); `Home (Leiden)` vs Leipzig.

**Intentional quirks (do not "fix"):** trailing `<<` on Hotseat line; tag-in-heading body sections (`## #workoutlog`).

## What to fix vs leave alone

| Issue | Action |
| --- | --- |
| Wrong prev/next **date** on an **existing** nav line | Safe to fix (`fix-diary-nav.py`) |
| Missing nav line / wrong label order / unparseable line | Manual only — **do not add or reorder lines** |
| Link target file missing for a **future** date | OK — note will be created when that day comes |
| Link target missing for a **past** date | Gap in diary — flag, don't invent files |
| Frontmatter field drift | Report only |
| Body markdown heading issues | Report only |
| Sync-conflict duplicates | Manual only |

**`fix-diary-nav.py` only rewrites existing nav lines when dates are wrong.** It never adds nav lines, never touches frontmatter or body.

## Completed work (as of 2026-06-15)

- Nav prev/next dates fixed for notes **since 2024-01-01** (88 files); git commit `166ba15` on `obsidian-vault-backup`.
- Pre-2024 notes still have ~8k wrong-date hits; not batch-fixed (historical drift — confirm scope before touching).

## How agents should work

0. **Sync:** `wait-onedrive-vault.ps1` (Windows) or `obsidian-sync-onedrive.sh` (Pi). Use `vault-git-snapshot.ps1` for git (includes OneDrive wait + rebase).
1. **Read first:** `analyze-diary-headers.py --nav-only --since YYYY-MM-DD --summary-only`
2. **Dry-run fixes:** `fix-diary-nav.py --since …` (default is dry-run)
3. **Git snapshot before any write:** `vault-git-snapshot.ps1 -Message "pre: …"`
4. **Apply:** `fix-diary-nav.py --apply --push` (or snapshot manually after)
5. **When in doubt, hold back** — report findings, ask Ben before bulk or structural changes

Windows git auth: **HTTPS via `gh auth`** (not SSH). See [`README.md`](../README.md).

## Tools

| Script | Purpose |
| --- | --- |
| `analyze-diary-headers.py` | Read-only scan (`--nav-only` for link validation) |
| `fix-diary-nav.py` | Fix wrong dates on existing nav lines only |
| `vault-git-snapshot.ps1` | Commit vault state (`-Push` for GitHub) |
| `vault-git-bootstrap.ps1` | One-time Windows git mirror setup |
