#!/usr/bin/env python3
"""Append a concise, machine-derived P3 benchmark verdict to a CI summary."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    lines = ["## P3 benchmark evidence", ""]
    try:
        if not args.report.is_file():
            raise ValueError(f"validation report missing: {args.report}")
        report = json.loads(args.report.read_text(encoding="utf-8"))
        if report.get("validation") != "PASS" or report.get("all_records_valid") is not True:
            raise ValueError("validator report does not contain a PASS verdict")
        if not args.csv.is_file():
            raise ValueError(f"benchmark CSV missing: {args.csv}")
        with args.csv.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            raise ValueError("benchmark CSV has no data rows")
        row = rows[-1]
        lines += [
            "<strong>Benchmark validation: PASS</strong>",
            f"- Run ID: `{row['run_id']}`",
            f"- Dimension / nonzeros: `{row['dimension']}` / `{row['non_zero_count']}`",
            f"- Warm-up / measured iterations: `{row['warmup_iterations']}` / `{row['measured_iterations']}`",
            f"- Sequential mean: `{row['sequential_mean_ms']} ms`",
            f"- Parallel mean: `{row['parallel_mean_ms']} ms`",
            f"- Speedup: `{row['speedup']}×`",
            f"- Maximum numerical error: `{row['max_absolute_error']}`",
            f"- Validated CSV records: `{report['records']}`",
        ]
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        lines += ["<strong>Benchmark validation: FAIL / unavailable</strong>", f"- Reason: `{exc}`"]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("a", encoding="utf-8") as stream:
            stream.write("\n".join(lines) + "\n")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
