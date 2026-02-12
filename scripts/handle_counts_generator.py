#!/usr/bin/env python3
"""
Read summary files (SUMMARY_DIR) and export files (EXPORT_DIR), output CSV of handle stats.

Uses SUMMARY_DIR, EXPORT_DIR, and HANDLES from config (.env). Output includes every
.env handle and every handle cited in summaries (case-insensitive). Columns:
handle (no @), in_env, snr (summary_mentions/exported_tweets), exported_tweets, summary_mentions.

Usage:
    python scripts/handle_counts_generator.py
    python scripts/handle_counts_generator.py --output logs/summary_handle_counts.csv
"""

import argparse
import csv
import os
import re
import sys

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging_utils import log_error, log_info, log_success

SCRIPT_TAG = "HandleCounts"

# Filename: X-YYYY-MM-DD.html or X-YYYY-MM-DD.md
SUMMARY_FILE_PATTERN = re.compile(r"^X-(\d{4}-\d{2}-\d{2})\.(html|md)$")
# Export: X-YYYY-MM-DD.md only
EXPORT_FILE_PATTERN = re.compile(r"^X-(\d{4}-\d{2}-\d{2})\.md$")
# Section header in export: ... @handle: (optional trailing whitespace)
EXPORT_SECTION_HEADER_PATTERN = re.compile(r"@([A-Za-z0-9_]+):\s*$")
# @handle in content (alphanumeric and underscore)
HANDLE_PATTERN = re.compile(r"@([A-Za-z0-9_]+)")


def _ensure_env():
    """Load environment and return (HANDLES, SUMMARY_DIR, EXPORT_DIR) from config."""
    from utils import ensure_environment_loaded

    ensure_environment_loaded()
    from config import HANDLES, SUMMARY_DIR, EXPORT_DIR

    return HANDLES, SUMMARY_DIR, EXPORT_DIR


def _normalize_display(handle: str) -> str:
    """Return display form: ensure @ prefix."""
    s = handle.strip()
    return f"@{s}" if s and not s.startswith("@") else s


def _canonical_key(handle: str) -> str:
    """Return lowercase key for deduplication and matching."""
    s = handle.strip()
    if s.startswith("@"):
        s = s[1:]
    return s.lower()


def _handle_for_export(display: str) -> str:
    """Return handle without @ for CSV export."""
    s = display.strip()
    return s[1:] if s.startswith("@") else s


def discover_summary_files(summary_dir: str) -> list[tuple[str, str]]:
    """List summary files and return (file_path, YYYY-MM) for each.

    Args:
        summary_dir: Path to data/summary (or SUMMARY_DIR).

    Returns:
        List of (absolute_path, month_str) for files matching X-YYYY-MM-DD.{html,md}.
    """
    if not os.path.isdir(summary_dir):
        return []
    out = []
    for name in os.listdir(summary_dir):
        m = SUMMARY_FILE_PATTERN.match(name)
        if m:
            date_str = m.group(1)
            month_str = date_str[:7]  # YYYY-MM
            path = os.path.join(summary_dir, name)
            if os.path.isfile(path):
                out.append((path, month_str))
    return out


def discover_export_files(export_dir: str) -> list[str]:
    """List export files and return full paths for each.

    Args:
        export_dir: Path to data/export (or EXPORT_DIR).

    Returns:
        List of absolute paths for files matching X-YYYY-MM-DD.md.
    """
    if not os.path.isdir(export_dir):
        return []
    out = []
    for name in os.listdir(export_dir):
        if EXPORT_FILE_PATTERN.match(name):
            path = os.path.join(export_dir, name)
            if os.path.isfile(path):
                out.append(path)
    return out


def count_exported_tweets_by_handle(export_paths: list[str]) -> dict[str, int]:
    """Parse export files and return total tweet count per handle (canonical key).

    Section headers are lines ending with @handle:. Bullet lines starting with "- "
    are tweets. Aggregates across all files.

    Args:
        export_paths: Full paths to X-YYYY-MM-DD.md files.

    Returns:
        Dict mapping canonical_handle -> total tweet count.
    """
    totals = {}
    for path in export_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            log_error(SCRIPT_TAG, f"Could not read {path}", e)
            continue
        i = 0
        while i < len(lines):
            line = lines[i]
            m = EXPORT_SECTION_HEADER_PATTERN.search(line.rstrip("\n").rstrip())
            if m:
                key = m.group(1).lower()
                count = 0
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if EXPORT_SECTION_HEADER_PATTERN.search(next_line.rstrip("\n").rstrip()):
                        break
                    if next_line.strip().startswith("- "):
                        count += 1
                    i += 1
                totals[key] = totals.get(key, 0) + count
                continue
            i += 1
    return totals


def extract_handle_counts(content: str) -> dict[str, int]:
    """Count each @handle occurrence in text. Keys are canonical (lowercase, no @).

    Args:
        content: Raw file text (HTML or Markdown).

    Returns:
        Dict mapping canonical_handle -> count.
    """
    counts = {}
    for m in HANDLE_PATTERN.finditer(content):
        raw = m.group(1)
        key = raw.lower()
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_month_counts(
    file_list: list[tuple[str, str]],
) -> tuple[dict[str, dict[str, int]], set[str]]:
    """Read files, count mentions per (handle, month). Return (counts, all_cited_handles).

    counts: canonical_handle -> { month_str -> count }
    all_cited_handles: set of canonical keys that appeared in at least one file.

    Args:
        file_list: From discover_summary_files: (path, YYYY-MM).

    Returns:
        (counts nested dict, set of canonical handle keys).
    """
    # canonical_handle -> month -> count
    counts = {}
    for path, month_str in file_list:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            log_error(SCRIPT_TAG, f"Could not read {path}", e)
            continue
        file_counts = extract_handle_counts(content)
        for key, n in file_counts.items():
            if key not in counts:
                counts[key] = {}
            counts[key][month_str] = counts[key].get(month_str, 0) + n
    cited = set(counts.keys())
    return counts, cited


def all_handles_for_csv(env_handles: list[str], cited_canonical: set[str]) -> list[str]:
    """Merge .env handles and cited-only handles; return display-format list.

    Env handles appear first (in .env order), then cited-only in sorted order.
    Case-insensitive: cited handle that matches an env handle is not duplicated.

    Args:
        env_handles: From config.HANDLES (may or may not have @).
        cited_canonical: Set of canonical (lowercase) handles from summaries.

    Returns:
        List of display handles (@handle) for CSV rows, no duplicates.
    """
    seen = set()
    ordered_display = []
    for h in env_handles:
        if not h:
            continue
        k = _canonical_key(h)
        if k in seen:
            continue
        seen.add(k)
        ordered_display.append(_normalize_display(h))
    for k in sorted(cited_canonical):
        if k in seen:
            continue
        seen.add(k)
        ordered_display.append("@" + k)
    return ordered_display


def write_csv(
    output_path: str,
    display_handles: list[str],
    env_canonical: set[str],
    exported_tweets: dict[str, int],
    summary_mentions: dict[str, int],
) -> None:
    """Write CSV: handle (no @), in_env, snr, exported_tweets, summary_mentions; one row per handle.

    Args:
        output_path: Path to output CSV.
        display_handles: Row order (display form, e.g. @handle).
        env_canonical: Set of canonical handle keys that are in .env (1 in column, else 0).
        exported_tweets: canonical_handle -> total tweets from export files.
        summary_mentions: canonical_handle -> total mentions in summary files.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fieldnames = ["handle", "in_env", "snr", "exported_tweets", "summary_mentions"]
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for display in display_handles:
            key = _canonical_key(display)
            exp = exported_tweets.get(key, 0)
            summ = summary_mentions.get(key, 0)
            snr = round(summ / exp, 2) if exp else 0.0
            row = {
                "handle": _handle_for_export(display),
                "in_env": 1 if key in env_canonical else 0,
                "snr": snr,
                "exported_tweets": exp,
                "summary_mentions": summ,
            }
            writer.writerow(row)


def run(
    output_path: str,
    summary_dir: str,
    export_dir: str,
    env_handles: list[str],
) -> bool:
    """Discover summary and export files, aggregate counts, write CSV.

    Args:
        output_path: Where to write the CSV.
        summary_dir: Directory containing X-YYYY-MM-DD.{html,md} summary files.
        export_dir: Directory containing X-YYYY-MM-DD.md export files.
        env_handles: List of handles from config (HANDLES).

    Returns:
        True if CSV was written, False on failure.
    """
    # Summary files -> summary_mentions (total per handle)
    summary_file_list = discover_summary_files(summary_dir)
    if not summary_file_list:
        log_info(SCRIPT_TAG, f"No summary files found in {summary_dir}; writing CSV with env handles only.")
    else:
        log_info(SCRIPT_TAG, f"Found {len(summary_file_list)} summary files in {summary_dir}")

    counts, cited_canonical = build_month_counts(summary_file_list)
    summary_mentions = {}
    for key, month_counts in counts.items():
        summary_mentions[key] = sum(month_counts.values())

    # Export files -> exported_tweets (total per handle)
    export_paths = discover_export_files(export_dir)
    if not export_paths:
        log_info(SCRIPT_TAG, f"No export files found in {export_dir}; exported_tweets will be 0 for all handles.")
    else:
        log_info(SCRIPT_TAG, f"Found {len(export_paths)} export files in {export_dir}")
    exported_tweets = count_exported_tweets_by_handle(export_paths)

    display_handles = all_handles_for_csv(env_handles, cited_canonical)
    if not display_handles:
        log_error(SCRIPT_TAG, "No handles to output (env HANDLES empty and no citations)")
        return False

    env_canonical = {_canonical_key(h) for h in env_handles if h}
    write_csv(output_path, display_handles, env_canonical, exported_tweets, summary_mentions)
    log_success(SCRIPT_TAG, f"Wrote {len(display_handles)} handles to {output_path}")
    return True


def main() -> None:
    """Load config, parse args, run and exit."""
    parser = argparse.ArgumentParser(
        description="Generate summary_handle_counts.csv (handle, in_env, exported_tweets, summary_mentions)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument(
        "--output",
        default=os.path.join(root, "logs", "summary_handle_counts.csv"),
        help="Path for output CSV",
    )
    args = parser.parse_args()

    try:
        handles, summary_dir, export_dir = _ensure_env()
    except SystemExit:
        raise
    except Exception as e:
        log_error(SCRIPT_TAG, "Failed to load config", e)
        sys.exit(1)

    log_info(SCRIPT_TAG, f"Summary dir: {summary_dir}, export dir: {export_dir}, env handles: {len(handles)}")
    if not run(args.output, summary_dir, export_dir, handles):
        sys.exit(1)


if __name__ == "__main__":
    main()
