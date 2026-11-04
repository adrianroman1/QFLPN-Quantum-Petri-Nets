#!/usr/bin/env python3
"""Generate a RUN_ID-bound QFLPN P3 benchmark Markdown report.

The generator supports:
1. A run-specific report, written atomically with --overwrite --strict-output.
2. A GitHub Actions step summary, appended to GITHUB_STEP_SUMMARY.

The canonical repository report
P3/results/raw/benchmark-report.md is immutable from this generator.
It is an evidence input/reference, never a generator output target.

Only canonical timed benchmark dimensions are accepted:
1,000,000; 10,000,000; 70,000,000; 100,000,000.

The dimension-12 correctness fixture is not a timed benchmark.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_REPORT_PATH = (
    REPOSITORY_ROOT
    / "P3"
    / "results"
    / "raw"
    / "benchmark-report.md"
)


CANONICAL_BENCHMARKS = {
    12: {
        "benchmark_id": "QFLPN-12",
        "role": "CORRECTNESS_FIXTURE",
    },
    1_000_000: {
        "benchmark_id": "QFLPN-1M",
        "role": "TIMED_BENCHMARK",
    },
    10_000_000: {
        "benchmark_id": "QFLPN-10M",
        "role": "TIMED_BENCHMARK",
    },
    70_000_000: {
        "benchmark_id": "QFLPN-70M",
        "role": "TIMED_BENCHMARK",
    },
    100_000_000: {
        "benchmark_id": "QFLPN-100M",
        "role": "TIMED_BENCHMARK",
    },
}

TIMED_BENCHMARK_DIMENSIONS = frozenset({
    1_000_000,
    10_000_000,
    70_000_000,
    100_000_000,
})

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
    "max_error",
)


class SummaryError(ValueError):
    """Raised when benchmark evidence cannot be safely summarized."""


def canonical_report_path() -> Path:
    """Return the canonical report path resolved against the repository."""

    return CANONICAL_REPORT_PATH.resolve(strict=False)


def reject_canonical_report_output(output_path: Path) -> None:
    """Prevent every supported path alias from targeting the canonical report.

    The check covers:
    - the canonical relative path;
    - an absolute path to the canonical report;
    - paths passing through symlinked parent directories;
    - an existing hard link to the canonical report.

    This guard runs before creating parent directories or opening output files.
    """

    canonical = canonical_report_path()
    candidate = output_path.resolve(strict=False)

    if candidate == canonical:
        raise SummaryError(
            "refusing to write the canonical benchmark report: "
            f"{canonical}. This file is an immutable evidence reference."
        )

    # resolve() handles symbolic-link aliases. samefile() additionally
    # protects an existing hard link that resolves to a different pathname.
    try:
        if (
            output_path.exists()
            and canonical.exists()
            and os.path.samefile(output_path, canonical)
        ):
            raise SummaryError(
                "refusing to write an output path that is a hard link "
                "to the canonical benchmark report: "
                f"{canonical}"
            )
    except OSError as exc:
        raise SummaryError(
            "cannot safely verify output path against the canonical "
            f"benchmark report: {exc}"
        ) from exc


def finite_number(value: Any, name: str) -> float:
    """Convert a value to a finite floating-point number."""

    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SummaryError(f"{name} is not numeric") from exc

    if not math.isfinite(result):
        raise SummaryError(f"{name} is not finite")

    return result


def strict_integer(value: Any, name: str) -> int:
    """Parse a non-negative ASCII integer without accepting decimal forms."""

    if not isinstance(value, str):
        raise SummaryError(f"{name} must be an integer string")

    normalized = value.strip()

    if not re.fullmatch(r"[0-9]+", normalized):
        raise SummaryError(f"{name} must be a non-negative integer")

    try:
        return int(normalized)
    except ValueError as exc:
        raise SummaryError(f"{name} is outside the supported range") from exc


def require_regular_file(path: Path, description: str) -> None:
    """Reject missing files, directories, and symlinks."""

    if path.is_symlink():
        raise SummaryError(
            f"{description} must not be a symlink: {path}"
        )

    if not path.is_file():
        raise SummaryError(
            f"{description} is missing or not a regular file: {path}"
        )


def validate_run_id(run_id: Any) -> str:
    """Validate the run identifier used to join evidence."""

    if not isinstance(run_id, str) or not run_id:
        raise SummaryError("RUN_ID must be a non-empty string")

    if not run_id.isascii():
        raise SummaryError("RUN_ID must contain ASCII characters only")

    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise SummaryError("RUN_ID contains unsupported characters")

    return run_id


def validate_timed_benchmark_identity(
    row: dict[str, str],
) -> tuple[int, str, int]:
    """Validate dimension, canonical ID, and NNZ for one timed CSV row."""

    dimension = strict_integer(
        row.get("dimension"),
        "dimension",
    )

    if dimension not in CANONICAL_BENCHMARKS:
        raise SummaryError(
            f"unsupported benchmark dimension: {dimension}"
        )

    catalog_entry = CANONICAL_BENCHMARKS[dimension]
    benchmark_id = row.get("benchmark_id")

    if benchmark_id != catalog_entry["benchmark_id"]:
        raise SummaryError(
            "benchmark_id does not match the canonical catalog: "
            f"dimension={dimension}, expected="
            f"{catalog_entry['benchmark_id']}, got={benchmark_id!r}"
        )

    if dimension not in TIMED_BENCHMARK_DIMENSIONS:
        raise SummaryError(
            f"dimension {dimension} is a correctness fixture, "
            "not a timed benchmark"
        )

    nnz = strict_integer(
        row.get("non_zero_count"),
        "non_zero_count",
    )

    if nnz != 2 * dimension:
        raise SummaryError(
            "non_zero_count does not match the P3 benchmark contract: "
            f"expected {2 * dimension}, got {nnz}"
        )

    return dimension, benchmark_id, nnz


def load_matching_csv_row(
    csv_path: Path,
    run_id: str,
) -> dict[str, str]:
    """Load exactly one canonical timed CSV row for the requested RUN_ID."""

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

            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise SummaryError(
                    "benchmark CSV contains duplicate column names"
                )

            missing = REQUIRED_CSV_FIELDS - set(reader.fieldnames)

            if missing:
                raise SummaryError(
                    "benchmark CSV is missing columns: "
                    + ", ".join(sorted(missing))
                )

            matches: list[dict[str, str]] = []

            for row in reader:
                if None in row:
                    raise SummaryError(
                        "benchmark CSV contains a row with extra fields"
                    )

                if any(value is None for value in row.values()):
                    raise SummaryError(
                        "benchmark CSV contains a row with missing fields"
                    )

                if row.get("run_id") == run_id:
                    matches.append(row)

    except SummaryError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise SummaryError(
            f"cannot read benchmark CSV: {exc}"
        ) from exc

    if len(matches) != 1:
        raise SummaryError(
            f"expected exactly one CSV row for run_id={run_id}; "
            f"found {len(matches)}"
        )

    validate_timed_benchmark_identity(matches[0])

    return matches[0]


def load_report(report_path: Path) -> dict[str, Any]:
    """Load and validate the benchmark validation JSON."""

    require_regular_file(
        report_path,
        "benchmark validation report",
    )

    try:
        report = json.loads(
            report_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SummaryError(
            f"cannot read validation JSON: {exc}"
        ) from exc

    if not isinstance(report, dict):
        raise SummaryError(
            "validation report must be a JSON object"
        )

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

    csv_run_id = validate_run_id(row.get("run_id"))

    if expected_run_id is not None:
        expected_run_id = validate_run_id(expected_run_id)

        if csv_run_id != expected_run_id:
            raise SummaryError(
                f"CSV run_id mismatch: expected {expected_run_id}, "
                f"got {csv_run_id}"
            )

    if latest.get("run_id") != csv_run_id:
        raise SummaryError(
            "CSV and JSON report run_id values do not match"
        )

    dimension, benchmark_id, nnz = (
        validate_timed_benchmark_identity(row)
    )

    report_dimension = latest.get("dimension")
    report_nnz = latest.get("nnz")

    if report_dimension != dimension:
        raise SummaryError(
            "CSV/JSON mismatch for dimension: "
            f"{dimension} versus {report_dimension!r}"
        )

    if report_nnz != nnz:
        raise SummaryError(
            "CSV/JSON mismatch for nnz: "
            f"{nnz} versus {report_nnz!r}"
        )

    report_benchmark_id = latest.get("benchmark_id")

    if (
        report_benchmark_id is not None
        and report_benchmark_id != benchmark_id
    ):
        raise SummaryError(
            "CSV/JSON mismatch for benchmark_id: "
            f"{benchmark_id} versus {report_benchmark_id!r}"
        )

    comparisons = {
        "speedup": "speedup",
        "sequential_mean_ms": "sequential_mean_ms",
        "parallel_mean_ms": "parallel_mean_ms",
        "max_error": "max_absolute_error",
    }

    for report_key, csv_key in comparisons.items():
        actual = finite_number(
            row[csv_key],
            csv_key,
        )

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

    run_id = validate_run_id(run_id)

    row = load_matching_csv_row(
        csv_path,
        run_id,
    )

    compare_evidence(
        row,
        report,
        expected_run_id=run_id,
    )

    dimension, benchmark_id, nnz = (
        validate_timed_benchmark_identity(row)
    )

    return "\n".join([
        "## QFLPN P3 benchmark summary",
        "",
        "- Validation: **PASS**",
        f"- Run ID: `{run_id}`",
        f"- Schema: `{report['schema']}`",
        f"- Valid CSV records: {report['records']}",
        f"- Benchmark ID: `{benchmark_id}`",
        f"- Dimension: {dimension}",
        f"- Non-zero values: {nnz}",
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
    """Write output safely; never target the canonical report."""

    reject_canonical_report_output(output_path)

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

            os.replace(
                temporary_path,
                output_path,
            )

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

        print(
            f"[FAIL] {exc}",
            file=sys.stderr,
        )

        if args.output and not args.strict_output:
            try:
                write_output(
                    args.output,
                    failure,
                    overwrite=args.overwrite,
                )
            except (OSError, SummaryError) as output_error:
                print(
                    f"[FAIL] Cannot write failure summary: {output_error}",
                    file=sys.stderr,
                )

        elif not args.output and not args.strict_output:
            print(
                failure,
                end="",
            )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
