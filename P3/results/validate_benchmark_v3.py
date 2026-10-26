#!/usr/bin/env python3
"""Fail-closed validator for persistent QFLPN P3 Benchmark V3 evidence.

Supported contracts:

LEGACY_96:
    6 workloads x 4 parallelism values x 4 thresholds = 96 rows.
    The legacy runner policy is ROW_BOUNDARY_SCAN.

AB_192:
    6 workloads x 2 split policies x 4 parallelism values
    x 4 thresholds = 192 rows.

The CSV schema is the 46-column schema emitted by
BenchmarkV3ResultWriter and BenchmarkV3Runner.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict
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

LEGACY_POLICY = "ROW_BOUNDARY_SCAN"

POLICIES = (
    "ROW_BOUNDARY_SCAN",
    "BINARY_NNZ_SPLIT",
)

MINIMUM_DIMENSION = 100

# Backward-compatible constant used by older tests and tooling.
EXPECTED_ROWS = 96

EXPECTED_LEGACY_ROWS = 96
EXPECTED_AB_ROWS = 192

ABS_TOL = 1.0e-12
REL_TOL = 1.0e-8
ERROR_TOL = 1.0e-12

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
WORKFLOW_ID_RE = re.compile(r"^[0-9]+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

LEGACY_KEYS = {
    (workload, parallelism, threshold)
    for workload in WORKLOADS
    for parallelism in PARALLELISMS
    for threshold in THRESHOLDS
}

AB_KEYS = {
    (workload, policy, parallelism, threshold)
    for workload in WORKLOADS
    for policy in POLICIES
    for parallelism in PARALLELISMS
    for threshold in THRESHOLDS
}


class ValidationError(ValueError):
    """Raised when V3 evidence violates its validation contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def text(row: dict[str, str], field: str) -> str:
    value = row.get(field)

    require(value is not None, f"{field} is missing")

    value = value.strip()

    require(bool(value), f"{field} is empty")

    return value


def integer(row: dict[str, str], field: str) -> int:
    value = text(row, field)

    require(
        re.fullmatch(r"(0|[1-9][0-9]*)", value) is not None,
        f"{field} must be a nonnegative integer",
    )

    return int(value)


def number(row: dict[str, str], field: str) -> float:
    value = text(row, field)

    try:
        result = float(value)
    except ValueError as exc:
        raise ValidationError(
            f"{field} must be numeric"
        ) from exc

    require(
        math.isfinite(result),
        f"{field} must be finite",
    )

    return result


def close(
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
            f"reported={actual!r}, calculated={expected!r}"
        ),
    )


def expected_verdict(speedup: float) -> str:
    if speedup < 0.80:
        return "REGRESSION"

    if speedup < 1.05:
        return "NEUTRAL"

    return "IMPROVEMENT"


def validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValidationError(
            "timestamp must be ISO-8601"
        ) from exc

    require(
        parsed.tzinfo is not None
        and parsed.utcoffset() is not None,
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
            "CSV row contains extra values",
        )

        require(
            all(value is not None for value in row.values()),
            "CSV row contains missing values",
        )

        validate_timestamp(
            text(row, "timestamp")
        )

        run_id = text(row, "run_id")

        require(
            RUN_ID_RE.fullmatch(run_id) is not None,
            "run_id contains unsupported characters",
        )

        workflow_id = text(row, "workflow_run_id")

        require(
            WORKFLOW_ID_RE.fullmatch(workflow_id) is not None,
            "workflow_run_id must contain decimal digits only",
        )

        commit = text(row, "commit_sha")

        require(
            COMMIT_RE.fullmatch(commit) is not None,
            "commit_sha must be a 40-character lowercase SHA-1",
        )

        workload = text(row, "workload_id")

        require(
            workload in WORKLOADS,
            f"unsupported workload_id: {workload}",
        )

        for field in (
            "benchmark_id",
            "matrix_family",
            "distribution",
            "parallel_strategy",
            "split_policy",
            "cpu",
            "java_version",
            "operating_system",
            "notes",
        ):
            text(row, field)

        dimension = integer(row, "dimension")
        nnz = integer(row, "non_zero_count")
        parallelism = integer(row, "parallelism")
        threshold = integer(row, "threshold_rows")
        warmup = integer(row, "warmup_iterations")
        iterations = integer(row, "measured_iterations")

        require(
            dimension >= MINIMUM_DIMENSION,
            (
                "dimension must be at least "
                f"{MINIMUM_DIMENSION}"
            ),
        )

        require(
            nnz > 0,
            "non_zero_count must be positive",
        )

        require(
            parallelism in PARALLELISMS,
            f"unsupported parallelism: {parallelism}",
        )

        require(
            threshold in THRESHOLDS,
            f"unsupported threshold_rows: {threshold}",
        )

        require(
            warmup >= 0,
            "warmup_iterations must be nonnegative",
        )

        require(
            iterations > 0,
            "measured_iterations must be positive",
        )

        require(
            text(row, "parallel_strategy") == "FORK_JOIN",
            "parallel_strategy must be FORK_JOIN",
        )

        policy = text(row, "split_policy")

        require(
            policy in POLICIES,
            f"unsupported split_policy: {policy}",
        )

        nnz_min = number(row, "nnz_min_per_row")
        nnz_avg = number(row, "nnz_avg_per_row")
        nnz_max = number(row, "nnz_max_per_row")

        require(
            0 <= nnz_min <= nnz_avg <= nnz_max,
            (
                "NNZ row statistics must satisfy "
                "0 <= min <= average <= max"
            ),
        )

        close(
            nnz_avg,
            nnz / dimension,
            "nnz_avg_per_row",
        )

        fixed_density = {
            "UNIFORM_2": 2,
            "UNIFORM_20": 20,
            "UNIFORM_100": 100,
        }

        if workload in fixed_density:
            density = fixed_density[workload]

            require(
                nnz == dimension * density,
                (
                    f"{workload} requires NNZ="
                    f"{dimension * density}"
                ),
            )

            close(
                nnz_min,
                float(density),
                "nnz_min_per_row",
            )

            close(
                nnz_max,
                float(density),
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

        metrics = {
            field: number(row, field)
            for field in timing_fields
        }

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
            require(
                metrics[field] > 0,
                f"{field} must be positive",
            )

        for field in (
            "sequential_stddev_ms",
            "parallel_stddev_ms",
        ):
            require(
                metrics[field] >= 0,
                f"{field} must be nonnegative",
            )

        for prefix_name in ("sequential", "parallel"):
            minimum = metrics[
                f"{prefix_name}_min_ms"
            ]

            median_value = metrics[
                f"{prefix_name}_median_ms"
            ]

            maximum = metrics[
                f"{prefix_name}_max_ms"
            ]

            mean_value = metrics[
                f"{prefix_name}_mean_ms"
            ]

            require(
                minimum <= median_value <= maximum,
                (
                    f"{prefix_name} "
                    "min/median/max ordering is invalid"
                ),
            )

            require(
                minimum <= mean_value <= maximum,
                f"{prefix_name} mean is outside min/max",
            )

        speedup = number(row, "speedup")

        require(
            speedup > 0,
            "speedup must be positive",
        )

        seq_seconds = (
            metrics["sequential_mean_ms"] / 1000.0
        )

        par_seconds = (
            metrics["parallel_mean_ms"] / 1000.0
        )

        throughput = (
            (
                "sequential_rows_per_second",
                dimension / seq_seconds,
            ),
            (
                "parallel_rows_per_second",
                dimension / par_seconds,
            ),
            (
                "sequential_nnz_per_second",
                nnz / seq_seconds,
            ),
            (
                "parallel_nnz_per_second",
                nnz / par_seconds,
            ),
        )

        for field, expected in throughput:
            value = number(row, field)

            require(
                value > 0,
                f"{field} must be positive",
            )

            close(
                value,
                expected,
                field,
            )

        close(
            speedup,
            (
                metrics["sequential_mean_ms"]
                / metrics["parallel_mean_ms"]
            ),
            "speedup",
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

        setup_ms = number(
            row,
            "setup_time_ms",
        )

        require(
            min(
                seq_error,
                par_error,
                max_error,
                setup_ms,
            ) >= 0,
            "errors and setup_time_ms must be nonnegative",
        )

        require(
            max(
                seq_error,
                par_error,
                max_error,
            ) <= ERROR_TOL,
            f"numerical error exceeds {ERROR_TOL}",
        )

        require(
            max_error + ABS_TOL >= max(
                seq_error,
                par_error,
            ),
            (
                "max_absolute_error is smaller than "
                "an individual oracle error"
            ),
        )

        max_heap = integer(
            row,
            "max_jvm_memory_bytes",
        )

        free_heap = integer(
            row,
            "free_jvm_heap_bytes",
        )

        require(
            max_heap > 0,
            "max_jvm_memory_bytes must be positive",
        )

        require(
            free_heap <= max_heap,
            "free_jvm_heap_bytes exceeds max_jvm_memory_bytes",
        )

        require(
            text(row, "status") == "PASS",
            "row status must be PASS",
        )

        verdict = text(row, "verdict")
        calculated = expected_verdict(speedup)

        require(
            verdict == calculated,
            (
                "verdict mismatch: "
                f"reported={verdict}, calculated={calculated}"
            ),
        )

        return {
            "row": index,
            "key": (
                workload,
                policy,
                parallelism,
                threshold,
            ),
            "legacy_key": (
                workload,
                parallelism,
                threshold,
            ),
            "policy": policy,
            "run_id": run_id,
            "workflow_run_id": workflow_id,
            "commit_sha": commit,
            "dimension": dimension,
            "nnz": nnz,
            "speedup": speedup,
            "verdict": calculated,
            "max_absolute_error": max_error,
        }

    except ValidationError as exc:
        raise ValidationError(
            prefix + str(exc)
        ) from exc


def validate_run(
    run_id: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    require(
        bool(items),
        f"RUN_ID={run_id} contains no records",
    )

    identities = {
        (
            item["workflow_run_id"],
            item["commit_sha"],
        )
        for item in items
    }

    require(
        len(identities) == 1,
        (
            f"RUN_ID={run_id} mixes workflow "
            "or commit provenance"
        ),
    )

    policies = {
        item["policy"]
        for item in items
    }

    keys = [
        item["key"]
        for item in items
    ]

    require(
        len(keys) == len(set(keys)),
        (
            f"RUN_ID={run_id} contains duplicate "
            "workload/policy/configuration keys"
        ),
    )

    if policies == set(POLICIES):
        contract = "AB_192"

        require(
            len(items) == EXPECTED_AB_ROWS,
            (
                f"RUN_ID={run_id} has {len(items)} rows; "
                f"expected {EXPECTED_AB_ROWS}"
            ),
        )

        require(
            set(keys) == AB_KEYS,
            (
                f"RUN_ID={run_id} has an incomplete "
                "A/B configuration matrix"
            ),
        )

        return {
            "contract": contract,
            "rows": len(items),
            "policies": sorted(policies),
            "identity": next(iter(identities)),
        }

    if policies == {LEGACY_POLICY}:
        contract = "LEGACY_96"

        legacy_keys = [
            item["legacy_key"]
            for item in items
        ]

        require(
            len(legacy_keys) == len(set(legacy_keys)),
            (
                f"RUN_ID={run_id} contains duplicate "
                "legacy configurations"
            ),
        )

        require(
            len(items) == EXPECTED_LEGACY_ROWS,
            (
                f"RUN_ID={run_id} has {len(items)} rows; "
                f"expected {EXPECTED_LEGACY_ROWS}"
            ),
        )

        require(
            set(legacy_keys) == LEGACY_KEYS,
            (
                f"RUN_ID={run_id} has an incomplete "
                "legacy configuration matrix"
            ),
        )

        return {
            "contract": contract,
            "rows": len(items),
            "policies": sorted(policies),
            "identity": next(iter(identities)),
        }

    raise ValidationError(
        (
            f"RUN_ID={run_id} has mixed or unsupported "
            f"split policies: {sorted(policies)}"
        )
    )


def validate(
    path: Path,
    *,
    run_id: str | None = None,
    workflow_run_id: str | None = None,
    commit_sha: str | None = None,
) -> dict[str, Any]:
    """Validate every historical run and the selected complete execution."""

    path = Path(path)

    require(
        path.is_file() and not path.is_symlink(),
        (
            "CSV is missing, not a regular file, "
            f"or a symlink: {path}"
        ),
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

            require(
                reader.fieldnames == HEADER,
                "V3 CSV header mismatch",
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

    require(
        bool(rows),
        "V3 CSV contains no data rows",
    )

    checked = [
        validate_row(row, index)
        for index, row in enumerate(
            rows,
            start=1,
        )
    ]

    by_run: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for item in checked:
        by_run[item["run_id"]].append(item)

    run_reports: dict[
        str,
        dict[str, Any],
    ] = {}

    for historical_run_id, items in by_run.items():
        run_reports[historical_run_id] = validate_run(
            historical_run_id,
            items,
        )

    selected_id = (
        run_id
        if run_id is not None
        else checked[-1]["run_id"]
    )

    require(
        isinstance(selected_id, str)
        and RUN_ID_RE.fullmatch(selected_id) is not None,
        "requested RUN_ID is invalid",
    )

    selected = by_run.get(selected_id)

    require(
        selected is not None,
        f"RUN_ID not found in V3 CSV: {selected_id}",
    )

    selected_workflows = {
        item["workflow_run_id"]
        for item in selected
    }

    selected_commits = {
        item["commit_sha"]
        for item in selected
    }

    if workflow_run_id is not None:
        require(
            selected_workflows == {str(workflow_run_id)},
            (
                "V3 workflow_run_id does not match "
                "requested workflow"
            ),
        )

    if commit_sha is not None:
        require(
            selected_commits == {commit_sha},
            (
                "V3 commit_sha does not match "
                "requested commit"
            ),
        )

    counts = {
        verdict: sum(
            item["verdict"] == verdict
            for item in selected
        )
        for verdict in (
            "REGRESSION",
            "NEUTRAL",
            "IMPROVEMENT",
        )
    }

    selected_contract = run_reports[
        selected_id
    ]["contract"]

    expected_records = (
        EXPECTED_AB_ROWS
        if selected_contract == "AB_192"
        else EXPECTED_LEGACY_ROWS
    )

    return {
        "schema": "qflpn-benchmark-v3-validation-v2",
        "validation": "PASS",
        "all_records_valid": True,
        "historical_runs_validated": len(by_run),
        "run_contracts": run_reports,
        "expected_records": expected_records,
        "validated_records": len(selected),
        "configuration_matrix_complete": True,
        "run_contract": selected_contract,
        "run_id": selected_id,
        "workflow_run_id": next(iter(selected_workflows)),
        "commit_sha": next(iter(selected_commits)),
        "split_policies": sorted({
            item["policy"]
            for item in selected
        }),
        "verdict_counts": counts,
        "maximum_absolute_error": max(
            item["max_absolute_error"]
            for item in selected
        ),
        "records": selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate persistent QFLPN P3 Benchmark V3 evidence."
        )
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(
            "P3/benchmarks/benchmark_results_v3.csv"
        ),
    )

    parser.add_argument("--run-id")
    parser.add_argument("--workflow-run-id")
    parser.add_argument("--commit-sha")

    parser.add_argument(
        "--report-json",
        type=Path,
    )

    args = parser.parse_args()

    try:
        result = validate(
            args.csv,
            run_id=args.run_id,
            workflow_run_id=args.workflow_run_id,
            commit_sha=args.commit_sha,
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
        failure = {
            "schema": "qflpn-benchmark-v3-validation-v2",
            "validation": "FAIL",
            "all_records_valid": False,
            "error": str(exc),
        }

        output = (
            json.dumps(
                failure,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        )

        print(
            output,
            file=sys.stderr,
            end="",
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

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
