#!/usr/bin/env python3
"""Fail-closed validator for the canonical QFLPN benchmark V2 CSV."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


HEADER = [
    "timestamp",
    "run_id",
    "benchmark_id",
    "dimension",
    "non_zero_count",
    "parallelism",
    "threshold",
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
    "setup_time_ms",
    "cpu",
    "max_jvm_memory_bytes",
    "free_jvm_heap_bytes",
    "java_version",
    "operating_system",
    "notes",
]


# Canonical, closed benchmark catalog.
#
# QFLPN-12 is a correctness fixture, not a timed benchmark.
# Only the other four dimensions are eligible for timed CSV records.
#
# This mapping must remain aligned with P3/code/BenchmarkScale.java.
CANONICAL_BENCHMARKS: dict[int, str] = {
    12: "QFLPN-12",
    1_000_000: "QFLPN-1M",
    10_000_000: "QFLPN-10M",
    70_000_000: "QFLPN-70M",
    100_000_000: "QFLPN-100M",
}

TIMED_BENCHMARK_DIMENSIONS = frozenset({
    1_000_000,
    10_000_000,
    70_000_000,
    100_000_000,
})

CORRECTNESS_FIXTURE_DIMENSIONS = frozenset({
    12,
})

EPSILON = 1e-12
REL_TOL = 1e-8
ABS_TOL = 1e-12

INTEGER_RE = re.compile(r"^(0|[1-9][0-9]*)$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class ValidationError(ValueError):
    """Raised when benchmark evidence violates the V2 contract."""


def need(condition: bool, message: str) -> None:
    """Raise ValidationError when a validation condition is false."""

    if not condition:
        raise ValidationError(message)


def text_value(row: dict[str, str], key: str) -> str:
    """Return a required non-empty text field."""

    value = row.get(key)

    need(value is not None, f"{key} is missing")
    need(value.strip() != "", f"{key} is empty")

    return value


def integer(row: dict[str, str], key: str) -> int:
    """Parse a strict nonnegative integer field."""

    value = row.get(key)

    need(value is not None, f"{key} is missing")
    need(
        bool(INTEGER_RE.fullmatch(value)),
        f"{key} must be a nonnegative integer",
    )

    return int(value)


def number(row: dict[str, str], key: str) -> float:
    """Parse a finite numeric field."""

    value = row.get(key)

    need(
        value is not None and value.strip() != "",
        f"{key} is missing",
    )

    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"{key} must be numeric") from exc

    need(math.isfinite(result), f"{key} must be finite")

    return result


def close(actual: float, expected: float, field: str) -> None:
    """Compare floating-point values using the V2 tolerances."""

    need(
        math.isclose(
            actual,
            expected,
            rel_tol=REL_TOL,
            abs_tol=ABS_TOL,
        ),
        f"{field} mismatch: {actual} != {expected}",
    )


def expected_benchmark_id(dimension: int) -> str:
    """
    Resolve a dimension through the closed canonical catalog.

    There is deliberately no generic identifier fallback.

    Unknown dimensions, including 30_000_000, are rejected.
    """

    if isinstance(dimension, bool) or not isinstance(dimension, int):
        raise ValidationError(
            "dimension must be an integer from the canonical catalog"
        )

    try:
        return CANONICAL_BENCHMARKS[dimension]
    except KeyError as exc:
        supported = ", ".join(
            str(value)
            for value in CANONICAL_BENCHMARKS
        )

        raise ValidationError(
            f"unsupported benchmark dimension {dimension}; "
            f"canonical dimensions are: {supported}"
        ) from exc


def validate_row(
    row: dict[str, str],
    index: int,
) -> dict[str, Any]:
    """Validate one V2 CSV record against the canonical contract."""

    prefix = f"row {index}: "

    try:
        need(
            None not in row,
            "CSV row has more fields than the header",
        )

        need(
            all(value is not None for value in row.values()),
            "CSV row has missing fields",
        )

        stamp = text_value(row, "timestamp")

        try:
            parsed = datetime.fromisoformat(
                stamp.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValidationError(
                "timestamp is not valid ISO-8601"
            ) from exc

        need(
            parsed.tzinfo is not None
            and parsed.utcoffset() is not None,
            "timestamp must include a timezone",
        )

        run_id = text_value(row, "run_id")

        need(
            bool(RUN_ID_RE.fullmatch(run_id)),
            "run_id contains unsupported characters",
        )

        benchmark_id = text_value(row, "benchmark_id")

        dimension = integer(row, "dimension")
        nnz = integer(row, "non_zero_count")
        parallelism = integer(row, "parallelism")
        threshold = integer(row, "threshold")
        warmup = integer(row, "warmup_iterations")
        iterations = integer(row, "measured_iterations")

        need(
            dimension > 0,
            "dimension must be positive",
        )

        canonical_id = expected_benchmark_id(dimension)

        need(
            benchmark_id == canonical_id,
            (
                "benchmark_id does not match the canonical catalog: "
                f"N={dimension} requires {canonical_id}, "
                f"got {benchmark_id}"
            ),
        )

        need(
            dimension in TIMED_BENCHMARK_DIMENSIONS,
            (
                f"N={dimension} is a correctness fixture, "
                "not an eligible timed benchmark dimension"
            ),
        )

        need(
            nnz == 2 * dimension,
            (
                "non_zero_count must equal 2 * dimension "
                "for the P3 benchmark workload"
            ),
        )

        need(
            parallelism > 0,
            "parallelism must be positive",
        )

        need(
            threshold > 0,
            "threshold must be positive",
        )

        need(
            iterations > 0,
            "measured_iterations must be positive",
        )

        seq_mean = number(row, "sequential_mean_ms")
        seq_median = number(row, "sequential_median_ms")
        seq_std = number(row, "sequential_stddev_ms")

        par_mean = number(row, "parallel_mean_ms")
        par_median = number(row, "parallel_median_ms")
        par_std = number(row, "parallel_stddev_ms")

        speedup = number(row, "speedup")

        seq_throughput = number(
            row,
            "sequential_throughput_states_per_s",
        )

        par_throughput = number(
            row,
            "parallel_throughput_states_per_s",
        )

        seq_error = number(
            row,
            "sequential_expected_error",
        )

        par_error = number(
            row,
            "parallel_expected_error",
        )

        max_error = number(
            row,
            "max_absolute_error",
        )

        setup_ms = number(row, "setup_time_ms")

        need(
            min(
                seq_mean,
                seq_median,
                par_mean,
                par_median,
                speedup,
            ) > 0,
            "means, medians and speedup must be positive",
        )

        need(
            min(
                seq_std,
                par_std,
                seq_error,
                par_error,
                max_error,
                setup_ms,
            ) >= 0,
            (
                "standard deviations, errors and setup time "
                "must be nonnegative"
            ),
        )

        need(
            seq_median > 0 and par_median > 0,
            "medians must be positive",
        )

        need(
            max(seq_error, par_error, max_error) <= EPSILON,
            f"numerical error exceeds tolerance {EPSILON}",
        )

        max_heap = integer(
            row,
            "max_jvm_memory_bytes",
        )

        free_heap = integer(
            row,
            "free_jvm_heap_bytes",
        )

        need(
            max_heap > 0,
            "max_jvm_memory_bytes must be positive",
        )

        need(
            0 <= free_heap <= max_heap,
            "invalid JVM heap measurements",
        )

        for key in (
            "cpu",
            "java_version",
            "operating_system",
        ):
            text_value(row, key)

        need(
            row.get("notes") is not None,
            "notes field is missing",
        )

        close(
            speedup,
            seq_mean / par_mean,
            "speedup",
        )

        close(
            seq_throughput,
            dimension / (seq_mean / 1000.0),
            "sequential throughput",
        )

        close(
            par_throughput,
            dimension / (par_mean / 1000.0),
            "parallel throughput",
        )

        return {
            "row": index,
            "run_id": run_id,
            "benchmark_id": benchmark_id,
            "dimension": dimension,
            "nnz": nnz,
            "speedup": speedup,
            "sequential_mean_ms": seq_mean,
            "parallel_mean_ms": par_mean,
            "max_error": max(
                seq_error,
                par_error,
                max_error,
            ),
        }

    except ValidationError as exc:
        raise ValidationError(prefix + str(exc)) from exc


def validate(
    path: Path,
    expected: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Validate the complete V2 CSV.

    Every historical row must satisfy the canonical catalog.
    Optional expected configuration values are checked against
    every row, preserving the original validator contract.
    """

    path = Path(path)

    need(
        path.is_file(),
        f"CSV file does not exist or is not a regular file: {path}",
    )

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            reader = csv.DictReader(
                stream,
                strict=True,
            )

            need(
                reader.fieldnames == HEADER,
                "CSV V2 header mismatch",
            )

            rows = list(reader)

    except UnicodeError as exc:
        raise ValidationError(
            "CSV is not valid UTF-8"
        ) from exc

    except csv.Error as exc:
        raise ValidationError(
            f"CSV syntax error: {exc}"
        ) from exc

    except OSError:
        raise

    need(
        bool(rows),
        "CSV contains no benchmark data rows",
    )

    checked: list[dict[str, Any]] = []
    seen_run_ids: set[str] = set()

    for index, row in enumerate(rows, start=1):
        result = validate_row(row, index)

        run_id = result["run_id"]

        need(
            run_id not in seen_run_ids,
            f"row {index}: duplicate run_id: {run_id}",
        )

        seen_run_ids.add(run_id)

        if expected:
            for key, value in expected.items():
                actual = integer(row, key)

                need(
                    actual == value,
                    (
                        f"row {index}: {key} expected "
                        f"{value}, got {actual}"
                    ),
                )

        checked.append(result)

    return {
        "schema": "qflpn-benchmark-v2",
        "validation": "PASS",
        "records": len(checked),
        "all_records_valid": True,
        "latest_record": checked[-1],
    }


def main() -> int:
    """Command-line entry point."""

    parser = argparse.ArgumentParser(
        description=(
            "Strictly validate canonical QFLPN benchmark V2 CSV evidence."
        )
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(
            "P3/benchmarks/benchmark_results_v2.csv"
        ),
    )

    parser.add_argument(
        "--report-json",
        type=Path,
    )

    parser.add_argument(
        "--expected-n",
        type=int,
    )

    parser.add_argument(
        "--warmup",
        type=int,
    )

    parser.add_argument(
        "--iterations",
        type=int,
    )

    parser.add_argument(
        "--threshold",
        type=int,
    )

    parser.add_argument(
        "--parallelism",
        type=int,
    )

    args = parser.parse_args()

    expected = {
        key: value
        for key, value in {
            "dimension": args.expected_n,
            "warmup_iterations": args.warmup,
            "measured_iterations": args.iterations,
            "threshold": args.threshold,
            "parallelism": args.parallelism,
        }.items()
        if value is not None
    }

    try:
        result = validate(
            args.csv,
            expected,
        )

        output = (
            json.dumps(
                result,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        )

        if args.report_json:
            args.report_json.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            args.report_json.write_text(
                output,
                encoding="utf-8",
            )

        print(
            output,
            end="",
        )

        return 0

    except (
        ValidationError,
        OSError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "schema": "qflpn-benchmark-v2",
                    "validation": "FAIL",
                    "error": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
