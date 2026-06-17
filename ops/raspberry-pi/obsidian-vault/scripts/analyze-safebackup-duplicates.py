#!/usr/bin/env python3
"""Compare Pi OneDrive safeBackup copies against canonical vault files."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

SAFEBACKUP_PATTERN = re.compile(r"-[\w]+-safeBackup-\d+\.md$", re.IGNORECASE)


def load_config(config_path: Path) -> dict[str, str]:
    config: dict[str, str] = {}
    if not config_path.is_file():
        return config
    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        config[key.strip()] = os.path.expandvars(value.strip())
    return config


def resolve_vault_path(script_dir: Path) -> Path:
    config = load_config(script_dir.parent / "config.env")
    vault = config.get("VAULT_PATH", r"C:\Users\Ben\OneDrive\Obsidian\hej")
    return Path(vault)


def canonical_name(backup_name: str) -> str | None:
    if not SAFEBACKUP_PATTERN.search(backup_name):
        return None
    return SAFEBACKUP_PATTERN.sub(".md", backup_name)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip() + "\n"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


@dataclass
class Comparison:
    backup_path: str
    canonical_path: str | None
    canonical_exists: bool
    verdict: str
    backup_bytes: int
    canonical_bytes: int | None
    backup_mtime: str
    canonical_mtime: str | None
    backup_lines: int
    canonical_lines: int | None
    normalized_match: bool
    byte_identical: bool
    diff_line_count: int
    diff_preview: list[str]


def compare_pair(backup: Path, vault: Path) -> Comparison:
    rel_backup = backup.relative_to(vault).as_posix()
    canon_name = canonical_name(backup.name)
    if not canon_name:
        return Comparison(
            backup_path=rel_backup,
            canonical_path=None,
            canonical_exists=False,
            verdict="unparseable_name",
            backup_bytes=backup.stat().st_size,
            canonical_bytes=None,
            backup_mtime=datetime.fromtimestamp(backup.stat().st_mtime).isoformat(timespec="seconds"),
            canonical_mtime=None,
            backup_lines=0,
            canonical_lines=None,
            normalized_match=False,
            byte_identical=False,
            diff_line_count=0,
            diff_preview=[],
        )

    canonical = backup.with_name(canon_name)
    rel_canonical = canonical.relative_to(vault).as_posix()
    backup_text = read_text(backup)
    backup_norm = normalize_text(backup_text)
    backup_lines = backup_norm.count("\n")

    if not canonical.is_file():
        return Comparison(
            backup_path=rel_backup,
            canonical_path=rel_canonical,
            canonical_exists=False,
            verdict="canonical_missing",
            backup_bytes=backup.stat().st_size,
            canonical_bytes=None,
            backup_mtime=datetime.fromtimestamp(backup.stat().st_mtime).isoformat(timespec="seconds"),
            canonical_mtime=None,
            backup_lines=backup_lines,
            canonical_lines=None,
            normalized_match=False,
            byte_identical=False,
            diff_line_count=0,
            diff_preview=[],
        )

    canonical_text = read_text(canonical)
    canonical_norm = normalize_text(canonical_text)
    canonical_lines = canonical_norm.count("\n")
    byte_identical = backup.read_bytes() == canonical.read_bytes()
    normalized_match = backup_norm == canonical_norm

    diff = list(
        difflib.unified_diff(
            canonical_norm.splitlines(keepends=True),
            backup_norm.splitlines(keepends=True),
            fromfile=rel_canonical,
            tofile=rel_backup,
            n=2,
        )
    )
    diff_preview = [line.rstrip("\n") for line in diff[:24]]

    if byte_identical:
        verdict = "identical_bytes"
    elif normalized_match:
        verdict = "identical_normalized"
    else:
        verdict = "content_differs"

    return Comparison(
        backup_path=rel_backup,
        canonical_path=rel_canonical,
        canonical_exists=True,
        verdict=verdict,
        backup_bytes=backup.stat().st_size,
        canonical_bytes=canonical.stat().st_size,
        backup_mtime=datetime.fromtimestamp(backup.stat().st_mtime).isoformat(timespec="seconds"),
        canonical_mtime=datetime.fromtimestamp(canonical.stat().st_mtime).isoformat(timespec="seconds"),
        backup_lines=backup_lines,
        canonical_lines=canonical_lines,
        normalized_match=normalized_match,
        byte_identical=byte_identical,
        diff_line_count=len(diff),
        diff_preview=diff_preview,
    )


def group_by_canonical(comparisons: list[Comparison]) -> dict[str, list[Comparison]]:
    groups: dict[str, list[Comparison]] = {}
    for item in comparisons:
        key = item.canonical_path or item.backup_path
        groups.setdefault(key, []).append(item)
    return groups


def render_markdown(
    vault: Path,
    comparisons: list[Comparison],
    groups: dict[str, list[Comparison]],
) -> str:
    from collections import Counter

    counts = Counter(c.verdict for c in comparisons)
    lines = [
        "# safeBackup duplicate analysis",
        "",
        f"Vault: `{vault}`",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Backup files scanned: **{len(comparisons)}**",
        f"Canonical notes involved: **{len(groups)}**",
        "",
        "## Verdict summary",
        "",
        "| Verdict | Count | Meaning |",
        "| --- | ---: | --- |",
        f"| `identical_bytes` | {counts.get('identical_bytes', 0)} | Backup matches canonical exactly — safe to delete backup |",
        f"| `identical_normalized` | {counts.get('identical_normalized', 0)} | Same text after whitespace/line-ending normalization — safe to delete backup |",
        f"| `content_differs` | {counts.get('content_differs', 0)} | Text differs — review before deleting |",
        f"| `canonical_missing` | {counts.get('canonical_missing', 0)} | No canonical file beside backup — keep until reviewed |",
        f"| `unparseable_name` | {counts.get('unparseable_name', 0)} | Filename did not match safeBackup pattern |",
        "",
        "## By canonical note",
        "",
    ]

    def sort_key(path: str) -> str:
        return path

    for canonical_path in sorted(groups, key=sort_key):
        items = sorted(groups[canonical_path], key=lambda c: c.backup_path)
        lines.append(f"### `{canonical_path}`")
        lines.append("")
        if items[0].canonical_exists:
            lines.append(
                f"- Canonical: {items[0].canonical_bytes} bytes, "
                f"{items[0].canonical_lines} lines, mtime `{items[0].canonical_mtime}`"
            )
        else:
            lines.append("- Canonical: **missing**")
        lines.append(f"- Backups: {len(items)}")
        lines.append("")

        for item in items:
            lines.append(f"#### `{item.backup_path}` → **{item.verdict}**")
            lines.append("")
            lines.append(
                f"- Backup: {item.backup_bytes} bytes, {item.backup_lines} lines, "
                f"mtime `{item.backup_mtime}`"
            )
            if item.verdict in {"identical_bytes", "identical_normalized"}:
                lines.append("- Action: **likely safe to delete** (duplicate of canonical)")
            elif item.verdict == "content_differs":
                delta_bytes = item.backup_bytes - (item.canonical_bytes or 0)
                delta_lines = item.backup_lines - (item.canonical_lines or 0)
                sign_b = "+" if delta_bytes >= 0 else ""
                sign_l = "+" if delta_lines >= 0 else ""
                lines.append(
                    f"- Size delta vs canonical: {sign_b}{delta_bytes} bytes, "
                    f"{sign_l}{delta_lines} lines"
                )
                lines.append("- Action: **review diff before deleting**")
                if item.diff_preview:
                    lines.append("")
                    lines.append("```diff")
                    lines.extend(item.diff_preview)
                    if item.diff_line_count > len(item.diff_preview):
                        lines.append(f"... ({item.diff_line_count - len(item.diff_preview)} more diff lines)")
                    lines.append("```")
            elif item.verdict == "canonical_missing":
                lines.append("- Action: **keep or merge manually** — canonical file not found")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vault",
        type=Path,
        help="Vault root (default: from config.env or Windows OneDrive path)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Write machine-readable JSON report to this path",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        help="Write markdown report to this path",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    vault = args.vault or resolve_vault_path(script_dir)
    if not vault.is_dir():
        print(f"Vault not found: {vault}", file=sys.stderr)
        return 1

    backups = sorted(
        p for p in vault.rglob("*") if p.is_file() and "-safeBackup-" in p.name
    )
    comparisons = [compare_pair(p, vault) for p in backups]
    groups = group_by_canonical(comparisons)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    reports_dir = script_dir.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    md_out = args.md_out or reports_dir / f"safebackup-analysis-{timestamp}.md"
    json_out = args.json_out or reports_dir / f"safebackup-analysis-{timestamp}.json"

    payload = {
        "vault": str(vault),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "backup_file_count": len(comparisons),
        "canonical_note_count": len(groups),
        "verdict_counts": dict(
            __import__("collections").Counter(c.verdict for c in comparisons)
        ),
        "comparisons": [asdict(c) for c in comparisons],
    }
    json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_out.write_text(render_markdown(vault, comparisons, groups), encoding="utf-8")

    print(f"Scanned {len(comparisons)} safeBackup files across {len(groups)} canonical notes")
    for verdict, count in sorted(payload["verdict_counts"].items()):
        print(f"  {verdict}: {count}")
    print(f"\nMarkdown: {md_out}")
    print(f"JSON:     {json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
