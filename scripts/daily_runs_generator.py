#!/usr/bin/env python3
"""
Parse pipeline log.txt and generate logs/daily_runs.csv.

Extracts one record per day (earliest run): date, time, sources, sum_in, sum_out,
sum_oi, trans_in, trans_out, trans_oi. Only successful runs with non-cached
summarizer and translator steps are included. sum_oi and trans_oi are
output/input token ratios (rounded to 2 decimals).

Usage:
    python scripts/daily_runs_generator.py
    python scripts/daily_runs_generator.py --input logs/log.txt --output logs/daily_runs.csv
"""

import argparse
import csv
import os
import re
import sys

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logging_utils import log_error, log_info, log_success

SCRIPT_TAG = "DailyRunsGenerator"


def process_logs(input_path: str, output_path: str) -> bool:
    """Parse log file and write daily runs CSV.

    Splits log by run separator, extracts date/time, sources, summarizer/translator
    token counts and o/i rates from non-cached steps. Keeps one row per date
    (earliest run of the day). Writes CSV to output_path.

    Args:
        input_path: Path to pipeline log file (e.g. logs/log.txt).
        output_path: Path for output CSV (e.g. logs/daily_runs.csv).

    Returns:
        True if CSV was written successfully, False if input missing or no valid runs.
    """
    if not os.path.exists(input_path):
        log_error(SCRIPT_TAG, f"Input file not found: {input_path}")
        return False

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    runs = re.split(r"──────────", content)
    daily_data = {}

    for run_block in runs:
        if not run_block.strip():
            continue

        start_match = re.search(
            r"✅ Started at (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})", run_block
        )
        if not start_match:
            continue

        date_str = start_match.group(1)
        time_str = start_match.group(2)

        if "✅ Converted to JSON" not in run_block or "✅ Published" not in run_block:
            continue

        gathered_sources = None
        for line in run_block.split("\n"):
            if "Gathered" in line and "using cached file" not in line:
                m = re.search(r"Gathered (\d+) sources", line)
                if m:
                    gathered_sources = int(m.group(1))
                    break
        if gathered_sources is None:
            continue

        summarizer_tokens = None
        for line in run_block.split("\n"):
            if "Summarized using" in line and "using cached file" not in line:
                m = re.search(
                    r"Summarized using (\d+) input tokens, (\d+) output tokens", line
                )
                if m:
                    summarizer_tokens = (int(m.group(1)), int(m.group(2)))
                    break
        if not summarizer_tokens:
            continue

        translator_tokens = None
        for line in run_block.split("\n"):
            if "Translated using" in line and "using cached file" not in line:
                m = re.search(
                    r"Translated using (\d+) input tokens, (\d+) output tokens", line
                )
                if m:
                    translator_tokens = (int(m.group(1)), int(m.group(2)))
                    break
        if not translator_tokens:
            continue

        sum_in, sum_out = summarizer_tokens[0], summarizer_tokens[1]
        trans_in, trans_out = translator_tokens[0], translator_tokens[1]
        sum_oi = round(sum_out / sum_in, 2) if sum_in else 0.0
        trans_oi = round(trans_out / trans_in, 2) if trans_in else 0.0

        record = {
            "date": date_str,
            "time": time_str,
            "sources": gathered_sources,
            "sum_in": sum_in,
            "sum_out": sum_out,
            "sum_oi": sum_oi,
            "trans_in": trans_in,
            "trans_out": trans_out,
            "trans_oi": trans_oi,
        }

        if date_str not in daily_data or time_str < daily_data[date_str]["time"]:
            daily_data[date_str] = record

    if not daily_data:
        log_error(SCRIPT_TAG, "No valid runs found in log")
        return False

    sorted_dates = sorted(daily_data.keys())
    header = [
        "date",
        "time",
        "sources",
        "sum_in",
        "sum_out",
        "sum_oi",
        "trans_in",
        "trans_out",
        "trans_oi",
    ]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for d in sorted_dates:
            writer.writerow(daily_data[d])

    log_success(SCRIPT_TAG, f"Wrote {len(daily_data)} rows to {output_path}")
    return True


def main() -> None:
    """Parse arguments and run daily runs generator."""
    parser = argparse.ArgumentParser(
        description="Generate daily_runs.csv (date, time, sources, sum_in/out/oi, trans_in/out/oi) from pipeline log",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument(
        "--input",
        default=os.path.join(root, "logs", "log.txt"),
        help="Path to pipeline log file",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(root, "logs", "daily_runs.csv"),
        help="Path for output CSV",
    )
    args = parser.parse_args()

    log_info(SCRIPT_TAG, f"Reading {args.input}")
    if not process_logs(args.input, args.output):
        sys.exit(1)


if __name__ == "__main__":
    main()
