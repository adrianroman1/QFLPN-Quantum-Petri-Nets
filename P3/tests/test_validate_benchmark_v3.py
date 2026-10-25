from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "results"
    / "validate_benchmark_v3.py"
)
SPEC = importlib.util.spec_from_file_location(
    "qflpn_validate_benchmark_v3",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None

VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def make_row(
    workload: str,
    parallelism: int,
    threshold: int,
) -> dict[str, str]:
    dimension = 100
    density = {
        "UNIFORM_2": 2,
        "UNIFORM_20": 20,
        "UNIFORM_100": 100,
    }.get(workload, 5)

    nnz = dimension * density
    seq_mean = 20.0
    par_mean = 10.0
    speedup = seq_mean / par_mean

    return {
        "timestamp": "2026-10-25T10:00:00Z",
        "run_id": "p3-v3-test-001",
        "workflow_run_id": "40229879183",
        "commit_sha": "a" * 40,
        "benchmark_id": f"QFLPN-V3-{workload}-100",
        "workload_id": workload,
        "matrix_family": "CSR",
        "distribution": workload.lower(),
        "dimension": str(dimension),
        "non_zero_count": str(nnz),
        "nnz_min_per_row": str(density),
        "nnz_avg_per_row": str(density),
        "nnz_max_per_row": str(density),
        "parallelism": str(parallelism),
        "threshold_rows": str(threshold),
        "parallel_strategy": "ForkJoinPool",
        "split_policy": "ROW_BALANCED",
        "warmup_iterations": "2",
        "measured_iterations": "5",
        "sequential_mean_ms": str(seq_mean),
        "sequential_median_ms": "19",
        "sequential_stddev_ms": "1",
        "sequential_min_ms": "18",
        "sequential_max_ms": "22",
        "parallel_mean_ms": str(par_mean),
        "parallel_median_ms": "9",
        "parallel_stddev_ms": "1",
        "parallel_min_ms": "8",
        "parallel_max_ms": "12",
        "speedup": str(speedup),
        "sequential_rows_per_second": str(
            dimension / (seq_mean / 1000.0)
        ),
        "parallel_rows_per_second": str(
            dimension / (par_mean / 1000.0)
        ),
        "sequential_nnz_per_second": str(
            nnz / (seq_mean / 1000.0)
        ),
        "parallel_nnz_per_second": str(
            nnz / (par_mean / 1000.0)
        ),
        "sequential_expected_error": "0",
        "parallel_expected_error": "0",
        "max_absolute_error": "0",
        "setup_time_ms": "1",
        "cpu": "test-cpu",
        "max_jvm_memory_bytes": "4000000000",
        "free_jvm_heap_bytes": "500000000",
        "java_version": "21",
        "operating_system": "Linux",
        "status": "PASS",
        "verdict": "IMPROVEMENT",
        "notes": "synthetic validator fixture",
    }


def complete_matrix() -> list[dict[str, str]]:
    return [
        make_row(workload, parallelism, threshold)
        for workload in VALIDATOR.WORKLOADS
        for parallelism in VALIDATOR.PARALLELISMS
        for threshold in VALIDATOR.THRESHOLDS
    ]


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=VALIDATOR.HEADER,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


def test_expected_matrix_contains_96_configurations() -> None:
    assert VALIDATOR.EXPECTED_ROWS == 96
    assert len(VALIDATOR.EXPECTED_KEYS) == 96


def test_accepts_complete_valid_matrix(tmp_path: Path) -> None:
    path = tmp_path / "benchmark-v3.csv"
    write_csv(path, complete_matrix())

    result = VALIDATOR.validate(path)

    assert result["validation"] == "PASS"
    assert result["all_records_valid"] is True
    assert result["validated_records"] == 96
    assert result["expected_records"] == 96
    assert result["configuration_matrix_complete"] is True
    assert result["run_id"] == "p3-v3-test-001"
    assert result["workflow_run_id"] == "40229879183"
    assert result["verdict_counts"]["IMPROVEMENT"] == 96


def test_rejects_missing_configuration(tmp_path: Path) -> None:
    rows = complete_matrix()
    rows.pop()

    path = tmp_path / "missing.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="expected exactly 96 rows",
    ):
        VALIDATOR.validate(path)


def test_rejects_duplicate_configuration(tmp_path: Path) -> None:
    rows = complete_matrix()
    rows[-1] = dict(rows[0])

    path = tmp_path / "duplicate.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="duplicate configuration key",
    ):
        VALIDATOR.validate(path)


def test_rejects_mixed_run_ids(tmp_path: Path) -> None:
    rows = complete_matrix()
    rows[-1]["run_id"] = "another-run"

    path = tmp_path / "mixed-run.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="mixed run_id",
    ):
        VALIDATOR.validate(path)


def test_rejects_mixed_workflow_run_ids(tmp_path: Path) -> None:
    rows = complete_matrix()
    rows[-1]["workflow_run_id"] = "999999"

    path = tmp_path / "mixed-workflow.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="mixed workflow_run_id",
    ):
        VALIDATOR.validate(path)


def test_rejects_mixed_commit_sha(tmp_path: Path) -> None:
    rows = complete_matrix()
    rows[-1]["commit_sha"] = "b" * 40

    path = tmp_path / "mixed-commit.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="mixed commit_sha",
    ):
        VALIDATOR.validate(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("workload_id", "UNKNOWN", "unsupported workload_id"),
        ("parallelism", "3", "unsupported parallelism"),
        ("threshold_rows", "4096.0", "nonnegative integer"),
        ("dimension", "0", "dimension must be positive"),
        ("non_zero_count", "0", "non_zero_count must be positive"),
        ("commit_sha", "invalid", "40-character lowercase SHA-1"),
        ("workflow_run_id", "run-123", "decimal digits only"),
        ("timestamp", "2026-10-25T10:00:00", "timezone"),
        ("status", "FAIL", "row status must be PASS"),
        ("sequential_mean_ms", "nan", "must be finite"),
        ("parallel_mean_ms", "0", "parallel_mean_ms must be positive"),
        ("max_absolute_error", "1e-4", "numerical error exceeds"),
        ("free_jvm_heap_bytes", "5000000000", "exceeds"),
    ],
)
def test_rejects_invalid_row_fields(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    rows = complete_matrix()
    rows[0][field] = value

    path = tmp_path / "invalid.csv"
    write_csv(path, rows)

    with pytest.raises(VALIDATOR.ValidationError, match=message):
        VALIDATOR.validate(path)


def test_recalculates_and_rejects_speedup(tmp_path: Path) -> None:
    rows = complete_matrix()
    rows[0]["speedup"] = "3.0"

    path = tmp_path / "wrong-speedup.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="speedup mismatch",
    ):
        VALIDATOR.validate(path)


def test_recalculates_and_rejects_throughput(tmp_path: Path) -> None:
    rows = complete_matrix()
    rows[0]["sequential_nnz_per_second"] = "123"

    path = tmp_path / "wrong-throughput.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="sequential_nnz_per_second mismatch",
    ):
        VALIDATOR.validate(path)


@pytest.mark.parametrize(
    ("speedup", "expected"),
    [
        (0.799999, "REGRESSION"),
        (0.80, "NEUTRAL"),
        (1.049999, "NEUTRAL"),
        (1.05, "IMPROVEMENT"),
    ],
)
def test_verdict_boundaries(
    speedup: float,
    expected: str,
) -> None:
    assert VALIDATOR.expected_verdict(speedup) == expected


def test_rejects_incorrect_verdict(tmp_path: Path) -> None:
    rows = complete_matrix()
    rows[0]["verdict"] = "REGRESSION"

    path = tmp_path / "wrong-verdict.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="verdict mismatch",
    ):
        VALIDATOR.validate(path)


def test_rejects_wrong_csv_header(tmp_path: Path) -> None:
    path = tmp_path / "wrong-header.csv"
    path.write_text(
        "timestamp,run_id,dimension\n"
        "2026-10-25T10:00:00Z,test,100\n",
        encoding="utf-8",
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="V3 CSV header mismatch",
    ):
        VALIDATOR.validate(path)


def test_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.csv"
    write_csv(target, complete_matrix())

    link = tmp_path / "link.csv"
    link.symlink_to(target)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="symlink",
    ):
        VALIDATOR.validate(link)


def test_rejects_uniform_workload_with_wrong_nnz(tmp_path: Path) -> None:
    rows = complete_matrix()
    rows[0]["non_zero_count"] = "201"

    path = tmp_path / "wrong-uniform-nnz.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="requires NNZ",
    ):
        VALIDATOR.validate(path)
