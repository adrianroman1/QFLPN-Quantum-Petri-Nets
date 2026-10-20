#!/usr/bin/env python3

"""Regression tests for the independent P3 CSV validator."""

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

HEADER = VALIDATOR.EXPECTED_HEADER

N = 100


def valid_row() -> dict[str, str]:
    return {
        "timestamp": "2026-10-20T10:00:00Z",
        "benchmark_id": "QFLPN-100",
        "dimension": "100",
        "non_zero_count": "200",
        "parallelism": "2",
        "threshold": "4096",
        "warmup_iterations": "1",
        "measured_iterations": "2",
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
        "notes": "Synthetic test data",
    }


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=HEADER,
            extrasaction="raise",
        )

        writer.writeheader()
        writer.writerows(rows)


def args_for(path: Path, **overrides) -> Namespace:
    values = {
        "csv": path,
        "expected_n": N,
        "parallelism": 2,
        "threshold": 4096,
        "warmup": 1,
        "iterations": 2,
        "expected_row_count": None,
    }

    values.update(overrides)

    return Namespace(**values)


def test_accepts_valid_row(tmp_path: Path) -> None:
    path = tmp_path / "valid.csv"
    write_csv(path, [valid_row()])

    result = VALIDATOR.validate(args_for(path))

    assert result["validation"] == "PASS"
    assert result["dimension"] == N
    assert result["nnz"] == 2 * N
    assert result["speedup_recomputed"] == pytest.approx(2.0)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("sequential_expected_error", "-1.0", "must not be negative"),
        ("parallel_expected_error", "-1.0", "must not be negative"),
        ("max_absolute_error", "-1.0", "must not be negative"),
        ("sequential_expected_error", "1.1e-12", "exceeds tolerance"),
        ("parallel_expected_error", "1.1e-12", "exceeds tolerance"),
        ("max_absolute_error", "1.1e-12", "exceeds tolerance"),
        ("sequential_ms", "0", "must be positive"),
        ("parallel_ms", "0", "must be positive"),
        ("parallel_ms", "nan", "must be finite"),
        ("speedup", "nan", "must be finite"),
        ("setup_time_ms", "-1", "must not be negative"),
        ("available_memory_bytes", "0", "must be positive"),
        ("java_version", "", "must not be empty"),
    ],
)
def test_rejects_invalid_fields(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    path = tmp_path / "invalid.csv"

    row = valid_row()
    row[field] = value

    write_csv(path, [row])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match=message,
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_wrong_speedup(tmp_path: Path) -> None:
    path = tmp_path / "speedup.csv"

    row = valid_row()
    row["speedup"] = "3.0"

    write_csv(path, [row])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="speedup mismatch",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_wrong_sequential_throughput(
    tmp_path: Path,
) -> None:
    path = tmp_path / "throughput.csv"

    row = valid_row()
    row["sequential_throughput_states_per_s"] = "1.0"

    write_csv(path, [row])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="sequential throughput mismatch",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_wrong_nnz(tmp_path: Path) -> None:
    path = tmp_path / "nnz.csv"

    row = valid_row()
    row["non_zero_count"] = "199"

    write_csv(path, [row])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="NNZ mismatch",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_wrong_dimension(tmp_path: Path) -> None:
    path = tmp_path / "dimension.csv"

    row = valid_row()
    row["dimension"] = "101"

    write_csv(path, [row])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="dimension mismatch",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_wrong_parallelism(tmp_path: Path) -> None:
    path = tmp_path / "parallelism.csv"

    row = valid_row()
    row["parallelism"] = "4"

    write_csv(path, [row])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="parallelism does not match",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_wrong_threshold(tmp_path: Path) -> None:
    path = tmp_path / "threshold.csv"

    row = valid_row()
    row["threshold"] = "2048"

    write_csv(path, [row])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="threshold does not match",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_wrong_iteration_count(
    tmp_path: Path,
) -> None:
    path = tmp_path / "iterations.csv"

    row = valid_row()
    row["measured_iterations"] = "3"

    write_csv(path, [row])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="measured iteration count",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_wrong_warmup_count(
    tmp_path: Path,
) -> None:
    path = tmp_path / "warmup.csv"

    row = valid_row()
    row["warmup_iterations"] = "5"

    write_csv(path, [row])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="warmup iteration count",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_wrong_record_count(
    tmp_path: Path,
) -> None:
    path = tmp_path / "records.csv"
    write_csv(path, [valid_row()])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="record count mismatch",
    ):
        VALIDATOR.validate(
            args_for(path, expected_row_count=2)
        )


def test_accepts_expected_record_count(
    tmp_path: Path,
) -> None:
    path = tmp_path / "records.csv"

    write_csv(
        path,
        [valid_row(), valid_row()],
    )

    result = VALIDATOR.validate(
        args_for(path, expected_row_count=2)
    )

    assert result["csv_total_records"] == 2


def test_rejects_missing_csv(tmp_path: Path) -> None:
    path = tmp_path / "missing.csv"

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="CSV file does not exist",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_header_only_csv(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        csv.writer(handle).writerow(HEADER)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="no benchmark data rows",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_invalid_header(tmp_path: Path) -> None:
    path = tmp_path / "header.csv"
    path.write_text(
        "timestamp,dimension,wrong\n",
        encoding="utf-8",
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="header does not match",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_extra_csv_column(tmp_path: Path) -> None:
    path = tmp_path / "extra.csv"

    row = valid_row()

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerow(
            [row[field] for field in HEADER] + ["unexpected"]
        )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="unexpected extra columns",
    ):
        VALIDATOR.validate(args_for(path))


def test_rejects_timestamp_without_timezone(
    tmp_path: Path,
) -> None:
    path = tmp_path / "timezone.csv"

    row = valid_row()
    row["timestamp"] = "2026-10-20T10:00:00"

    write_csv(path, [row])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="timezone information",
    ):
        VALIDATOR.validate(args_for(path))
