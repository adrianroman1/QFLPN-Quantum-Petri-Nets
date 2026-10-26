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

RUN_ID = "p3-v3-test-001"
WORKFLOW_RUN_ID = "40229879183"
COMMIT_SHA = "a" * 40

LEGACY_POLICY = "ROW_BOUNDARY_SCAN"
AB_POLICIES = (
    "ROW_BOUNDARY_SCAN",
    "BINARY_NNZ_SPLIT",
)

EXPECTED_LEGACY_ROWS = 96
EXPECTED_AB_ROWS = 192


def make_row(
    workload: str,
    parallelism: int,
    threshold: int,
    split_policy: str,
) -> dict[str, str]:
    dimension = 100

    density = {
        "UNIFORM_2": 2,
        "UNIFORM_20": 20,
        "UNIFORM_100": 100,
        "BANDED": 5,
        "BLOCK": 8,
    }.get(workload)

    if density is None:
        # Deterministic POWERLAW row-count model used by the Java runner.
        density = sum(
            min(dimension, 1 + int(32.0 / (row + 1.0) ** 0.5))
            for row in range(dimension)
        ) // dimension

    if workload == "POWERLAW":
        row_counts = [
            min(dimension, 1 + int(32.0 / (row + 1.0) ** 0.5))
            for row in range(dimension)
        ]
        nnz = sum(row_counts)
        nnz_min = min(row_counts)
        nnz_max = max(row_counts)
        nnz_avg = nnz / dimension
    else:
        nnz = dimension * density
        nnz_min = float(density)
        nnz_max = float(density)
        nnz_avg = float(density)

    seq_mean = 20.0
    par_mean = 10.0
    speedup = seq_mean / par_mean

    return {
        "timestamp": "2026-10-25T10:00:00Z",
        "run_id": RUN_ID,
        "workflow_run_id": WORKFLOW_RUN_ID,
        "commit_sha": COMMIT_SHA,
        "benchmark_id": (
            f"QFLPN-V3-{workload}-{split_policy}"
        ),
        "workload_id": workload,
        "matrix_family": {
            "UNIFORM_2": "UNIFORM",
            "UNIFORM_20": "UNIFORM",
            "UNIFORM_100": "UNIFORM",
            "BANDED": "BANDED",
            "BLOCK": "BLOCK_DIAGONAL",
            "POWERLAW": "POWER_LAW",
        }[workload],
        "distribution": {
            "UNIFORM_2": "FIXED_2_PER_ROW",
            "UNIFORM_20": "FIXED_20_PER_ROW",
            "UNIFORM_100": "FIXED_100_PER_ROW",
            "BANDED": "LOCAL_BAND_5",
            "BLOCK": "BLOCK_LOCAL_8",
            "POWERLAW": "DETERMINISTIC_INVERSE_SQRT",
        }[workload],
        "dimension": str(dimension),
        "non_zero_count": str(nnz),
        "nnz_min_per_row": str(nnz_min),
        "nnz_avg_per_row": str(nnz_avg),
        "nnz_max_per_row": str(nnz_max),
        "parallelism": str(parallelism),
        "threshold_rows": str(threshold),
        "parallel_strategy": "FORK_JOIN",
        "split_policy": split_policy,
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
        "cpu": "test-cpu;processors=8",
        "max_jvm_memory_bytes": "4000000000",
        "free_jvm_heap_bytes": "500000000",
        "java_version": "21",
        "operating_system": "Linux",
        "status": "PASS",
        "verdict": "IMPROVEMENT",
        "notes": (
            "pool_reused;alternating_order;"
            "independent_csr_oracle"
            f";split_policy={split_policy}"
        ),
    }


def make_matrix(
    policies: tuple[str, ...],
) -> list[dict[str, str]]:
    return [
        make_row(
            workload,
            parallelism,
            threshold,
            policy,
        )
        for workload in VALIDATOR.WORKLOADS
        for policy in policies
        for parallelism in VALIDATOR.PARALLELISMS
        for threshold in VALIDATOR.THRESHOLDS
    ]


def legacy_matrix() -> list[dict[str, str]]:
    return make_matrix((LEGACY_POLICY,))


def ab_matrix() -> list[dict[str, str]]:
    return make_matrix(AB_POLICIES)


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=VALIDATOR.HEADER,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


def validate_file(
    path: Path,
    expected_rows: int,
    expected_contract: str,
) -> dict:
    result = VALIDATOR.validate(
        path,
        run_id=RUN_ID,
        workflow_run_id=WORKFLOW_RUN_ID,
        commit_sha=COMMIT_SHA,
    )

    assert result["validation"] == "PASS"
    assert result["all_records_valid"] is True
    assert result["configuration_matrix_complete"] is True
    assert result["run_id"] == RUN_ID
    assert result["workflow_run_id"] == WORKFLOW_RUN_ID
    assert result["commit_sha"] == COMMIT_SHA
    assert result["validated_records"] == expected_rows
    assert result["expected_records"] == expected_rows
    assert result["run_contract"] == expected_contract

    return result


def test_runner_schema_has_exactly_46_columns() -> None:
    assert len(VALIDATOR.HEADER) == 46
    assert len(set(VALIDATOR.HEADER)) == 46


def test_legacy_contract_contains_96_configurations() -> None:
    assert len(VALIDATOR.LEGACY_KEYS) == EXPECTED_LEGACY_ROWS


def test_ab_contract_contains_192_configurations() -> None:
    assert len(VALIDATOR.AB_KEYS) == EXPECTED_AB_ROWS


def test_accepts_complete_legacy_96_matrix(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy-96.csv"
    write_csv(path, legacy_matrix())

    result = validate_file(
        path,
        EXPECTED_LEGACY_ROWS,
        "LEGACY_96",
    )

    assert result["split_policies"] == [LEGACY_POLICY]
    assert result["verdict_counts"]["IMPROVEMENT"] == 96


def test_accepts_complete_ab_192_matrix(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ab-192.csv"
    write_csv(path, ab_matrix())

    result = validate_file(
        path,
        EXPECTED_AB_ROWS,
        "AB_192",
    )

    assert result["split_policies"] == sorted(AB_POLICIES)
    assert result["verdict_counts"]["IMPROVEMENT"] == 192


def test_rejects_incomplete_legacy_matrix(
    tmp_path: Path,
) -> None:
    rows = legacy_matrix()
    rows.pop()

    path = tmp_path / "legacy-missing.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="expected 96",
    ):
        VALIDATOR.validate(path, run_id=RUN_ID)


def test_rejects_incomplete_ab_matrix(
    tmp_path: Path,
) -> None:
    rows = ab_matrix()
    rows.pop()

    path = tmp_path / "ab-missing.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="expected 192",
    ):
        VALIDATOR.validate(path, run_id=RUN_ID)


def test_rejects_duplicate_legacy_configuration(
    tmp_path: Path,
) -> None:
    rows = legacy_matrix()
    rows[-1] = dict(rows[0])

    path = tmp_path / "legacy-duplicate.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="duplicate",
    ):
        VALIDATOR.validate(path, run_id=RUN_ID)


def test_rejects_duplicate_ab_configuration(
    tmp_path: Path,
) -> None:
    rows = ab_matrix()
    rows[-1] = dict(rows[0])

    path = tmp_path / "ab-duplicate.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="duplicate",
    ):
        VALIDATOR.validate(path, run_id=RUN_ID)


def test_rejects_mixed_run_ids(
    tmp_path: Path,
) -> None:
    rows = legacy_matrix()
    rows[-1]["run_id"] = "another-run"

    path = tmp_path / "mixed-run.csv"
    write_csv(path, rows)

    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path, run_id=RUN_ID)


def test_rejects_mixed_workflow_run_ids(
    tmp_path: Path,
) -> None:
    rows = legacy_matrix()
    rows[-1]["workflow_run_id"] = "999999"

    path = tmp_path / "mixed-workflow.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="mixes workflow or commit provenance",
    ):
        VALIDATOR.validate(path, run_id=RUN_ID)


def test_rejects_mixed_commit_sha(
    tmp_path: Path,
) -> None:
    rows = legacy_matrix()
    rows[-1]["commit_sha"] = "b" * 40

    path = tmp_path / "mixed-commit.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="mixes workflow or commit provenance",
    ):
        VALIDATOR.validate(path, run_id=RUN_ID)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("workload_id", "UNKNOWN", "unsupported workload_id"),
        ("parallelism", "3", "unsupported parallelism"),
        ("threshold_rows", "4096.0", "nonnegative integer"),
        ("dimension", "0", "dimension must be at least 100"),
        ("non_zero_count", "0", "non_zero_count must be positive"),
        ("commit_sha", "invalid", "40-character lowercase SHA-1"),
        ("workflow_run_id", "run-123", "decimal digits only"),
        (
            "timestamp",
            "2026-10-25T10:00:00",
            "timezone",
        ),
        ("status", "FAIL", "row status must be PASS"),
        ("sequential_mean_ms", "nan", "must be finite"),
        (
            "parallel_mean_ms",
            "0",
            "parallel_mean_ms must be positive",
        ),
        (
            "max_absolute_error",
            "1e-4",
            "numerical error exceeds",
        ),
        ("free_jvm_heap_bytes", "5000000000", "exceeds"),
    ],
)
def test_rejects_invalid_row_fields(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    rows = legacy_matrix()
    rows[0][field] = value

    path = tmp_path / f"invalid-{field}.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match=message,
    ):
        VALIDATOR.validate(path, run_id=RUN_ID)


def test_rejects_incorrect_speedup(
    tmp_path: Path,
) -> None:
    rows = legacy_matrix()
    rows[0]["speedup"] = "3.0"

    path = tmp_path / "wrong-speedup.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="speedup mismatch",
    ):
        VALIDATOR.validate(path, run_id=RUN_ID)


def test_rejects_incorrect_throughput(
    tmp_path: Path,
) -> None:
    rows = legacy_matrix()
    rows[0]["sequential_nnz_per_second"] = "123"

    path = tmp_path / "wrong-throughput.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="sequential_nnz_per_second mismatch",
    ):
        VALIDATOR.validate(path, run_id=RUN_ID)


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


def test_rejects_incorrect_verdict(
    tmp_path: Path,
) -> None:
    rows = legacy_matrix()
    rows[0]["verdict"] = "REGRESSION"

    path = tmp_path / "wrong-verdict.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="verdict mismatch",
    ):
        VALIDATOR.validate(path, run_id=RUN_ID)


def test_rejects_wrong_csv_header(
    tmp_path: Path,
) -> None:
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


def test_rejects_uniform_workload_with_wrong_nnz(
    tmp_path: Path,
) -> None:
    rows = legacy_matrix()
    rows[0]["non_zero_count"] = "201"

    path = tmp_path / "wrong-uniform-nnz.csv"
    write_csv(path, rows)

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="requires NNZ",
    ):
        VALIDATOR.validate(path, run_id=RUN_ID)


def test_rejects_symlink_csv(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.csv"
    write_csv(target, legacy_matrix())

    link = tmp_path / "link.csv"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable.")

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="symlink",
    ):
        VALIDATOR.validate(link)
