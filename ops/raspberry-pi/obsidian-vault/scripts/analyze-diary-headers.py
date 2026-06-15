#!/usr/bin/env python3
"""Read-only scanner for Diary daily note header/scaffold issues."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

DAILY_NOTE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}, \w{3}\.md$")
CONFLICT_PATTERN = re.compile(r"\(conflict \d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\)")
DEVICE_SUFFIX_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}, \w{3}-.+?\.md$")
NAV_LINE_PATTERN = re.compile(
    r"^<< \[\[([^\]]+)\]\] \| \[\[([^\]]+)\]\] >>(?: \((\w+)\)| (\w+))?\s*$"
)
LINK_DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2}),\s*(\w+)$")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")
TEMPLATE_ARTIFACT_PATTERN = re.compile(r":\*{2,}\s*$|:\*{4}$")
EMPTY_NUMBERED_HEADER = re.compile(r"^#{1,6}\s+\d+\.\s*$")
TAG_IN_HEADING = re.compile(r"^#{1,6}\s+#\w")

CURRENT_TEMPLATE_FIELDS = {
    "Heading",
    "Comfort",
    "Home (Leipzig)",
    "Walk >30mins.",
    "Whereabouts",
    "Sports",
    "Drugs",
    "E",
    "Purchases",
    "Meditate",
    "Interessant",
}

LEGACY_TEMPLATE_FIELDS = {"Wellbeing", "Work", "Finished", "Home (Leiden)"}

INTERVAL_LABELS = ("day", "week", "month", "quarter", "year")

# Matches Obsidian Daily Note template (Templater tp.date offsets).
INTERVAL_OFFSETS: dict[str, tuple[int, int]] = {
    "day": (-1, 1),
    "week": (-7, 7),
    "month": (-30, 30),
    "quarter": (-90, 90),
    "year": (-365, 365),
}


@dataclass
class Issue:
    category: str
    detail: str
    line: int | None = None


@dataclass
class FileReport:
    path: str
    relative_path: str
    date: str | None
    skipped: bool = False
    skip_reason: str | None = None
    issues: list[Issue] = field(default_factory=list)


@dataclass
class ScanReport:
    scanned_at: str
    vault_path: str
    diary_folder: str
    files_scanned: int
    files_skipped: int
    files_with_issues: int
    issue_counts: dict[str, int]
    files: list[FileReport] = field(default_factory=list)


def load_config(config_path: Path) -> dict[str, str]:
    config: dict[str, str] = {}
    if not config_path.exists():
        return config
    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        value = os.path.expandvars(value)
        config[key.strip()] = value
    return config


def resolve_paths(script_dir: Path) -> tuple[Path, Path, Path]:
    obsidian_vault_dir = script_dir.parent
    config = load_config(obsidian_vault_dir / "config.env")
    if not config:
        config = load_config(obsidian_vault_dir / "config.example.env")

    vault_path = Path(
        config.get("VAULT_PATH", r"C:\Users\Ben\OneDrive\Obsidian\hej")
    )
    diary_folder = config.get("DIARY_FOLDER", "Diary")
    reports_dir = obsidian_vault_dir / "reports"
    return vault_path, vault_path / diary_folder, reports_dir


def should_skip_file(path: Path, diary_root: Path) -> str | None:
    name = path.name
    rel = path.relative_to(diary_root).as_posix()

    if name == "0_Legend & Diary Conventions.md":
        return "legend_file"
    if CONFLICT_PATTERN.search(name):
        return "sync_conflict"
    if DEVICE_SUFFIX_PATTERN.match(name):
        return "device_suffix_duplicate"
    if "Archive" in rel.split("/"):
        return "archive_path"
    if not DAILY_NOTE_PATTERN.match(name):
        return "not_daily_note_pattern"
    return None


def parse_date_from_filename(name: str) -> str | None:
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", name)
    return match.group(1) if match else None


def parse_note_date(name_or_stem: str) -> date | None:
    iso = parse_date_from_filename(name_or_stem)
    if not iso:
        return None
    try:
        return date.fromisoformat(iso)
    except ValueError:
        return None


def format_link_target(d: date) -> str:
    return f"{d.isoformat()}, {d.strftime('%a')}"


def parse_link_target(target: str) -> tuple[date | None, str | None]:
    match = LINK_DATE_PATTERN.match(target.strip())
    if not match:
        return None, None
    try:
        return date.fromisoformat(match.group(1)), match.group(2)
    except ValueError:
        return None, match.group(2)


def build_diary_index(diary_root: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = defaultdict(list)
    for path in diary_root.rglob("*.md"):
        if DAILY_NOTE_PATTERN.match(path.name):
            index[path.stem].append(path)
    return index


def analyze_interval_nav(
    nav_lines: list[tuple[int, str]],
    note_date: date,
    diary_index: dict[str, list[Path]],
) -> list[Issue]:
    issues: list[Issue] = []

    if not nav_lines:
        return issues

    for idx, (line_no, nav) in enumerate(nav_lines[:5]):
        expected_label = INTERVAL_LABELS[idx] if idx < len(INTERVAL_LABELS) else None
        match = NAV_LINE_PATTERN.match(nav)
        if not match:
            issues.append(
                Issue("nav.unparseable_line", f"could not parse nav line: {nav!r}", line_no)
            )
            continue

        prev_raw, next_raw = match.group(1), match.group(2)
        label = (match.group(3) or match.group(4) or "").lower()

        if not label:
            issues.append(
                Issue("nav.missing_interval_label", f"nav line has no day/week/month/quarter/year label", line_no)
            )
            label = expected_label or "day"

        if expected_label and label != expected_label:
            issues.append(
                Issue(
                    "nav.wrong_interval_order",
                    f"line {idx + 1} label {label!r}, expected {expected_label!r}",
                    line_no,
                )
            )

        if label not in INTERVAL_OFFSETS:
            issues.append(
                Issue("nav.unknown_interval_label", f"unknown interval label: {label!r}", line_no)
            )
            continue

        prev_offset, next_offset = INTERVAL_OFFSETS[label]
        expected_prev = format_link_target(note_date + timedelta(days=prev_offset))
        expected_next = format_link_target(note_date + timedelta(days=next_offset))

        for direction, raw, expected in (
            ("prev", prev_raw, expected_prev),
            ("next", next_raw, expected_next),
        ):
            parsed_date, weekday_label = parse_link_target(raw)
            if parsed_date is None:
                issues.append(
                    Issue(
                        "nav.unparseable_link",
                        f"{direction} link not in YYYY-MM-DD, ddd format: {raw!r}",
                        line_no,
                    )
                )
                continue

            expected_date = date.fromisoformat(expected.split(", ")[0])
            date_matches = parsed_date == expected_date

            if not date_matches:
                issues.append(
                    Issue(
                        f"nav.wrong_{direction}_date",
                        f"{label} {direction}: got {raw!r}, expected [[{expected}]]",
                        line_no,
                    )
                )

            expected_weekday = expected_date.strftime("%a")
            if date_matches and weekday_label and weekday_label != expected_weekday:
                issues.append(
                    Issue(
                        "nav.wrong_weekday_label",
                        f"{label} {direction}: date {parsed_date} is {expected_weekday}, link says {weekday_label!r}",
                        line_no,
                    )
                )

            if raw not in diary_index and expected_date <= date.today():
                issues.append(
                    Issue(
                        "nav.missing_target_file",
                        f"{label} {direction}: no daily note file for [[{expected}]]",
                        line_no,
                    )
                )

    return issues


def extract_frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    if not lines or lines[0].strip() != "---":
        return {}, 0

    fields: dict[str, str] = {}
    end_idx = 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
        if ":" in lines[i]:
            key, _, val = lines[i].partition(":")
            fields[key.strip()] = val.strip()

    return fields, end_idx


def find_interval_nav_lines(lines: list[str], start: int) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for i in range(start, min(start + 30, len(lines))):
        stripped = lines[i].strip()
        if stripped.startswith("<< [[") and ">>" in stripped:
            found.append((i + 1, stripped))
        elif stripped and not stripped.startswith("<<"):
            if found:
                break
    return found


def analyze_markdown_headings(lines: list[str], body_start: int) -> list[Issue]:
    issues: list[Issue] = []
    prev_level = 0
    seen_heading = False
    max_level_before_h1: int | None = None

    for i in range(body_start, len(lines)):
        line = lines[i]
        match = HEADING_PATTERN.match(line)
        if not match:
            continue

        level = len(match.group(1))
        text = match.group(2).strip()
        line_no = i + 1

        if TEMPLATE_ARTIFACT_PATTERN.search(line):
            issues.append(
                Issue("markdown.template_artifact", f"trailing asterisks: {text!r}", line_no)
            )

        if EMPTY_NUMBERED_HEADER.match(line):
            issues.append(
                Issue("markdown.empty_numbered_header", f"empty numbered header: {text!r}", line_no)
            )

        if TAG_IN_HEADING.match(line):
            issues.append(
                Issue("markdown.tag_in_heading", f"tag in heading: {text!r}", line_no)
            )

        if seen_heading and prev_level > 0 and level > prev_level + 1:
            issues.append(
                Issue(
                    "markdown.heading_level_skip",
                    f"h{level} after h{prev_level} (skipped level)",
                    line_no,
                )
            )

        if level == 1 and seen_heading and max_level_before_h1 and max_level_before_h1 >= 2:
            issues.append(
                Issue(
                    "markdown.h1_mid_document",
                    f"H1 {text!r} appears after deeper headings",
                    line_no,
                )
            )

        if level == 1:
            max_level_before_h1 = None
        elif max_level_before_h1 is None or level > max_level_before_h1:
            max_level_before_h1 = level

        prev_level = level
        seen_heading = True

    return issues


def analyze_file(
    path: Path,
    diary_root: Path,
    conflict_siblings: set[str],
    diary_index: dict[str, list[Path]],
    nav_only: bool = False,
) -> FileReport:
    rel = path.relative_to(diary_root.parent).as_posix()
    rel_diary = path.relative_to(diary_root).as_posix()
    report = FileReport(
        path=str(path),
        relative_path=rel,
        date=parse_date_from_filename(path.name),
    )

    skip = should_skip_file(path, diary_root)
    if skip:
        report.skipped = True
        report.skip_reason = skip
        return report

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        report.issues.append(Issue("meta.read_error", "could not decode as utf-8"))
        return report

    lines = text.splitlines()
    issues: list[Issue] = []

    fields, fm_end = extract_frontmatter(lines)
    if fm_end == 0:
        if not nav_only:
            issues.append(Issue("scaffold.missing_frontmatter", "no --- frontmatter block"))
        body_start = 0
    else:
        body_start = fm_end + 1
        if not nav_only:
            present_keys = set(fields.keys())
            legacy_present = present_keys & LEGACY_TEMPLATE_FIELDS
            missing_current = CURRENT_TEMPLATE_FIELDS - present_keys

            if legacy_present:
                issues.append(
                    Issue(
                        "scaffold.frontmatter_field_drift",
                        f"legacy fields present: {', '.join(sorted(legacy_present))}",
                    )
                )
            if missing_current and report.date and report.date >= "2024-01-01":
                issues.append(
                    Issue(
                        "scaffold.frontmatter_field_drift",
                        f"missing current template fields: {', '.join(sorted(missing_current))}",
                    )
                )

    nav_lines = find_interval_nav_lines(lines, body_start if body_start else 0)
    note_date = parse_note_date(path.stem)

    if note_date and nav_lines:
        issues.extend(analyze_interval_nav(nav_lines, note_date, diary_index))

    if not nav_only:
        if len(nav_lines) < 5:
            issues.append(
                Issue(
                    "scaffold.missing_interval_nav",
                    f"found {len(nav_lines)} interval nav lines, expected 5",
                )
            )
        else:
            for line_no, nav in nav_lines[:5]:
                if "(day)" in nav or "(week)" in nav or "(month)" in nav or "(quarter)" in nav or "(year)" in nav:
                    issues.append(
                        Issue("scaffold.interval_label_legacy", f"legacy parens label: {nav!r}", line_no)
                    )
                    break

        for i in range(body_start, min(body_start + 40, len(lines))):
            stripped = lines[i].strip()
            if stripped.startswith("[[_The Hotseat]]"):
                if stripped.endswith("<<"):
                    issues.append(
                        Issue(
                            "scaffold.hotseat_marker",
                            "Hotseat line has trailing << (likely intentional)",
                            i + 1,
                        )
                    )
                break

        if "/" in rel_diary and re.match(r"^\d{4}/", rel_diary):
            issues.append(
                Issue("meta.year_subfolder", f"file in year subfolder: {rel_diary}")
            )

        base_name = path.stem
        if base_name in conflict_siblings:
            issues.append(
                Issue(
                    "meta.sync_conflict_sibling",
                    "a sync-conflict duplicate exists for this note",
                )
            )

        issues.extend(analyze_markdown_headings(lines, body_start))
    elif len(nav_lines) < 5:
        issues.append(
            Issue(
                "scaffold.missing_interval_nav",
                f"found {len(nav_lines)} interval nav lines, expected 5",
            )
        )

    report.issues = issues
    return report


def collect_daily_notes(diary_root: Path) -> tuple[list[Path], set[str]]:
    if not diary_root.exists():
        raise FileNotFoundError(f"Diary folder not found: {diary_root}")

    all_md = list(diary_root.rglob("*.md"))
    conflict_bases: set[str] = set()
    for p in all_md:
        if CONFLICT_PATTERN.search(p.name):
            base = CONFLICT_PATTERN.sub("", p.stem).strip()
            conflict_bases.add(base)

    candidates = []
    for p in all_md:
        if should_skip_file(p, diary_root):
            continue
        candidates.append(p)

    return candidates, conflict_bases


def filter_by_since(files: Iterable[Path], since: str | None) -> list[Path]:
    if not since:
        return list(files)
    filtered = []
    for p in files:
        d = parse_date_from_filename(p.name)
        if d and d >= since:
            filtered.append(p)
    return filtered


def sort_by_date_desc(files: list[Path]) -> list[Path]:
    def key(p: Path) -> str:
        return parse_date_from_filename(p.name) or "0000-00-00"

    return sorted(files, key=key, reverse=True)


def build_summary_markdown(report: ScanReport) -> str:
    lines = [
        "# Diary Header Analysis Summary",
        "",
        f"Scanned at: {report.scanned_at}",
        f"Vault: `{report.vault_path}`",
        f"Diary: `{report.diary_folder}`",
        "",
        f"- Files scanned: {report.files_scanned}",
        f"- Files skipped: {report.files_skipped}",
        f"- Files with issues: {report.files_with_issues}",
        "",
        "## Issue counts",
        "",
        "| Category | Count | Auto-fix later? |",
        "| --- | ---: | --- |",
    ]

    auto_fix = {
        "nav.wrong_prev_date": "Yes",
        "nav.wrong_next_date": "Yes",
        "nav.wrong_weekday_label": "Yes",
        "nav.missing_target_file": "Maybe",
        "nav.unparseable_line": "Manual",
        "nav.unparseable_link": "Manual",
        "nav.wrong_interval_order": "Maybe",
        "nav.missing_interval_label": "Manual",
        "nav.unknown_interval_label": "Manual",
        "scaffold.interval_label_legacy": "Yes",
        "markdown.template_artifact": "Yes",
        "scaffold.missing_frontmatter": "Maybe",
        "scaffold.missing_interval_nav": "Maybe",
        "scaffold.frontmatter_field_drift": "Report only",
        "scaffold.hotseat_marker": "Report only",
        "markdown.heading_level_skip": "Report only",
        "markdown.h1_mid_document": "Report only",
        "markdown.empty_numbered_header": "Report only",
        "markdown.tag_in_heading": "Report only",
        "meta.sync_conflict_sibling": "Manual",
        "meta.year_subfolder": "Info only",
        "meta.read_error": "Manual",
    }

    for cat, count in sorted(report.issue_counts.items(), key=lambda x: (-x[1], x[0])):
        fix = auto_fix.get(cat, "TBD")
        lines.append(f"| `{cat}` | {count} | {fix} |")

    lines.extend(["", "## Sample files per category", ""])

    by_cat: dict[str, list[str]] = defaultdict(list)
    for f in report.files:
        if f.skipped:
            continue
        for issue in f.issues:
            if len(by_cat[issue.category]) < 3:
                detail = f" — {issue.detail}" if issue.detail else ""
                line = f" (L{issue.line})" if issue.line else ""
                by_cat[issue.category].append(f"- `{f.relative_path}`{line}{detail}")

    for cat in sorted(by_cat.keys()):
        lines.append(f"### `{cat}`")
        lines.extend(by_cat[cat])
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Diary daily note header analyzer")
    parser.add_argument("--nav-only", action="store_true", help="Only report interval nav link issues")
    parser.add_argument("--since", help="Only scan notes on or after YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=50, help="Max files to scan (0 = no limit)")
    parser.add_argument("--summary-only", action="store_true", help="Print summary only, skip writing reports")
    parser.add_argument("--verbose", action="store_true", help="Print per-file issues to stdout")
    parser.add_argument("--vault", help="Override vault path")
    parser.add_argument("--diary", help="Override diary folder name (default: Diary)")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    vault_path, diary_root, reports_dir = resolve_paths(script_dir)

    if args.vault:
        vault_path = Path(args.vault)
        diary_root = vault_path / (args.diary or "Diary")
    elif args.diary:
        diary_root = vault_path / args.diary

    if not diary_root.exists():
        print(f"Error: Diary folder not found: {diary_root}", file=sys.stderr)
        return 1

    candidates, conflict_bases = collect_daily_notes(diary_root)
    diary_index = build_diary_index(diary_root)
    candidates = filter_by_since(candidates, args.since)
    candidates = sort_by_date_desc(candidates)

    if args.limit and args.limit > 0:
        scan_list = candidates[: args.limit]
    else:
        scan_list = candidates

    file_reports: list[FileReport] = []
    issue_counter: Counter[str] = Counter()

    for path in scan_list:
        fr = analyze_file(
            path, diary_root, conflict_bases, diary_index, nav_only=args.nav_only
        )
        file_reports.append(fr)
        if args.verbose and fr.issues:
            print(f"\n{fr.relative_path}:")
            for issue in fr.issues:
                loc = f" L{issue.line}" if issue.line else ""
                print(f"  [{issue.category}]{loc} {issue.detail}")

    if args.nav_only:
        nav_categories = {"scaffold.missing_interval_nav"}
        for f in file_reports:
            f.issues = [
                i for i in f.issues
                if i.category.startswith("nav.") or i.category in nav_categories
            ]

    files_with_issues = sum(1 for f in file_reports if f.issues)
    for f in file_reports:
        for issue in f.issues:
            issue_counter[issue.category] += 1

    report = ScanReport(
        scanned_at=datetime.now().isoformat(timespec="seconds"),
        vault_path=str(vault_path),
        diary_folder=str(diary_root),
        files_scanned=len(file_reports),
        files_skipped=len(candidates) - len(scan_list) if args.limit else 0,
        files_with_issues=files_with_issues,
        issue_counts=dict(issue_counter),
        files=file_reports,
    )

    summary_md = build_summary_markdown(report)

    print(summary_md)

    if not args.summary_only:
        reports_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        json_path = reports_dir / f"diary-header-analysis-{ts}.json"
        md_path = reports_dir / f"diary-header-analysis-{ts}.md"

        payload = asdict(report)
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        md_path.write_text(summary_md, encoding="utf-8")
        print(f"\nWrote {json_path}")
        print(f"Wrote {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
