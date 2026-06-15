# Diary Daily Note Structure

Reference for the Obsidian daily note scaffold in `Diary/`. Used by `analyze-diary-headers.py` and future fix scripts.

## Obsidian config

From `.obsidian/daily-notes.json`:

```json
{
  "format": "YYYY-MM-DD, ddd",
  "folder": "Diary",
  "template": "_Templates/Daily Note"
}
```

## File naming

| Era | Pattern | Example path |
| --- | --- | --- |
| Current | `YYYY-MM-DD, ddd.md` | `Diary/2026-06-15, Mon.md` |
| 2016–2025 | Same name, often in year subfolder | `Diary/2025/2025-12-18, Thu.md` |
| Historical archive | Full weekday names possible | `Archive (2016-2022...)/` |

Daily note regex: `^\d{4}-\d{2}-\d{2}, \w{3}\.md$`

**Skip for automation:** sync-conflict files `(conflict ...)`, device-suffix duplicates (`-ZenDesktop19`), `0_Legend & Diary Conventions.md`, `Archive*` paths.

## Canonical scaffold (current template)

Source: `_Templates/Daily Note.md`

### 1. YAML frontmatter

```yaml
---
Heading:
Comfort:
Home (Leipzig): true
Walk >30mins.: false
Whereabouts:
Sports:
Drugs:
E:
Purchases:
Meditate:
Interessant:
---
```

### 2. Interval navigation (5 lines)

```
<< [[YYYY-MM-DD, ddd]] | [[YYYY-MM-DD, ddd]] >> day
<< [[YYYY-MM-DD, ddd]] | [[YYYY-MM-DD, ddd]] >> week
<< [[YYYY-MM-DD, ddd]] | [[YYYY-MM-DD, ddd]] >> month
<< [[YYYY-MM-DD, ddd]] | [[YYYY-MM-DD, ddd]] >> quarter
<< [[YYYY-MM-DD, ddd]] | [[YYYY-MM-DD, ddd]] >> year
```

Current template uses bare labels (`day`, `week`, …). Older notes may use parentheses: `>> (day)`.

### 3. Hotseat marker + separator

```
[[_The Hotseat]]<<

---

- [ ] 
```

The trailing `<<` after the wikilink is a consistent marker (not valid wikilink syntax alone); treat as intentional unless Ben says otherwise.

## Historical drift (do not normalize blindly)

| Field / pattern | Era | Notes |
| --- | --- | --- |
| `Wellbeing`, `Work`, `Finished` | 2016–2025 | Removed from current template |
| `Home (Leiden)` | pre-Leipzig | Replaced by `Home (Leipzig)` |
| `>> (day)` etc. | pre-2026 common | Legacy interval labels |
| Year subfolders | 2016–2025 | 2026+ notes may be flat at `Diary/` root |

Metadata scales and hash-tag conventions: `Diary/0_Legend & Diary Conventions.md`.

## Body content headers

Structured sections sometimes use markdown headings:

- `## #workoutlog` → `### Exercises:` → `### Overall Feelings:`
- `## #contentlog` → `### takeaways / quote` etc.
- `## chat met ChatGPT...` → `### chat-opener` → `### antwoord`

These are **body content**, separate from the scaffold frontmatter/nav block. Heading hierarchy issues in body text are report-only unless Ben confirms fix rules.

Known body patterns to watch:

- Template leftovers: `Overall Feelings:****`
- Empty numbered headers: `#### 1.`
- Tag-in-heading: `## #workoutlog`
- H1 mid-document after deeper headings: `# rest van diary entry`

## Telegram bot drift

`features/obsidian/diary_header.py` still emits `Wellbeing`, `Work`, and `Finished` in the Telegram `/diary` header. That output does not match the current Obsidian Daily Note template. Documented here for awareness; not changed by obsidian-vault tooling in phase 1.

## Related paths

| Path | Role |
| --- | --- |
| `C:\Users\Ben\OneDrive\Obsidian\hej\Diary\` | Windows daily notes |
| `/home/ben/obsidian/vault/Diary/` | Pi synced copy |
| `ops/raspberry-pi/obsidian-vault/scripts/analyze-diary-headers.py` | Read-only scanner |
