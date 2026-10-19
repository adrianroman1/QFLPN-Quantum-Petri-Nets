#!/usr/bin/env python3

"""
Independent validator for P3 benchmark CSV results.

Checks:
- CSV schema;
- timestamp;
- benchmark dimension;
- NNZ = 2N;
- benchmark configuration;
- finite positive execution times;
- speedup consistency;
- throughput consistency;
- numerical errors;
- execution environment metadata.

The validator does not modify the CSV file.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys

from datetime import datetime, timezone
from pathlib import Path


EXPECTED_HEADER = [
    "timestamp",
    "benchmark_id",
    "dimension",
    "non_zero_count",
    "parallelism",
    "threshold",
    "warmup_iterations",
    "measured_iterations",
    "sequential_ms",
    "parallel_ms",
    "speedup",
    "sequential_throughput_states_per_s",
    "parallel_throughput_states_per_s",
    "sequential_expected_error",
    "parallel_expected_error",
    "max_absolute_error",
    "setup_time_ms",
    "cpu",
    "available_memory_bytes",
    "java_version",
    "operating_system",
    "notes",
]

DEFAULT_CSV = (
    Path(__file__).resolve().parents[1]
    / "benchmarks"
    / "benchmark_results.csv"
)

EPSILON = 1.0e-12
REL_TOL = 1.0e-8
ABS_TOL = 1.0e-12


class ValidationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def parse_int(row: dict, key: str) -> int:
    try:
        return int(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(
            f"Invalid integer field: {key}"
        ) from exc


def parse_float(row: dict, key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(
            f"Invalid numeric field: {key}"
        ) from exc

    require(
        math.isfinite(value),
        f"{key} must be finite"
    )

    return value


def close_enough(
    actual: float,
    expected: float,
    field: str,
) -> None:
    require(
        math.isclose(
            actual,
            expected,
            rel_tol=REL_TOL,
            abs_tol=ABS_TOL,
        ),
        (
            f"{field} mismatch: "
            f"CSV={actual:.16g}, "
            f"recomputed={expected:.16g}"
        ),
    )


def validate_timestamp(value: str) -> None:
    require(
        bool(value.strip()),
        "timestamp must not be empty"
    )

    normalized = value.strip().replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(
            "timestamp must be ISO-8601"
        ) from exc

    require(
        parsed.tzinfo is not None,
        "timestamp must include timezone information"
    )


def load_latest_row(path: Path) -> dict:
    require(
        path.is_file(),
        f"CSV file does not exist: {path}"
    )

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        require(
            reader.fieldnames == EXPECTED_HEADER,
            "CSV header does not match the expected schema"
        )

        rows = list(reader)

    require(
        len(rows) > 0,
        "CSV contains no benchmark data rows"
    )

    row = rows[-1]

    require(
        None not in row,
        "CSV row contains unexpected extra columns"
    )

    require(
        all(value is not None for value in row.values()),
        "CSV row contains missing fields"
    )

    return row


def validate(args: argparse.Namespace) -> dict:
    row = load_latest_row(args.csv)

    validate_timestamp(row["timestamp"])

    dimension = parse_int(row, "dimension")
    nnz = parse_int(row, "non_zero_count")
    parallelism = parse_int(row, "parallelism")
    threshold = parse_int(row, "threshold")
    warmup = parse_int(row, "warmup_iterations")
    iterations = parse_int(row, "measured_iterations")

    sequential_ms = parse_float(row, "sequential_ms")
    parallel_ms = parse_float(row, "parallel_ms")
    stored_speedup = parse_float(row, "speedup")

    sequential_throughput = parse_float(
        row,
        "sequential_throughput_states_per_s",
    )

    parallel_throughput = parse_float(
        row,
        "parallel_throughput_states_per_s",
    )

    sequential_error = parse_float(
        row,
        "sequential_expected_error",
    )

    parallel_error = parse_float(
        row,
        "parallel_expected_error",
    )

    maximum_difference = parse_float(
        row,
        "max_absolute_error",
    )

    setup_time_ms = parse_float(
        row,
        "setup_time_ms",
    )

    available_memory = parse_int(
        row,
        "available_memory_bytes",
    )

    require(
        dimension == args.expected_n,
        (
            f"dimension mismatch: "
            f"expected {args.expected_n}, got {dimension}"
        ),
    )

    require(
        nnz == 2 * dimension,
        f"NNZ mismatch: expected {2 * dimension}, got {nnz}"
    )

    require(
        parallelism == args.parallelism,
        "parallelism does not match requested configuration"
    )

    require(
        threshold == args.threshold,
        "threshold does not match requested configuration"
    )

    require(
        warmup == args.warmup,
        "warmup iteration count does not match configuration"
    )

    require(
        iterations == args.iterations,
        "measured iteration count does not match configuration"
    )

    require(
        sequential_ms > 0.0,
        "sequential_ms must be positive"
    )

    require(
        parallel_ms > 0.0,
        "parallel_ms must be positive"
    )

    require(
        stored_speedup > 0.0,
        "speedup must be positive"
    )

    require(
        setup_time_ms >= 0.0,
        "setup_time_ms must not be negative"
    )

    require(
        available_memory >= 0,
        "available_memory_bytes must not be negative"
    )

    require(
        row["benchmark_id"].strip() != "",
        "benchmark_id must not be empty"
    )

    require(
        row["cpu"].strip() != "",
        "cpu metadata must not be empty"
    )

    require(
        row["java_version"].strip() != "",
        "java_version must not be empty"
    )

    require(
        row["operating_system"].strip() != "",
        "operating_system must not be empty"
    )

    recomputed_speedup = sequential_ms / parallel_ms

    close_enough(
        stored_speedup,
        recomputed_speedup,
        "speedup",
    )

    expected_sequential_throughput = (
        dimension / (sequential_ms / 1000.0)
    )

    expected_parallel_throughput = (
        dimension / (parallel_ms / 1000.0)
    )

    close_enough(
        sequential_throughput,
        expected_sequential_throughput,
        "sequential throughput",
    )

    close_enough(
        parallel_throughput,
        expected_parallel_throughput,
        "parallel throughput",
    )

    require(
        sequential_error <= EPSILON,
        "sequential expected error exceeds tolerance"
    )

    require(
        parallel_error <= EPSILON,
        "parallel expected error exceeds tolerance"
    )

    require(
        maximum_difference <= EPSILON,
        "sequential/parallel difference exceeds tolerance"
    )

    reduction = 1.0 - (
        parallel_ms / sequential_ms
    )

    return {
        "validation": "PASS",
        "timestamp": row["timestamp"],
        "benchmark_id": row["benchmark_id"],
        "dimension": dimension,
        "nnz": nnz,
        "warmup_iterations": warmup,
        "measured_iterations": iterations,
        "parallelism": parallelism,
        "threshold": threshold,
        "sequential_ms": sequential_ms,
        "parallel_ms": parallel_ms,
        "speedup_csv": stored_speedup,
        "speedup_recomputed": recomputed_speedup,
        "time_reduction": reduction,
        "time_reduction_percent": reduction * 100.0,
        "sequential_expected_error": sequential_error,
        "parallel_expected_error": parallel_error,
        "max_absolute_error": maximum_difference,
        "csv": str(args.csv),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate P3 benchmark CSV results."
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help="Benchmark CSV path",
    )

    parser.add_argument(
        "--expected-n",
        type=int,
        default=1_000_000,
    )

    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--threshold",
        type=int,
        default=4096,
    )

    parser.add_argument(
        "--parallelism",
        type=int,
        default=2,
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = validate(args)

    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "validation": "FAIL",
                    "error": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
