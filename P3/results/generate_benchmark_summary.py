#!/usr/bin/env python3
"""Generate a RUN_ID-bound QFLPN P3 benchmark Markdown report.

The same generator supports two output modes:

1. Run-specific report:
   --output P3/results/raw/<RUN_ID>/benchmark-report.md
   --overwrite --strict-output

2. GitHub Actions step summary:
   --output "$GITHUB_STEP_SUMMARY"
   (default append behavior)

A strict run-specific invocation never writes a failure document that could
be mistaken for a valid benchmark report.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import tempfile
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
    """Convert a value to a finite floating-point number."""

    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SummaryError(f"{name} is not numeric") from exc

    if not math.isfinite(result):
        raise SummaryError(f"{name} is not finite")

    return result


def require_regular_file(path: Path, description: str) -> None:
    """Reject missing files, directories, and symlinks."""

    if path.is_symlink():
        raise SummaryError(f"{description} must not be a symlink: {path}")

    if not path.is_file():
        raise SummaryError(f"{description} is missing or not a regular file: {path}")


def load_matching_csv_row(
    csv_path: Path,
    run_id: str,
) -> dict[str, str]:
    """Load exactly one canonical CSV row for the requested RUN_ID."""

    require_regular_file(csv_path, "benchmark CSV")

    try:
        with csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
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
                row
                for row in reader
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
    """Load and validate the benchmark validation JSON."""

    require_regular_file(report_path, "benchmark validation report")

    try:
        report = json.loads(
            report_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SummaryError(
            f"cannot read validation JSON: {exc}"
        ) from exc

    if not isinstance(report, dict):
        raise SummaryError("validation report must be a JSON object")

    if report.get("schema") != "qflpn-benchmark-v2":
        raise SummaryError(
            "validation report has an unsupported schema"
        )

    if report.get("validation") != "PASS":
        raise SummaryError(
            "benchmark validation report is not PASS"
        )

    if report.get("all_records_valid") is not True:
        raise SummaryError(
            "validation report does not confirm all records valid"
        )

    records = report.get("records")

    if (
        not isinstance(records, int)
        or isinstance(records, bool)
        or records < 1
    ):
        raise SummaryError(
            "validation report has an invalid record count"
        )

    latest = report.get("latest_record")

    if not isinstance(latest, dict):
        raise SummaryError(
            "validation report has no latest_record object"
        )

    return report


def compare_evidence(
    row: dict[str, str],
    report: dict[str, Any],
    expected_run_id: str | None,
) -> dict[str, Any]:
    """Cross-check the CSV row and validation JSON for one RUN_ID."""

    latest = report["latest_record"]
    csv_run_id = row["run_id"]

    if not isinstance(csv_run_id, str) or not csv_run_id:
        raise SummaryError("CSV row has an empty run_id")

    if expected_run_id and csv_run_id != expected_run_id:
        raise SummaryError(
            f"CSV run_id mismatch: expected {expected_run_id}, "
            f"got {csv_run_id}"
        )

    if latest.get("run_id") != csv_run_id:
        raise SummaryError(
            "CSV and JSON report run_id values do not match"
        )

    comparisons = {
        "dimension": int(row["dimension"]),
        "nnz": int(row["non_zero_count"]),
    }

    for field, expected in comparisons.items():
        if latest.get(field) != expected:
            csv_key = (
                "non_zero_count"
                if field == "nnz"
                else field
            )
            raise SummaryError(
                f"CSV/JSON mismatch for {field}: "
                f"{row.get(csv_key)} versus {latest.get(field)}"
            )

    csv_values = {
        "speedup": "speedup",
        "sequential_mean_ms": "sequential_mean_ms",
        "parallel_mean_ms": "parallel_mean_ms",
        "max_error": "max_absolute_error",
    }

    for report_key, csv_key in csv_values.items():
        actual = finite_number(row[csv_key], csv_key)
        expected = finite_number(
            latest.get(report_key),
            report_key,
        )

        if not math.isclose(
            actual,
            expected,
            rel_tol=1e-8,
            abs_tol=1e-12,
        ):
            raise SummaryError(
                f"CSV/JSON mismatch for {csv_key}: "
                f"{actual} != {expected}"
            )

    for field in REPORT_NUMERIC_FIELDS:
        if field in latest:
            finite_number(latest[field], field)

    # Ensure the displayed CSV metrics are numeric and finite.
    for field in REQUIRED_CSV_FIELDS:
        if field.endswith("_ms") or field in {
            "speedup",
            "sequential_throughput_states_per_s",
            "parallel_throughput_states_per_s",
            "sequential_expected_error",
            "parallel_expected_error",
            "max_absolute_error",
        }:
            finite_number(row[field], field)

    return latest


def build_summary(
    csv_path: Path,
    report_path: Path,
    expected_run_id: str | None = None,
) -> str:
    """Build Markdown using only evidence belonging to one RUN_ID."""

    report = load_report(report_path)
    latest = report["latest_record"]

    run_id = expected_run_id

    if run_id is None:
        run_id = latest.get("run_id")

    if not isinstance(run_id, str) or not run_id:
        raise SummaryError("cannot determine benchmark run_id")

    if not run_id.isascii():
        raise SummaryError("RUN_ID must contain ASCII characters only")

    if any(
        not (character.isalnum() or character in "._-")
        for character in run_id
    ):
        raise SummaryError("RUN_ID contains unsupported characters")

    row = load_matching_csv_row(csv_path, run_id)
    latest = compare_evidence(
        row,
        report,
        expected_run_id=run_id,
    )

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
        (
            "- Sequential oracle error: "
            f"`{row['sequential_expected_error']}`"
        ),
        (
            "- Parallel oracle error: "
            f"`{row['parallel_expected_error']}`"
        ),
        (
            "- Maximum absolute error: "
            f"`{row['max_absolute_error']}`"
        ),
        f"- JSON report: `{report_path.as_posix()}`",
        f"- CSV evidence: `{csv_path.as_posix()}`",
        "",
        (
            "The CSV row and JSON validation report were matched "
            "by the exact RUN_ID."
        ),
        "",
    ])


def write_output(
    output_path: Path,
    content: str,
    overwrite: bool,
) -> None:
    """Write output safely; overwrite mode uses atomic replacement."""

    if output_path.is_symlink():
        raise SummaryError(
            f"output path must not be a symlink: {output_path}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if overwrite:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
            text=True,
        )

        temporary_path = Path(temporary_name)

        try:
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
                newline="\n",
            ) as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(temporary_path, output_path)

        except Exception:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    else:
        with output_path.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize matching QFLPN P3 benchmark evidence."
        )
    )

    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--report",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    parser.add_argument(
        "--run-id",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Atomically replace the output file instead of appending."
        ),
    )

    parser.add_argument(
        "--strict-output",
        action="store_true",
        help=(
            "Do not write a failure Markdown document when validation fails."
        ),
    )

    args = parser.parse_args()

    try:
        summary = build_summary(
            args.csv,
            args.report,
            expected_run_id=args.run_id,
        )

        if args.output:
            write_output(
                args.output,
                summary,
                overwrite=args.overwrite,
            )
        else:
            print(summary, end="")

    except (SummaryError, OSError, ValueError) as exc:
        failure = "\n".join([
            "## QFLPN P3 benchmark summary",
            "",
            "- Validation: **FAIL**",
            f"- Reason: {exc}",
            "",
        ])

        print(f"[FAIL] {exc}", file=sys.stderr)

        if args.output and not args.strict_output:
            try:
                write_output(
                    args.output,
                    failure,
                    overwrite=args.overwrite,
                )
            except OSError as output_error:
                print(
                    f"[FAIL] Cannot write failure summary: {output_error}",
                    file=sys.stderr,
                )

        elif not args.output and not args.strict_output:
            print(failure, end="")

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
