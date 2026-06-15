# Diary Header Analysis Taxonomy

Issue categories detected by `scripts/analyze-diary-headers.py`. Updated 2026-06-15.

## Interval navigation link validation (primary)

The Daily Note template generates five nav lines with fixed day offsets (Templater `tp.date.now`):

| Line | Label | Prev offset | Next offset |
| --- | --- | ---: | ---: |
| 1 | day | −1 | +1 |
| 2 | week | −7 | +7 |
| 3 | month | −30 | +30 |
| 4 | quarter | −90 | +90 |
| 5 | year | −365 | +365 |

Each link must be `[[YYYY-MM-DD, ddd]]` where `ddd` matches the date's weekday (`Mon`, `Tue`, …).

Run nav-only scan:

```powershell
python ops\raspberry-pi\obsidian-vault\scripts\analyze-diary-headers.py --nav-only --limit 0 --summary-only
python ops\raspberry-pi\obsidian-vault\scripts\analyze-diary-headers.py --nav-only --since 2024-01-01 --limit 0 --verbose
```

### Nav issue categories

| Category | Description | Auto-fix? |
| --- | --- | --- |
| `nav.wrong_prev_date` | Prev wikilink date ≠ note date + offset | **Yes** |
| `nav.wrong_next_date` | Next wikilink date ≠ note date + offset | **Yes** |
| `nav.wrong_weekday_label` | Date correct but weekday label wrong | **Yes** |
| `nav.missing_target_file` | Correct date (≤ today) but no matching daily note file | Maybe (gap in diary) |
| `nav.unparseable_link` | Link not in `YYYY-MM-DD, ddd` form | Manual |
| `nav.unparseable_line` | Whole nav line malformed | Manual |
| `nav.missing_interval_label` | Nav line missing `day`/`week`/… label | Manual |
| `nav.wrong_interval_order` | Labels out of order (e.g. `week` on line 1) | Maybe |
| `nav.unknown_interval_label` | Unrecognized interval label | Manual |
| `scaffold.missing_interval_nav` | Fewer than 5 nav lines present | Maybe |

Future dates are **not** flagged as missing files (tomorrow's note may not exist yet).

### Nav scan results — all daily notes (3,626 files)

| Category | Count | Notes |
| --- | ---: | --- |
| `nav.wrong_prev_date` | 4,308 | Stale/wrong prev links |
| `nav.wrong_next_date` | 4,019 | Stale/wrong next links |
| `nav.missing_target_file` | 539 | Correct link, note file absent |
| `nav.unparseable_link` | 86 | e.g. `2025-06-28, Sat 1` typo |
| `scaffold.missing_interval_nav` | 27 | Incomplete nav block |
| `nav.wrong_interval_order` | 8 | Shifted/missing day line |
| `nav.missing_interval_label` | 4 | Label omitted entirely |

**2,546** files have at least one nav issue. Many older notes accumulate offset drift over time; recent clusters are more actionable.

### Nav scan — since 2024-01-01 (893 files)

| Category | Count |
| --- | ---: |
| `nav.wrong_prev_date` | 101 |
| `nav.wrong_next_date` | 87 |
| `nav.missing_target_file` | 43 |
| `nav.unparseable_link` | 34 |
| `nav.wrong_interval_order` | 8 |
| `scaffold.missing_interval_nav` | 4 |
| `nav.missing_interval_label` | 1 |

**127** files with nav issues — much smaller, higher-signal set.

### Known cluster: May 2026 stale links

Notes from **2026-05-01 through 2026-05-07** (and nearby) share incorrect nav blocks — many still point at `2026-04-29` / `2026-05-01` instead of dates derived from each file's own date. Example (`2026-05-07, Thu.md`):

- day: got `2026-04-29` / `2026-05-01`, expected `2026-05-06` / `2026-05-08`
- all five intervals affected on worst offenders

Likely cause: nav block copied from another note without re-running the template. **High-priority fix candidate** for phase 2.

---

## Scaffold / markdown categories (lower priority)

| Category | Description | Auto-fix? |
| --- | --- | --- |
| `scaffold.missing_frontmatter` | No `---` YAML block | Maybe |
| `scaffold.frontmatter_field_drift` | Legacy or missing template fields | Report only |
| `scaffold.interval_label_legacy` | `>> (day)` vs `>> day` | Yes (cosmetic) |
| `scaffold.hotseat_marker` | `[[_The Hotseat]]<<` | Report only |
| `markdown.template_artifact` | Trailing `****` | Yes |
| `markdown.tag_in_heading` | `## #workoutlog` | Report only |
| `meta.sync_conflict_sibling` | Conflict duplicate exists | Manual |
| `meta.year_subfolder` | Under `Diary/YYYY/` | Info only |

Full scaffold scan (3,626 files): dominant cosmetic issues are `scaffold.interval_label_legacy` (3,560) and `meta.year_subfolder` (3,464). See `docs/diary-structure.md` for scaffold reference.

## Phase 2 fix priorities

1. **`nav.wrong_prev_date` / `nav.wrong_next_date`** — recompute all five lines from filename date; start with `--since 2024-01-01` or May 2026 cluster
2. **`markdown.template_artifact`** (39 files) — strip trailing `****`
3. **Sync conflicts** (13 pairs) — manual only
4. **`scaffold.interval_label_legacy`** — cosmetic `(day)` → `day`

## Re-run analysis

```powershell
# Nav links only (recommended)
python ops\raspberry-pi\obsidian-vault\scripts\analyze-diary-headers.py --nav-only --limit 0 --summary-only

# Full header scan
python ops\raspberry-pi\obsidian-vault\scripts\analyze-diary-headers.py --limit 0
```

Reports: `reports/` (gitignored).
