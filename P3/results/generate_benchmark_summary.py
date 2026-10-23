#!/usr/bin/env python3
"""Create a CI summary from matching QFLPN benchmark CSV and JSON evidence."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

REQUIRED_CSV_FIELDS = {
    "timestamp",
    "run_id",
    "benchmark_id",
    "dimension",
    "non_zero_count",
    "warmup_iterations",
    "measured_iterations",
    "sequential_mean_ms",
    "sequential_median_ms",
    "sequential_stddev_ms",
    "parallel_mean_ms",
    "parallel_median_ms",
    "parallel_stddev_ms",
    "speedup",
    "sequential_throughput_states_per_s",
    "parallel_throughput_states_per_s",
    "sequential_expected_error",
    "parallel_expected_error",
    "max_absolute_error",
}

REPORT_NUMERIC_FIELDS = (
    "sequential_mean_ms",
    "sequential_median_ms",
    "sequential_stddev_ms",
    "parallel_mean_ms",
    "parallel_median_ms",
    "parallel_stddev_ms",
    "speedup",
    "sequential_throughput_states_per_s",
    "parallel_throughput_states_per_s",
    "sequential_oracle_error",
    "parallel_oracle_error",
    "max_absolute_error",
)


class SummaryError(ValueError):
    """Raised when benchmark evidence cannot be safely summarized."""


def finite_number(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SummaryError(f"{name} is not numeric") from exc

    if not math.isfinite(result):
        raise SummaryError(f"{name} is not finite")

    return result


def load_matching_csv_row(csv_path: Path, run_id: str) -> dict[str, str]:
    if not csv_path.is_file():
        raise SummaryError(f"benchmark CSV is missing: {csv_path}")

    try:
        with csv_path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as stream:
            reader = csv.DictReader(stream, strict=True)

            if reader.fieldnames is None:
                raise SummaryError("benchmark CSV has no header")

            missing = REQUIRED_CSV_FIELDS - set(reader.fieldnames)
            if missing:
                raise SummaryError(
                    "benchmark CSV is missing columns: "
                    + ", ".join(sorted(missing))
                )

            matches = [
                row for row in reader
                if row.get("run_id") == run_id
            ]
    except (OSError, UnicodeError, csv.Error) as exc:
        raise SummaryError(f"cannot read benchmark CSV: {exc}") from exc

    if len(matches) != 1:
        raise SummaryError(
            f"expected exactly one CSV row for run_id={run_id}; "
            f"found {len(matches)}"
        )

    return matches[0]


def load_report(report_path: Path) -> dict[str, Any]:
    if not report_path.is_file():
        raise SummaryError(f"benchmark validation report is missing: {report_path}")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SummaryError(f"cannot read validation JSON: {exc}") from exc

    if not isinstance(report, dict):
        raise SummaryError("validation report must be a JSON object")

    if report.get("schema") != "qflpn-benchmark-v2":
        raise SummaryError("validation report has an unsupported schema")

    if report.get("validation") != "PASS":
        raise SummaryError("benchmark validation report is not PASS")

    if report.get("all_records_valid") is not True:
        raise SummaryError("validation report does not confirm all records valid")

    if not isinstance(report.get("records"), int) or report["records"] < 1:
        raise SummaryError("validation report has an invalid record count")

    latest = report.get("latest_record")
    if not isinstance(latest, dict):
        raise SummaryError("validation report has no latest_record object")

    return report


def compare_evidence(
    row: dict[str, str],
    report: dict[str, Any],
    expected_run_id: str | None,
) -> dict[str, Any]:
    latest = report["latest_record"]
    csv_run_id = row["run_id"]

    if expected_run_id and csv_run_id != expected_run_id:
        raise SummaryError(
            f"CSV run_id mismatch: expected {expected_run_id}, got {csv_run_id}"
        )

    if latest.get("run_id") != csv_run_id:
        raise SummaryError("CSV and JSON report run_id values do not match")

    comparisons = {
        "dimension": int(row["dimension"]),
        "nnz": int(row["non_zero_count"]),
    }

    for field, expected in comparisons.items():
        if latest.get(field) != expected:
            raise SummaryError(
                f"CSV/JSON mismatch for {field}: "
                f"{row.get(field if field != 'nnz' else 'non_zero_count')} "
                f"versus {latest.get(field)}"
            )

    csv_values = {
        "speedup": "speedup",
        "sequential_mean_ms": "sequential_mean_ms",
        "parallel_mean_ms": "parallel_mean_ms",
        "max_error": "max_absolute_error",
    }

    for report_key, csv_key in csv_values.items():
        actual = finite_number(row[csv_key], csv_key)
        expected = finite_number(latest[report_key], report_key)
        if not math.isclose(actual, expected, rel_tol=1e-8, abs_tol=1e-12):
            raise SummaryError(
                f"CSV/JSON mismatch for {csv_key}: {actual} != {expected}"
            )

    for field in REPORT_NUMERIC_FIELDS:
        if field in latest:
            finite_number(latest[field], field)

    return latest


def build_summary(
    csv_path: Path,
    report_path: Path,
    expected_run_id: str | None = None,
) -> str:
    report = load_report(report_path)
    run_id = expected_run_id

    if run_id is None:
        latest = report.get("latest_record", {})
        run_id = latest.get("run_id")

    if not isinstance(run_id, str) or not run_id:
        raise SummaryError("cannot determine benchmark run_id")

    row = load_matching_csv_row(csv_path, run_id)
    latest = compare_evidence(row, report, expected_run_id)

    return "\n".join([
        "## QFLPN P3 benchmark summary",
        "",
        "- Validation: **PASS**",
        f"- Run ID: `{run_id}`",
        f"- Schema: `{report['schema']}`",
        f"- Valid CSV records: {report['records']}",
        f"- Dimension: {row['dimension']}",
        f"- Non-zero values: {row['non_zero_count']}",
        f"- Warm-up iterations: {row['warmup_iterations']}",
        f"- Measured iterations: {row['measured_iterations']}",
        "",
        "| Metric | Sequential | Parallel |",
        "|---|---:|---:|",
        (
            "| Mean (ms) | "
            f"{float(row['sequential_mean_ms']):.6f} | "
            f"{float(row['parallel_mean_ms']):.6f} |"
        ),
        (
            "| Median (ms) | "
            f"{float(row['sequential_median_ms']):.6f} | "
            f"{float(row['parallel_median_ms']):.6f} |"
        ),
        (
            "| Std. dev. (ms) | "
            f"{float(row['sequential_stddev_ms']):.6f} | "
            f"{float(row['parallel_stddev_ms']):.6f} |"
        ),
        (
            "| Throughput (states/s) | "
            f"{float(row['sequential_throughput_states_per_s']):.3f} | "
            f"{float(row['parallel_throughput_states_per_s']):.3f} |"
        ),
        "",
        f"- Speedup: **{float(row['speedup']):.6f}×**",
        f"- Sequential oracle error: `{row['sequential_expected_error']}`",
        f"- Parallel oracle error: `{row['parallel_expected_error']}`",
        f"- Maximum absolute error: `{row['max_absolute_error']}`",
        f"- JSON report: `{report_path.as_posix()}`",
        f"- CSV evidence: `{csv_path.as_posix()}`",
        "",
        "The CSV row and JSON validation report were matched by run ID.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize matching QFLPN P3 benchmark evidence."
    )
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-id")
    args = parser.parse_args()

    try:
        summary = build_summary(
            args.csv,
            args.report,
            expected_run_id=args.run_id,
        )
    except (SummaryError, OSError, ValueError) as exc:
        summary = "\n".join([
            "## QFLPN P3 benchmark summary",
            "",
            "- Validation: **FAIL**",
            f"- Reason: {exc}",
            "",
        ])
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("a", encoding="utf-8") as stream:
                stream.write(summary)
        else:
            print(summary, end="")
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("a", encoding="utf-8") as stream:
            stream.write(summary)
    else:
        print(summary, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
