#!/usr/bin/env python3
"""Strict validator for the additive QFLPN P3 Benchmark V3 evidence.

V2 is deliberately not imported or modified by this module.

The validator enforces:
- exact V3 CSV header;
- exactly 96 distinct workload/configuration combinations;
- common run_id, workflow_run_id and commit_sha;
- finite and physically valid measurements;
- recomputation of speedup and throughput;
- recomputation of the performance verdict;
- numerical-error limits;
- exact configuration-set equality (not merely row count).

Usage:
    python P3/results/validate_benchmark_v3.py \
        --csv P3/benchmarks/benchmark_results_v3.csv \
        --report-json P3/reports/benchmark-v3-validation.json
"""

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
    "workflow_run_id",
    "commit_sha",
    "benchmark_id",
    "workload_id",
    "matrix_family",
    "distribution",
    "dimension",
    "non_zero_count",
    "nnz_min_per_row",
    "nnz_avg_per_row",
    "nnz_max_per_row",
    "parallelism",
    "threshold_rows",
    "parallel_strategy",
    "split_policy",
    "warmup_iterations",
    "measured_iterations",
    "sequential_mean_ms",
    "sequential_median_ms",
    "sequential_stddev_ms",
    "sequential_min_ms",
    "sequential_max_ms",
    "parallel_mean_ms",
    "parallel_median_ms",
    "parallel_stddev_ms",
    "parallel_min_ms",
    "parallel_max_ms",
    "speedup",
    "sequential_rows_per_second",
    "parallel_rows_per_second",
    "sequential_nnz_per_second",
    "parallel_nnz_per_second",
    "sequential_expected_error",
    "parallel_expected_error",
    "max_absolute_error",
    "setup_time_ms",
    "cpu",
    "max_jvm_memory_bytes",
    "free_jvm_heap_bytes",
    "java_version",
    "operating_system",
    "status",
    "verdict",
    "notes",
]

WORKLOADS = (
    "UNIFORM_2",
    "UNIFORM_20",
    "UNIFORM_100",
    "BANDED",
    "BLOCK",
    "POWERLAW",
)
PARALLELISMS = (1, 2, 4, 8)
THRESHOLDS = (1024, 2048, 4096, 8192)

EXPECTED_KEYS = {
    (workload, parallelism, threshold)
    for workload in WORKLOADS
    for parallelism in PARALLELISMS
    for threshold in THRESHOLDS
}

EXPECTED_ROWS = len(EXPECTED_KEYS)

ABS_TOL = 1.0e-12
REL_TOL = 1.0e-8
ERROR_TOL = 1.0e-12

RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
WORKFLOW_ID_RE = re.compile(r"^[0-9]+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ValidationError(ValueError):
    """Raised when V3 evidence violates its contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def required_text(row: dict[str, str], field: str) -> str:
    value = row.get(field)
    require(value is not None, f"{field} is missing")
    value = value.strip()
    require(bool(value), f"{field} is empty")
    return value


def integer(row: dict[str, str], field: str) -> int:
    value = required_text(row, field)
    require(
        re.fullmatch(r"(0|[1-9][0-9]*)", value) is not None,
        f"{field} must be a nonnegative integer",
    )
    return int(value)


def number(row: dict[str, str], field: str) -> float:
    value = required_text(row, field)
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be numeric") from exc
    require(math.isfinite(result), f"{field} must be finite")
    return result


def close(actual: float, expected: float, field: str) -> None:
    require(
        math.isclose(
            actual,
            expected,
            rel_tol=REL_TOL,
            abs_tol=ABS_TOL,
        ),
        f"{field} mismatch: reported={actual!r}, calculated={expected!r}",
    )


def expected_verdict(speedup: float) -> str:
    if speedup < 0.80:
        return "REGRESSION"
    if speedup < 1.05:
        return "NEUTRAL"
    return "IMPROVEMENT"


def validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("timestamp must be ISO-8601") from exc
    require(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        "timestamp must include a timezone",
    )


def validate_row(
    row: dict[str, str],
    index: int,
) -> dict[str, Any]:
    prefix = f"row {index}: "

    try:
        require(
            None not in row,
            "CSV row contains more values than the header",
        )
        require(
            all(value is not None for value in row.values()),
            "CSV row contains missing values",
        )

        timestamp = required_text(row, "timestamp")
        validate_timestamp(timestamp)

        run_id = required_text(row, "run_id")
        require(bool(RUN_ID_RE.fullmatch(run_id)),
                "run_id contains unsupported characters")

        workflow_run_id = required_text(row, "workflow_run_id")
        require(bool(WORKFLOW_ID_RE.fullmatch(workflow_run_id)),
                "workflow_run_id must contain decimal digits only")

        commit_sha = required_text(row, "commit_sha")
        require(bool(COMMIT_RE.fullmatch(commit_sha)),
                "commit_sha must be a 40-character lowercase SHA-1")

        benchmark_id = required_text(row, "benchmark_id")
        workload_id = required_text(row, "workload_id")
        require(workload_id in WORKLOADS,
                f"unsupported workload_id: {workload_id}")

        for field in (
            "matrix_family",
            "distribution",
            "parallel_strategy",
            "split_policy",
            "cpu",
            "java_version",
            "operating_system",
        ):
            required_text(row, field)

        dimension = integer(row, "dimension")
        nnz = integer(row, "non_zero_count")
        parallelism = integer(row, "parallelism")
        threshold = integer(row, "threshold_rows")
        warmup = integer(row, "warmup_iterations")
        iterations = integer(row, "measured_iterations")

        require(dimension > 0, "dimension must be positive")
        require(nnz > 0, "non_zero_count must be positive")
        require(parallelism in PARALLELISMS,
                f"unsupported parallelism: {parallelism}")
        require(threshold in THRESHOLDS,
                f"unsupported threshold_rows: {threshold}")
        require(warmup >= 0, "warmup_iterations must be nonnegative")
        require(iterations > 0, "measured_iterations must be positive")
        require(bool(benchmark_id), "benchmark_id is empty")

        nnz_min = number(row, "nnz_min_per_row")
        nnz_avg = number(row, "nnz_avg_per_row")
        nnz_max = number(row, "nnz_max_per_row")

        require(nnz_min >= 0, "nnz_min_per_row must be nonnegative")
        require(nnz_avg >= 0, "nnz_avg_per_row must be nonnegative")
        require(nnz_max >= 0, "nnz_max_per_row must be nonnegative")
        require(nnz_min <= nnz_avg <= nnz_max,
                "row NNZ statistics must satisfy min <= average <= max")
        close(nnz_avg, nnz / dimension, "nnz_avg_per_row")

        # Fixed-density workload definitions have exact NNZ contracts.
        fixed_density = {
            "UNIFORM_2": 2,
            "UNIFORM_20": 20,
            "UNIFORM_100": 100,
        }
        if workload_id in fixed_density:
            expected_nnz = dimension * fixed_density[workload_id]
            require(
                nnz == expected_nnz,
                f"{workload_id} requires NNZ={expected_nnz}, got {nnz}",
            )
            close(
                nnz_min,
                float(fixed_density[workload_id]),
                "nnz_min_per_row",
            )
            close(
                nnz_max,
                float(fixed_density[workload_id]),
                "nnz_max_per_row",
            )

        timing_fields = (
            "sequential_mean_ms",
            "sequential_median_ms",
            "sequential_stddev_ms",
            "sequential_min_ms",
            "sequential_max_ms",
            "parallel_mean_ms",
            "parallel_median_ms",
            "parallel_stddev_ms",
            "parallel_min_ms",
            "parallel_max_ms",
        )
        metrics = {field: number(row, field) for field in timing_fields}

        for field in (
            "sequential_mean_ms",
            "sequential_median_ms",
            "sequential_min_ms",
            "sequential_max_ms",
            "parallel_mean_ms",
            "parallel_median_ms",
            "parallel_min_ms",
            "parallel_max_ms",
        ):
            require(metrics[field] > 0, f"{field} must be positive")

        for field in (
            "sequential_stddev_ms",
            "parallel_stddev_ms",
        ):
            require(metrics[field] >= 0, f"{field} must be nonnegative")

        require(
            metrics["sequential_min_ms"]
            <= metrics["sequential_median_ms"]
            <= metrics["sequential_max_ms"],
            "sequential min/median/max ordering is invalid",
        )
        require(
            metrics["parallel_min_ms"]
            <= metrics["parallel_median_ms"]
            <= metrics["parallel_max_ms"],
            "parallel min/median/max ordering is invalid",
        )
        require(
            metrics["sequential_min_ms"]
            <= metrics["sequential_mean_ms"]
            <= metrics["sequential_max_ms"],
            "sequential mean is outside min/max",
        )
        require(
            metrics["parallel_min_ms"]
            <= metrics["parallel_mean_ms"]
            <= metrics["parallel_max_ms"],
            "parallel mean is outside min/max",
        )

        speedup = number(row, "speedup")
        seq_rows_s = number(row, "sequential_rows_per_second")
        par_rows_s = number(row, "parallel_rows_per_second")
        seq_nnz_s = number(row, "sequential_nnz_per_second")
        par_nnz_s = number(row, "parallel_nnz_per_second")

        require(speedup > 0, "speedup must be positive")
        for field, value in (
            ("sequential_rows_per_second", seq_rows_s),
            ("parallel_rows_per_second", par_rows_s),
            ("sequential_nnz_per_second", seq_nnz_s),
            ("parallel_nnz_per_second", par_nnz_s),
        ):
            require(value > 0, f"{field} must be positive")

        calculated_speedup = (
            metrics["sequential_mean_ms"]
            / metrics["parallel_mean_ms"]
        )
        close(speedup, calculated_speedup, "speedup")

        seq_seconds = metrics["sequential_mean_ms"] / 1000.0
        par_seconds = metrics["parallel_mean_ms"] / 1000.0

        close(
            seq_rows_s,
            dimension / seq_seconds,
            "sequential_rows_per_second",
        )
        close(
            par_rows_s,
            dimension / par_seconds,
            "parallel_rows_per_second",
        )
        close(
            seq_nnz_s,
            nnz / seq_seconds,
            "sequential_nnz_per_second",
        )
        close(
            par_nnz_s,
            nnz / par_seconds,
            "parallel_nnz_per_second",
        )

        seq_error = number(row, "sequential_expected_error")
        par_error = number(row, "parallel_expected_error")
        max_error = number(row, "max_absolute_error")
        setup_ms = number(row, "setup_time_ms")

        require(
            min(seq_error, par_error, max_error, setup_ms) >= 0,
            "numerical errors and setup_time_ms must be nonnegative",
        )
        require(
            max(seq_error, par_error, max_error) <= ERROR_TOL,
            f"numerical error exceeds {ERROR_TOL}",
        )
        require(
            max_error + ABS_TOL >= max(seq_error, par_error),
            "max_absolute_error is smaller than an individual oracle error",
        )

        max_heap = integer(row, "max_jvm_memory_bytes")
        free_heap = integer(row, "free_jvm_heap_bytes")
        require(max_heap > 0, "max_jvm_memory_bytes must be positive")
        require(free_heap <= max_heap,
                "free_jvm_heap_bytes exceeds max_jvm_memory_bytes")

        status = required_text(row, "status")
        require(status == "PASS",
                f"row status must be PASS, got {status}")

        verdict = required_text(row, "verdict")
        calculated_verdict = expected_verdict(speedup)
        require(
            verdict == calculated_verdict,
            f"verdict mismatch: reported={verdict}, "
            f"calculated={calculated_verdict}",
        )

        key = (workload_id, parallelism, threshold)

        return {
            "row": index,
            "key": key,
            "run_id": run_id,
            "workflow_run_id": workflow_run_id,
            "commit_sha": commit_sha,
            "dimension": dimension,
            "nnz": nnz,
            "speedup": speedup,
            "verdict": calculated_verdict,
            "max_absolute_error": max_error,
        }

    except ValidationError as exc:
        raise ValidationError(prefix + str(exc)) from exc


def validate(path: Path) -> dict[str, Any]:
    path = Path(path)

    require(
        path.is_file() and not path.is_symlink(),
        f"CSV is missing, not a regular file, or a symlink: {path}",
    )

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            require(reader.fieldnames == HEADER, "V3 CSV header mismatch")
            rows = list(reader)
    except UnicodeError as exc:
        raise ValidationError("CSV is not valid UTF-8") from exc
    except csv.Error as exc:
        raise ValidationError(f"CSV syntax error: {exc}") from exc

    require(len(rows) == EXPECTED_ROWS,
            f"expected exactly {EXPECTED_ROWS} rows, got {len(rows)}")

    checked: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, int, int]] = set()

    common_run_id: str | None = None
    common_workflow_id: str | None = None
    common_commit: str | None = None

    for index, row in enumerate(rows, start=1):
        result = validate_row(row, index)
        key = result["key"]

        require(key not in seen_keys,
                f"row {index}: duplicate configuration key {key}")
        seen_keys.add(key)

        if common_run_id is None:
            common_run_id = result["run_id"]
            common_workflow_id = result["workflow_run_id"]
            common_commit = result["commit_sha"]
        else:
            require(
                result["run_id"] == common_run_id,
                f"row {index}: mixed run_id values",
            )
            require(
                result["workflow_run_id"] == common_workflow_id,
                f"row {index}: mixed workflow_run_id values",
            )
            require(
                result["commit_sha"] == common_commit,
                f"row {index}: mixed commit_sha values",
            )

        checked.append(result)

    missing = EXPECTED_KEYS - seen_keys
    extra = seen_keys - EXPECTED_KEYS

    require(
        not missing and not extra,
        "configuration matrix mismatch: "
        f"missing={sorted(missing)!r}; extra={sorted(extra)!r}",
    )

    verdict_counts = {
        verdict: sum(item["verdict"] == verdict for item in checked)
        for verdict in ("REGRESSION", "NEUTRAL", "IMPROVEMENT")
    }

    return {
        "schema": "qflpn-benchmark-v3-validation-v1",
        "validation": "PASS",
        "all_records_valid": True,
        "expected_records": EXPECTED_ROWS,
        "validated_records": len(checked),
        "configuration_matrix_complete": True,
        "run_id": common_run_id,
        "workflow_run_id": common_workflow_id,
        "commit_sha": common_commit,
        "verdict_counts": verdict_counts,
        "maximum_absolute_error": max(
            item["max_absolute_error"] for item in checked
        ),
        "records": checked,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Strictly validate QFLPN P3 Benchmark V3 evidence."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("P3/benchmarks/benchmark_results_v3.csv"),
    )
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()

    try:
        result = validate(args.csv)
        output = json.dumps(
            result,
            indent=2,
            allow_nan=False,
        ) + "\n"

        if args.report_json:
            args.report_json.parent.mkdir(parents=True, exist_ok=True)
            args.report_json.write_text(output, encoding="utf-8")

        print(output, end="")
        return 0

    except (ValidationError, OSError, ValueError) as exc:
        failure = {
            "schema": "qflpn-benchmark-v3-validation-v1",
            "validation": "FAIL",
            "all_records_valid": False,
            "error": str(exc),
        }
        print(
            json.dumps(failure, indent=2, allow_nan=False),
            file=sys.stderr,
        )

        if args.report_json:
            args.report_json.parent.mkdir(parents=True, exist_ok=True)
            args.report_json.write_text(
                json.dumps(failure, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
