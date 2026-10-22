#!/usr/bin/env python3
"""Fail-closed validator for P3 benchmark CSV evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys

from datetime import datetime
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
    "max_jvm_memory_bytes",
    "free_jvm_heap_bytes",
    "java_version",
    "operating_system",
    "notes",
]

# P3/results/validate_benchmark.py -> repository root / benchmarks
DEFAULT_CSV = (
    Path(__file__).resolve().parents[2]
    / "benchmarks"
    / "benchmark_results.csv"
)

EPSILON = 1.0e-12
REL_TOL = 1.0e-8
ABS_TOL = 1.0e-12


class ValidationError(Exception):
    """Raised when benchmark evidence is invalid."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def parse_int(row: dict, key: str) -> int:
    value = row.get(key, "")

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{key} must be an integer"
        ) from exc


def parse_float(row: dict, key: str) -> float:
    value = row.get(key, "")

    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{key} must be numeric"
        ) from exc

    require(math.isfinite(parsed), f"{key} must be finite")
    return parsed


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
            f"{field} mismatch: CSV={actual:.16g}, "
            f"recomputed={expected:.16g}"
        ),
    )


def expected_benchmark_id(dimension: int) -> str:
    special_ids = {
        12: "QFLPN-12",
        1_000_000: "QFLPN-1M",
        30_000_000: "QFLPN-30M",
    }

    return special_ids.get(
        dimension,
        f"QFLPN-{dimension}",
    )


def validate_timestamp(value: str) -> None:
    require(
        isinstance(value, str) and bool(value.strip()),
        "timestamp must not be empty",
    )

    normalized = value.strip()

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(
            "timestamp must be ISO-8601"
        ) from exc

    require(
        parsed.tzinfo is not None,
        "timestamp must include timezone information",
    )


def load_rows(path: Path) -> list[dict]:
    require(
        path.is_file(),
        f"CSV file does not exist: {path}",
    )

    try:
        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)

            require(
                reader.fieldnames == EXPECTED_HEADER,
                "CSV header does not match the expected 23-column schema",
            )

            rows = list(reader)

    except (OSError, csv.Error) as exc:
        raise ValidationError(
            f"Unable to read benchmark CSV: {exc}"
        ) from exc

    require(
        len(rows) > 0,
        "CSV contains no benchmark data rows",
    )

    for index, row in enumerate(rows, start=1):
        require(
            None not in row,
            f"CSV row {index} contains unexpected extra columns",
        )
        require(
            all(value is not None for value in row.values()),
            f"CSV row {index} contains missing fields",
        )

    return rows


def validate_row(
    row: dict,
    args: argparse.Namespace,
    row_number: int,
) -> dict:
    prefix = f"row {row_number}: "

    try:
        validate_timestamp(row["timestamp"])

        dimension = parse_int(row, "dimension")
        nnz = parse_int(row, "non_zero_count")
        parallelism = parse_int(row, "parallelism")
        threshold = parse_int(row, "threshold")
        warmup = parse_int(row, "warmup_iterations")
        iterations = parse_int(row, "measured_iterations")

        sequential_ms = parse_float(row, "sequential_ms")
        parallel_ms = parse_float(row, "parallel_ms")
        speedup = parse_float(row, "speedup")

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

        max_jvm_memory = parse_int(
            row,
            "max_jvm_memory_bytes",
        )
        free_jvm_heap = parse_int(
            row,
            "free_jvm_heap_bytes",
        )

        require(dimension > 0, "dimension must be positive")
        require(nnz >= 0, "non_zero_count must not be negative")
        require(parallelism > 0, "parallelism must be positive")
        require(threshold > 0, "threshold must be positive")
        require(warmup >= 0, "warmup_iterations must not be negative")
        require(iterations > 0, "measured_iterations must be positive")

        # Current benchmark matrix creates exactly two entries per row.
        require(
            nnz == 2 * dimension,
            f"NNZ mismatch: expected {2 * dimension}, got {nnz}",
        )

        expected_id = expected_benchmark_id(dimension)
        require(
            row["benchmark_id"] == expected_id,
            (
                "benchmark_id mismatch: expected "
                f"{expected_id}, got {row['benchmark_id']!r}"
            ),
        )

        if args.expected_n is not None:
            require(
                dimension == args.expected_n,
                (
                    f"dimension mismatch: expected {args.expected_n}, "
                    f"got {dimension}"
                ),
            )

        if args.parallelism is not None:
            require(
                parallelism == args.parallelism,
                "parallelism does not match requested configuration",
            )

        if args.threshold is not None:
            require(
                threshold == args.threshold,
                "threshold does not match requested configuration",
            )

        if args.warmup is not None:
            require(
                warmup == args.warmup,
                "warmup iteration count does not match configuration",
            )

        if args.iterations is not None:
            require(
                iterations == args.iterations,
                "measured iteration count does not match configuration",
            )

        require(sequential_ms > 0.0, "sequential_ms must be positive")
        require(parallel_ms > 0.0, "parallel_ms must be positive")
        require(speedup > 0.0, "speedup must be positive")
        require(setup_time_ms >= 0.0, "setup_time_ms must not be negative")

        require(
            max_jvm_memory > 0,
            "max_jvm_memory_bytes must be positive",
        )
        require(
            free_jvm_heap >= 0,
            "free_jvm_heap_bytes must not be negative",
        )
        require(
            free_jvm_heap <= max_jvm_memory,
            "free_jvm_heap_bytes cannot exceed max_jvm_memory_bytes",
        )

        require(
            sequential_error >= 0.0,
            "sequential_expected_error must not be negative",
        )
        require(
            parallel_error >= 0.0,
            "parallel_expected_error must not be negative",
        )
        require(
            maximum_difference >= 0.0,
            "max_absolute_error must not be negative",
        )

        require(
            sequential_error <= EPSILON,
            "sequential expected error exceeds tolerance",
        )
        require(
            parallel_error <= EPSILON,
            "parallel expected error exceeds tolerance",
        )
        require(
            maximum_difference <= EPSILON,
            "sequential/parallel difference exceeds tolerance",
        )

        for field in (
            "cpu",
            "java_version",
            "operating_system",
            "notes",
        ):
            require(
                bool(row[field].strip()),
                f"{field} must not be empty",
            )

        recomputed_speedup = sequential_ms / parallel_ms
        close_enough(
            speedup,
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

        return {
            "row": row_number,
            "dimension": dimension,
            "nnz": nnz,
            "speedup": recomputed_speedup,
            "sequential_ms": sequential_ms,
            "parallel_ms": parallel_ms,
            "max_jvm_memory_bytes": max_jvm_memory,
            "free_jvm_heap_bytes": free_jvm_heap,
        }

    except ValidationError as exc:
        raise ValidationError(prefix + str(exc)) from exc


def validate(args: argparse.Namespace) -> dict:
    rows = load_rows(args.csv)

    if args.expected_row_count is not None:
        require(
            len(rows) == args.expected_row_count,
            (
                "CSV record count mismatch: expected "
                f"{args.expected_row_count}, found {len(rows)}"
            ),
        )

    validated = [
        validate_row(row, args, index)
        for index, row in enumerate(rows, start=1)
    ]

    return {
        "validation": "PASS",
        "csv": str(args.csv),
        "csv_total_records": len(validated),
        "validated_records": len(validated),
        "latest_record": validated[-1],
        "all_records_valid": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate P3 benchmark CSV results."
    )

    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--expected-n", type=int, default=None)
    parser.add_argument("--warmup", type=int, default=None)
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--threshold", type=int, default=None)
    parser.add_argument("--parallelism", type=int, default=None)
    parser.add_argument("--expected-row-count", type=int, default=None)
    parser.add_argument("--report-json", type=Path, default=None)

    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        result = validate(args)
        output = json.dumps(
            result,
            indent=2,
            allow_nan=False,
        )

        if args.report_json is not None:
            args.report_json.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            args.report_json.write_text(
                output + "\n",
                encoding="utf-8",
            )

        print(output)
        return 0

    except (ValidationError, OSError) as exc:
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


if __name__ == "__main__":
    raise SystemExit(main())
