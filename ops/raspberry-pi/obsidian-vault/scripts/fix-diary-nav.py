#!/usr/bin/env python3
"""Fix wrong prev/next dates in Diary interval navigation lines."""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "analyze_diary_headers", _SCRIPT_DIR / "analyze-diary-headers.py"
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Could not load analyze-diary-headers.py")
_analyze = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _analyze
_SPEC.loader.exec_module(_analyze)


@dataclass
class LineChange:
    line_no: int
    label: str
    old: str
    new: str


@dataclass
class FileChange:
    relative_path: str
    lines: list[LineChange]


def label_suffix(label: str, use_parens: bool) -> str:
    return f" ({label})" if use_parens else f" {label}"


def rebuild_nav_line(
    note_date: date,
    label: str,
    use_parens: bool,
) -> str:
    prev_offset, next_offset = _analyze.INTERVAL_OFFSETS[label]
    prev = _analyze.format_link_target(note_date + timedelta(days=prev_offset))
    nxt = _analyze.format_link_target(note_date + timedelta(days=next_offset))
    return f"<< [[{prev}]] | [[{nxt}]] >>{label_suffix(label, use_parens)}"


def needs_date_fix(old_line: str, new_line: str) -> bool:
    old_match = _analyze.NAV_LINE_PATTERN.match(old_line.strip())
    new_match = _analyze.NAV_LINE_PATTERN.match(new_line.strip())
    if not old_match or not new_match:
        return old_line.strip() != new_line.strip()

    for group in (1, 2):
        old_parsed, _ = _analyze.parse_link_target(old_match.group(group))
        new_parsed, _ = _analyze.parse_link_target(new_match.group(group))
        if old_parsed != new_parsed:
            return True
    return False


def fix_file_content(path: Path, diary_root: Path) -> FileChange | None:
    skip = _analyze.should_skip_file(path, diary_root)
    if skip:
        return None

    note_date = _analyze.parse_note_date(path.stem)
    if note_date is None:
        return None

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    plain_lines = [line.rstrip("\r\n") for line in lines]

    _, fm_end = _analyze.extract_frontmatter(plain_lines)
    body_start = fm_end + 1 if fm_end else 0
    nav_lines = _analyze.find_interval_nav_lines(plain_lines, body_start)

    if not nav_lines:
        return None

    rel = path.relative_to(diary_root.parent).as_posix()
    changes: list[LineChange] = []

    for idx, (line_no, nav) in enumerate(nav_lines[:5]):
        expected_label = _analyze.INTERVAL_LABELS[idx]
        match = _analyze.NAV_LINE_PATTERN.match(nav)
        if not match:
            continue

        label = (match.group(3) or match.group(4) or expected_label).lower()
        if label not in _analyze.INTERVAL_OFFSETS:
            label = expected_label

        use_parens = match.group(3) is not None
        new_nav = rebuild_nav_line(note_date, label, use_parens)

        if needs_date_fix(nav, new_nav):
            changes.append(
                LineChange(line_no=line_no, label=label, old=nav, new=new_nav)
            )

    if not changes:
        return None

    return FileChange(relative_path=rel, lines=changes)


def apply_file_change(path: Path, change: FileChange) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    plain_lines = [line.rstrip("\r\n") for line in lines]

    for item in change.lines:
        idx = item.line_no - 1
        ending = ""
        if idx < len(lines) and lines[idx].endswith("\r\n"):
            ending = "\r\n"
        elif idx < len(lines) and lines[idx].endswith("\n"):
            ending = "\n"
        plain_lines[idx] = item.new
        lines[idx] = item.new + ending

    path.write_text("".join(lines), encoding="utf-8")


def collect_files(
    diary_root: Path,
    since: str | None,
    file_arg: str | None,
    limit: int,
) -> list[Path]:
    if file_arg:
        candidate = Path(file_arg)
        if not candidate.is_absolute():
            candidate = diary_root.parent / file_arg
        if not candidate.exists():
            candidate = diary_root / Path(file_arg).name
        return [candidate] if candidate.exists() else []

    candidates, _ = _analyze.collect_daily_notes(diary_root)
    candidates = _analyze.filter_by_since(candidates, since)
    candidates = _analyze.sort_by_date_desc(candidates)
    if limit > 0:
        return candidates[:limit]
    return candidates


def run_git_snapshot(message: str, push: bool = False) -> None:
    script = _SCRIPT_DIR / "vault-git-snapshot.ps1"
    if not script.exists():
        raise FileNotFoundError(f"Git snapshot script not found: {script}")

    args = ["powershell", "-NoProfile", "-File", str(script), "-Message", message]
    if push:
        args.append("-Push")
    result = subprocess.run(args, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "vault-git-snapshot.ps1 failed")


def ensure_git_ready(obsidian_vault_dir: Path) -> None:
    config_env = obsidian_vault_dir / "config.env"
    example_env = obsidian_vault_dir / "config.example.env"
    if not config_env.exists() and example_env.exists():
        config_env.write_text(example_env.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Created {config_env} from example.")

    bootstrap = _SCRIPT_DIR / "vault-git-bootstrap.ps1"
    config = _analyze.load_config(config_env if config_env.exists() else example_env)
    git_dir = Path(config.get("GIT_DIR", ""))
    if not git_dir.exists() and bootstrap.exists():
        print("Running vault-git-bootstrap.ps1 (one-time)...")
        result = subprocess.run(
            ["powershell", "-NoProfile", "-File", str(bootstrap)],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout.strip())
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "vault-git-bootstrap.ps1 failed")


def print_changes(changes: list[FileChange]) -> None:
    for fc in changes:
        print(f"\n{fc.relative_path}")
        for line in fc.lines:
            print(f"  L{line.line_no} {line.label}:")
            print(f"    - {line.old}")
            print(f"    + {line.new}")

    line_count = sum(len(fc.lines) for fc in changes)
    print(f"\n{len(changes)} file(s) would change, {line_count} line(s)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix Diary interval nav prev/next dates")
    parser.add_argument("--apply", action="store_true", help="Write fixes (default: dry-run)")
    parser.add_argument("--since", help="Only notes on or after YYYY-MM-DD")
    parser.add_argument("--file", help="Single file path relative to vault or Diary")
    parser.add_argument("--limit", type=int, default=0, help="Max files (0 = no limit)")
    parser.add_argument("--push", action="store_true", help="Push git snapshot after apply")
    parser.add_argument("--skip-git", action="store_true", help="Skip git snapshots (not recommended)")
    args = parser.parse_args()

    vault_path, diary_root, _ = _analyze.resolve_paths(_SCRIPT_DIR)
    obsidian_vault_dir = _SCRIPT_DIR.parent

    files = collect_files(diary_root, args.since, args.file, args.limit)
    if not files:
        print("No matching daily note files found.", file=sys.stderr)
        return 1

    pending: list[tuple[Path, FileChange]] = []
    for path in files:
        change = fix_file_content(path, diary_root)
        if change:
            pending.append((path, change))

    if not pending:
        print("No nav date fixes needed.")
        return 0

    print_changes([c for _, c in pending])

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to write changes.")
        return 0

    if not args.skip_git:
        ensure_git_ready(obsidian_vault_dir)
        run_git_snapshot("pre: fix diary nav prev/next dates")

    for path, change in pending:
        apply_file_change(path, change)
        print(f"Updated {change.relative_path}")

    if not args.skip_git:
        run_git_snapshot("post: fix diary nav prev/next dates", push=args.push)

    return 0


if __name__ == "__main__":
    sys.exit(main())
