# Diary Header Analysis Taxonomy

Issue categories detected by `scripts/analyze-diary-headers.py`. Updated from initial vault scan on 2026-06-15.

## Category reference

| Category | Description | Auto-fix phase 2? |
| --- | --- | --- |
| `scaffold.missing_frontmatter` | No `---` YAML block at top | Maybe (old notes differ) |
| `scaffold.frontmatter_field_drift` | Legacy fields (`Wellbeing`, `Work`, `Finished`) or missing current template fields | Report only |
| `scaffold.interval_label_legacy` | `>> (day)` instead of `>> day` (and similar for week/month/quarter/year) | **Yes** — safe batch candidate |
| `scaffold.missing_interval_nav` | Fewer than 5 interval navigation lines | Maybe |
| `scaffold.hotseat_marker` | `[[_The Hotseat]]<<` trailing `<<` | Report only (likely intentional) |
| `markdown.heading_level_skip` | Heading level jump (e.g. `####` without parent `##`) | Report only |
| `markdown.h1_mid_document` | `#` heading after deeper headings in body | Report only |
| `markdown.template_artifact` | Trailing `****` on headers (e.g. `Overall Feelings:****`) | **Yes** — safe batch candidate |
| `markdown.empty_numbered_header` | `#### 1.` with no title text | Report only |
| `markdown.tag_in_heading` | `## #workoutlog` style (tag embedded in heading) | Report only |
| `meta.sync_conflict_sibling` | A `(conflict ...)` duplicate file exists | Manual resolution |
| `meta.year_subfolder` | Note stored under `Diary/YYYY/` subfolder | Info only |
| `meta.read_error` | File could not be read as UTF-8 | Manual |

## Initial scan results (all daily notes)

Scan: **3,626** daily note files (`--limit 0`), vault `C:\Users\Ben\OneDrive\Obsidian\hej\Diary`.

| Category | Count | Notes |
| --- | ---: | --- |
| `scaffold.interval_label_legacy` | 3,560 | Dominant issue; `(day)` → `day` normalization |
| `meta.year_subfolder` | 3,464 | Expected for 2016–2025 layout |
| `scaffold.frontmatter_field_drift` | 3,323 | Mix of legacy fields and missing current fields |
| `scaffold.hotseat_marker` | 452 | Mostly 2026 flat-layout notes; likely intentional |
| `scaffold.missing_frontmatter` | 314 | Mostly pre-2024 notes |
| `markdown.tag_in_heading` | 54 | Structured log sections |
| `markdown.template_artifact` | 39 | Workout log `****` leftovers |
| `scaffold.missing_interval_nav` | 27 | Incomplete nav blocks |
| `meta.sync_conflict_sibling` | 13 | One per conflict duplicate pair |
| `markdown.empty_numbered_header` | 9 | ChatGPT/Claude numbered sections |
| `markdown.h1_mid_document` | 1 | `2025-09-09, Tue.md` |

`markdown.heading_level_skip` — **0 hits** in full scan (may be rare or need tighter heuristics).

## Scan since 2024-01-01 (893 files)

More relevant subset for near-term fixes:

| Category | Count |
| --- | ---: |
| `scaffold.frontmatter_field_drift` | 903 |
| `scaffold.interval_label_legacy` | 850 |
| `meta.year_subfolder` | 731 |
| `scaffold.hotseat_marker` | 452 |
| `markdown.tag_in_heading` | 54 |
| `markdown.template_artifact` | 39 |
| `meta.sync_conflict_sibling` | 13 |
| `markdown.empty_numbered_header` | 9 |
| `scaffold.missing_interval_nav` | 4 |
| `markdown.h1_mid_document` | 1 |
| `scaffold.missing_frontmatter` | 1 |

2026 flat-layout notes (no year subfolder) mostly use current template with `>> day` labels. Legacy `(day)` labels persist on notes through early May 2026.

## Phase 2 fix priorities (pending Ben confirmation)

1. **`markdown.template_artifact`** (39 files) — strip trailing `****`; low risk
2. **`scaffold.interval_label_legacy`** (850 since 2024) — `(day)` → `day` etc.; medium volume, likely safe
3. **Sync conflicts** (13 pairs) — manual review; never auto-fix
4. **`scaffold.missing_interval_nav`** (4 since 2024) — case-by-case
5. **Frontmatter drift** — report only until template migration strategy is agreed

## Re-run analysis

```powershell
python ops\raspberry-pi\obsidian-vault\scripts\analyze-diary-headers.py --summary-only
python ops\raspberry-pi\obsidian-vault\scripts\analyze-diary-headers.py --since 2024-01-01 --limit 0
python ops\raspberry-pi\obsidian-vault\scripts\analyze-diary-headers.py --limit 0
```

Detailed JSON/MD reports: `reports/` (gitignored). Latest full scan: `reports/diary-header-analysis-20260615-203516.json`.
