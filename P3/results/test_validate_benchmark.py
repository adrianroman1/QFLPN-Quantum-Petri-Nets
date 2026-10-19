#!/usr/bin/env python3

"""
Regression tests for the independent P3 benchmark CSV validator.

Run from the P3 directory:

    python -m pytest results/test_validate_benchmark.py -v

The tests use synthetic data only. They do not claim benchmark
performance measurements or replace the actual benchmark run.
"""

from __future__ import annotations

import csv
import importlib.util
from argparse import Namespace
from pathlib import Path

import pytest


VALIDATOR_PATH = (
    Path(__file__).resolve().parent
    / "validate_benchmark.py"
)

SPEC = importlib.util.spec_from_file_location(
    "p3_validate_benchmark",
    VALIDATOR_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "Could not load validate_benchmark.py"
    )

VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


EXPECTED_HEADER = VALIDATOR.EXPECTED_HEADER

EXPECTED_N = 100
EXPECTED_NNZ = 200


def valid_row() -> dict[str, str]:
    """
    Return one internally consistent synthetic benchmark row.
    """

    return {
        "timestamp": "2026-10-20T10:00:00+00:00",
        "benchmark_id": "QFLPN-TEST-100",
        "dimension": str(EXPECTED_N),
        "non_zero_count": str(EXPECTED_NNZ),
        "parallelism": "2",
        "threshold": "4096",
        "warmup_iterations": "5",
        "measured_iterations": "10",
        "sequential_ms": "20.0",
        "parallel_ms": "10.0",
        "speedup": "2.0",
        "sequential_throughput_states_per_s": "5000.0",
        "parallel_throughput_states_per_s": "10000.0",
        "sequential_expected_error": "0.0",
        "parallel_expected_error": "0.0",
        "max_absolute_error": "0.0",
        "setup_time_ms": "1.5",
        "cpu": "test-cpu",
        "available_memory_bytes": "4000000000",
        "java_version": "21",
        "operating_system": "Linux",
        "notes": "Synthetic regression-test data",
    }


def write_csv(
    path: Path,
    row: dict[str, str],
) -> None:
    """
    Write one CSV row using the production schema.
    """

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=EXPECTED_HEADER,
            extrasaction="raise",
        )

        writer.writeheader()
        writer.writerow(row)


def validation_args(path: Path) -> Namespace:
    return Namespace(
        csv=path,
        expected_n=EXPECTED_N,
        parallelism=2,
        threshold=4096,
        warmup=5,
        iterations=10,
    )


def test_accepts_consistent_benchmark_row(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "valid.csv"

    write_csv(
        csv_path,
        valid_row(),
    )

    result = VALIDATOR.validate(
        validation_args(csv_path)
    )

    assert result["validation"] == "PASS"
    assert result["dimension"] == EXPECTED_N
    assert result["nnz"] == EXPECTED_NNZ
    assert result["speedup_recomputed"] == pytest.approx(2.0)
    assert result["time_reduction"] == pytest.approx(0.5)
    assert result["time_reduction_percent"] == pytest.approx(50.0)


def test_rejects_inconsistent_stored_speedup(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "invalid-speedup.csv"

    row = valid_row()
    row["speedup"] = "3.0"

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="speedup mismatch",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_nnz_different_from_twice_dimension(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "invalid-nnz.csv"

    row = valid_row()
    row["non_zero_count"] = "199"

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="NNZ mismatch",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_zero_sequential_execution_time(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "zero-sequential-time.csv"

    row = valid_row()
    row["sequential_ms"] = "0.0"

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="sequential_ms must be positive",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_zero_parallel_execution_time(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "zero-parallel-time.csv"

    row = valid_row()
    row["parallel_ms"] = "0.0"

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="parallel_ms must be positive",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_non_finite_execution_time(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "non-finite-time.csv"

    row = valid_row()
    row["parallel_ms"] = "nan"

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="parallel_ms must be finite",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_sequential_error_above_tolerance(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "sequential-error.csv"

    row = valid_row()
    row["sequential_expected_error"] = "1.1e-12"

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="sequential expected error exceeds tolerance",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_parallel_error_above_tolerance(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "parallel-error.csv"

    row = valid_row()
    row["parallel_expected_error"] = "1.1e-12"

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="parallel expected error exceeds tolerance",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_sequential_parallel_difference_above_tolerance(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "difference-error.csv"

    row = valid_row()
    row["max_absolute_error"] = "1.1e-12"

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="sequential/parallel difference exceeds tolerance",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_wrong_benchmark_dimension(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "wrong-dimension.csv"

    row = valid_row()
    row["dimension"] = "101"
    row["non_zero_count"] = "202"

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="dimension mismatch",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_wrong_parallelism(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "wrong-parallelism.csv"

    row = valid_row()
    row["parallelism"] = "4"

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="parallelism does not match",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_wrong_iteration_configuration(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "wrong-iterations.csv"

    row = valid_row()
    row["measured_iterations"] = "9"

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="measured iteration count does not match",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_missing_csv(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "missing.csv"

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="CSV file does not exist",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_invalid_csv_header(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "invalid-header.csv"

    csv_path.write_text(
        "timestamp,dimension,wrong-column\n",
        encoding="utf-8",
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="CSV header does not match",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_csv_without_data_rows(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "header-only.csv"

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.writer(handle)
        writer.writerow(EXPECTED_HEADER)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="CSV contains no benchmark data rows",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )


def test_rejects_missing_execution_metadata(
    tmp_path: Path,
) -> None:

    csv_path = tmp_path / "missing-metadata.csv"

    row = valid_row()
    row["java_version"] = ""

    write_csv(
        csv_path,
        row,
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="java_version must not be empty",
    ):
        VALIDATOR.validate(
            validation_args(csv_path)
        )
