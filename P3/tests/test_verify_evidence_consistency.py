#!/usr/bin/env python3
"""Regression tests for the P3 V2/V3 evidence consistency verifier.

V2 tests use the real project validator and Markdown summary generator.
V3 tests use the real project V3 validator.

The tests verify:
- V2 CSV and validator JSON compatibility;
- V2 validator JSON and summary generator compatibility;
- six-file run-specific SHA-256 inventory;
- RUN_ID / workflow / commit identity binding;
- V3 A/B and legacy evidence validation;
- fail-closed behavior for tampering and malformed evidence.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "verify_evidence_consistency.py"

V2_VALIDATOR_SOURCE = ROOT / "results" / "validate_benchmark.py"
V2_GENERATOR_SOURCE = ROOT / "results" / "generate_benchmark_summary.py"
V3_VALIDATOR_SOURCE = ROOT / "results" / "validate_benchmark_v3.py"

RUN_ID = "p3-12345-1"
COMMIT = "a" * 40
WORKFLOW = "12345"

V2_DIMENSION = 1_000_000
V2_NNZ = 2 * V2_DIMENSION

V2_IDENTITY_KEYS = {
    "P3_RUN_ID": RUN_ID,
    "P3_WORKFLOW_RUN_ID": WORKFLOW,
    "P3_SOURCE_COMMIT": COMMIT,
    "P3_V2_DIMENSION": str(V2_DIMENSION),
    "P3_V3_DIMENSION": "4096",
}

V2_CHECKSUM_PATHS = {
    "benchmarks/benchmark_results_v2.csv",
    f"results/raw/{RUN_ID}/execution-identity.txt",
    f"results/raw/{RUN_ID}/benchmark-report.json",
    f"results/raw/{RUN_ID}/benchmark-report.txt",
    f"results/raw/{RUN_ID}/benchmark-report.md",
    f"results/raw/{RUN_ID}/validation-report.json",
}

V3_HEADER = [
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


def load_module(path: Path, name: str):
    """Load a Python module from an exact source path."""

    assert path.is_file(), f"Required source file is missing: {path}"

    spec = importlib.util.spec_from_file_location(name, path)

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


verifier = load_module(
    TOOL,
    "test_evidence_verifier",
)

v2_validator = load_module(
    V2_VALIDATOR_SOURCE,
    "test_authoritative_v2_validator",
)

summary_generator = load_module(
    V2_GENERATOR_SOURCE,
    "test_authoritative_v2_summary_generator",
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def checksum(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def write_checksums(
    p3: Path,
    checksum_path: Path,
    names: set[str],
) -> None:
    """Write a deterministic SHA-256 inventory."""

    lines = []

    for name in sorted(names):
        target = p3 / name

        assert target.is_file(), (
            f"Cannot checksum missing test fixture: {target}"
        )

        lines.append(
            f"{checksum(target)}  {name}"
        )

    checksum_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    checksum_path.write_text(
        "\n".join(lines) + "\n",
        encoding="ascii",
    )


def write_identity(
    path: Path,
    overrides: dict[str, str] | None = None,
) -> None:
    identity = dict(V2_IDENTITY_KEYS)

    if overrides:
        identity.update(overrides)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        "\n".join(
            f"{key}={value}"
            for key, value in identity.items()
        ) + "\n",
        encoding="utf-8",
    )


def v2_row(
    *,
    run_id: str = RUN_ID,
    dimension: int = V2_DIMENSION,
    benchmark_id: str | None = None,
) -> dict[str, str]:
    """Create one structurally complete, validator-compatible V2 row."""

    if benchmark_id is None:
        benchmark_id = v2_validator.expected_benchmark_id(
            dimension
        )

    sequential_mean = 10.0
    parallel_mean = 5.0

    return {
        "timestamp": "2026-10-30T10:00:00Z",
        "run_id": run_id,
        "benchmark_id": benchmark_id,
        "dimension": str(dimension),
        "non_zero_count": str(2 * dimension),
        "parallelism": "2",
        "threshold": "4096",
        "warmup_iterations": "5",
        "measured_iterations": "10",
        "sequential_mean_ms": str(sequential_mean),
        "sequential_median_ms": str(sequential_mean),
        "sequential_stddev_ms": "0",
        "parallel_mean_ms": str(parallel_mean),
        "parallel_median_ms": str(parallel_mean),
        "parallel_stddev_ms": "0",
        "speedup": str(sequential_mean / parallel_mean),
        "sequential_throughput_states_per_s": str(
            dimension / (sequential_mean / 1000.0)
        ),
        "parallel_throughput_states_per_s": str(
            dimension / (parallel_mean / 1000.0)
        ),
        "sequential_expected_error": "0",
        "parallel_expected_error": "0",
        "max_absolute_error": "0",
        "setup_time_ms": "0",
        "cpu": "test-cpu",
        "max_jvm_memory_bytes": "1000000000",
        "free_jvm_heap_bytes": "500000000",
        "java_version": "21",
        "operating_system": "Linux",
        "notes": "automated-test",
    }


def write_v2_csv(
    path: Path,
    rows: list[dict[str, str]] | None = None,
) -> None:
    """Write the exact canonical V2 header and supplied records."""

    if rows is None:
        rows = [v2_row()]

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=v2_validator.HEADER,
            extrasaction="raise",
        )

        writer.writeheader()
        writer.writerows(rows)


def v3_row(
    workload: str,
    policy: str,
    parallelism: int,
    threshold: int,
) -> dict[str, str]:
    dimension = 4096

    density = {
        "UNIFORM_2": 2,
        "UNIFORM_20": 20,
        "UNIFORM_100": 100,
    }.get(workload, 2)

    nnz = dimension * density

    sequential_mean = 10.0
    parallel_mean = 5.0

    return {
        "timestamp": "2026-10-26T10:00:00Z",
        "run_id": RUN_ID,
        "workflow_run_id": WORKFLOW,
        "commit_sha": COMMIT,
        "benchmark_id": "P3-V3",
        "workload_id": workload,
        "matrix_family": "CSR",
        "distribution": workload,
        "dimension": str(dimension),
        "non_zero_count": str(nnz),
        "nnz_min_per_row": str(density),
        "nnz_avg_per_row": str(density),
        "nnz_max_per_row": str(density),
        "parallelism": str(parallelism),
        "threshold_rows": str(threshold),
        "parallel_strategy": "FORK_JOIN",
        "split_policy": policy,
        "warmup_iterations": "1",
        "measured_iterations": "2",
        "sequential_mean_ms": str(sequential_mean),
        "sequential_median_ms": str(sequential_mean),
        "sequential_stddev_ms": "0",
        "sequential_min_ms": str(sequential_mean),
        "sequential_max_ms": str(sequential_mean),
        "parallel_mean_ms": str(parallel_mean),
        "parallel_median_ms": str(parallel_mean),
        "parallel_stddev_ms": "0",
        "parallel_min_ms": str(parallel_mean),
        "parallel_max_ms": str(parallel_mean),
        "speedup": str(sequential_mean / parallel_mean),
        "sequential_rows_per_second": str(
            dimension / (sequential_mean / 1000.0)
        ),
        "parallel_rows_per_second": str(
            dimension / (parallel_mean / 1000.0)
        ),
        "sequential_nnz_per_second": str(
            nnz / (sequential_mean / 1000.0)
        ),
        "parallel_nnz_per_second": str(
            nnz / (parallel_mean / 1000.0)
        ),
        "sequential_expected_error": "0",
        "parallel_expected_error": "0",
        "max_absolute_error": "0",
        "setup_time_ms": "0",
        "cpu": "test-cpu",
        "max_jvm_memory_bytes": "1000000000",
        "free_jvm_heap_bytes": "500000000",
        "java_version": "21",
        "operating_system": "Linux",
        "status": "PASS",
        "verdict": "IMPROVEMENT",
        "notes": "automated-test",
    }


def make_v3_matrix(
    path: Path,
    policies: tuple[str, ...] = (
        "ROW_BOUNDARY_SCAN",
        "BINARY_NNZ_SPLIT",
    ),
) -> None:
    workloads = (
        "UNIFORM_2",
        "UNIFORM_20",
        "UNIFORM_100",
        "BANDED",
        "BLOCK",
        "POWERLAW",
    )

    rows = [
        v3_row(
            workload,
            policy,
            parallelism,
            threshold,
        )
        for workload in workloads
        for policy in policies
        for parallelism in (1, 2, 4, 8)
        for threshold in (1024, 2048, 4096, 8192)
    ]

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=V3_HEADER,
        )

        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def v2_package(tmp_path: Path) -> Path:
    """Create complete V2 evidence using the real validator and generator."""

    root = tmp_path
    p3 = root / "P3"

    raw = (
        p3
        / "results"
        / "raw"
        / RUN_ID
    )

    reports = p3 / "reports"
    csv_path = (
        p3
        / "benchmarks"
        / "benchmark_results_v2.csv"
    )

    raw.mkdir(parents=True)
    reports.mkdir(parents=True)

    write_v2_csv(csv_path)

    destination_validator = (
        p3
        / "results"
        / "validate_benchmark.py"
    )

    destination_validator.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        V2_VALIDATOR_SOURCE,
        destination_validator,
    )

    validation = v2_validator.validate(csv_path)

    assert validation["schema"] == "qflpn-benchmark-v2"
    assert validation["validation"] == "PASS"
    assert validation["all_records_valid"] is True

    latest = validation["latest_record"]

    assert latest["run_id"] == RUN_ID
    assert latest["benchmark_id"] == "QFLPN-1M"
    assert latest["dimension"] == V2_DIMENSION
    assert latest["nnz"] == V2_NNZ
    assert latest["speedup"] == 2.0
    assert latest["sequential_mean_ms"] == 10.0
    assert latest["parallel_mean_ms"] == 5.0
    assert latest["max_error"] == 0.0

    validation_path = raw / "validation-report.json"

    write_json(
        validation_path,
        validation,
    )

    write_json(
        reports / "validation-report.json",
        validation,
    )

    markdown = summary_generator.build_summary(
        csv_path,
        validation_path,
        expected_run_id=RUN_ID,
    )

    (raw / "benchmark-report.md").write_text(
        markdown,
        encoding="utf-8",
    )

    (reports / "benchmark-report.md").write_text(
        markdown,
        encoding="utf-8",
    )

    write_json(
        raw / "benchmark-report.json",
        {
            "run_id": RUN_ID,
            "dimension": V2_DIMENSION,
            "validation": "PASS",
        },
    )

    (raw / "benchmark-report.txt").write_text(
        "\n".join([
            "QFLPN P3 benchmark",
            f"RUN_ID={RUN_ID}",
            "Validation=PASS",
            "",
        ]),
        encoding="utf-8",
    )

    write_identity(
        raw / "execution-identity.txt"
    )

    write_checksums(
        p3,
        raw / "SHA256SUMS.txt",
        V2_CHECKSUM_PATHS,
    )

    return root


@pytest.fixture
def v3_package(tmp_path: Path) -> Path:
    """Create V3 evidence using the real V3 validator."""

    root = tmp_path
    p3 = root / "P3"
    reports = p3 / "reports"

    reports.mkdir(parents=True)

    v3_path = (
        p3
        / "benchmarks"
        / "benchmark_results_v3.csv"
    )

    make_v3_matrix(v3_path)

    destination_validator = (
        p3
        / "results"
        / "validate_benchmark_v3.py"
    )

    destination_validator.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        V3_VALIDATOR_SOURCE,
        destination_validator,
    )

    validator = load_module(
        destination_validator,
        "fixture_authoritative_v3_validator",
    )

    result = validator.validate(
        v3_path,
        run_id=RUN_ID,
        workflow_run_id=WORKFLOW,
        commit_sha=COMMIT,
    )

    write_json(
        reports / "benchmark-v3-validation.json",
        result,
    )

    write_checksums(
        p3,
        reports / "benchmark-v3-SHA256SUMS.txt",
        {"benchmarks/benchmark_results_v3.csv"},
    )

    return root


# ---------------------------------------------------------------------
# V2 schema and validator/generator compatibility
# ---------------------------------------------------------------------


def test_v2_header_matches_authoritative_validator() -> None:
    assert len(v2_validator.HEADER) == 28
    assert set(v2_validator.HEADER) == verifier.V2_REQUIRED


def test_v2_validator_json_has_generator_required_fields(
    v2_package: Path,
) -> None:
    report_path = (
        v2_package
        / "P3"
        / "results"
        / "raw"
        / RUN_ID
        / "validation-report.json"
    )

    report = read_json(report_path)
    latest = report["latest_record"]

    required = {
        "run_id",
        "benchmark_id",
        "dimension",
        "nnz",
        "speedup",
        "sequential_mean_ms",
        "parallel_mean_ms",
        "max_error",
    }

    assert required.issubset(latest)
    assert report["schema"] == "qflpn-benchmark-v2"
    assert report["validation"] == "PASS"
    assert report["all_records_valid"] is True


def test_v2_generator_accepts_authoritative_validator_report(
    v2_package: Path,
) -> None:
    p3 = v2_package / "P3"

    summary = summary_generator.build_summary(
        p3 / "benchmarks" / "benchmark_results_v2.csv",
        (
            p3
            / "results"
            / "raw"
            / RUN_ID
            / "validation-report.json"
        ),
        expected_run_id=RUN_ID,
    )

    assert "Validation: **PASS**" in summary
    assert RUN_ID in summary
    assert "QFLPN-1M" in summary
    assert "1000000" in summary
    assert "2000000" in summary


def test_v2_verifier_accepts_complete_evidence(
    v2_package: Path,
) -> None:
    result = verifier.verify_v2(
        v2_package,
        RUN_ID,
        WORKFLOW,
        COMMIT,
    )

    assert result["validation"] == "PASS"
    assert result["schema"] == "qflpn-benchmark-v2"
    assert result["run_id"] == RUN_ID
    assert result["dimension"] == V2_DIMENSION
    assert result["benchmark_id"] == "QFLPN-1M"
    assert result["nnz"] == V2_NNZ
    assert result["execution_identity"] == "PASS"
    assert result["authoritative_validator"] == "PASS"
    assert len(result["verified_checksums"]) == 6


def test_v2_persistent_report_equals_authoritative_report(
    v2_package: Path,
) -> None:
    p3 = v2_package / "P3"

    raw_report = read_json(
        p3
        / "results"
        / "raw"
        / RUN_ID
        / "validation-report.json"
    )

    persistent_report = read_json(
        p3
        / "reports"
        / "validation-report.json"
    )

    assert raw_report == persistent_report


def test_v2_rejects_validation_report_field_mismatch(
    v2_package: Path,
) -> None:
    p3 = v2_package / "P3"

    path = (
        p3
        / "results"
        / "raw"
        / RUN_ID
        / "validation-report.json"
    )

    report = read_json(path)
    report["latest_record"]["max_error"] = 0.5
    write_json(path, report)

    with pytest.raises(
        verifier.EvidenceError,
        match="differs from the authoritative",
    ):
        verifier.verify_v2(
            v2_package,
            RUN_ID,
            WORKFLOW,
            COMMIT,
        )


def test_v2_rejects_generator_markdown_without_run_id(
    v2_package: Path,
) -> None:
    p3 = v2_package / "P3"

    path = (
        p3
        / "results"
        / "raw"
        / RUN_ID
        / "benchmark-report.md"
    )

    path.write_text(
        "## QFLPN P3 benchmark summary\n\n"
        "- Validation: **PASS**\n",
        encoding="utf-8",
    )

    with pytest.raises(
        verifier.EvidenceError,
        match="RUN_ID",
    ):
        verifier.verify_v2(
            v2_package,
            RUN_ID,
            WORKFLOW,
            COMMIT,
        )


def test_v2_rejects_wrong_java_report_dimension(
    v2_package: Path,
) -> None:
    p3 = v2_package / "P3"

    path = (
        p3
        / "results"
        / "raw"
        / RUN_ID
        / "benchmark-report.json"
    )

    report = read_json(path)
    report["dimension"] = 10_000_000
    write_json(path, report)

    with pytest.raises(
        verifier.EvidenceError,
        match="dimension",
    ):
        verifier.verify_v2(
            v2_package,
            RUN_ID,
            WORKFLOW,
            COMMIT,
        )


# ---------------------------------------------------------------------
# V2 six-file checksum inventory
# ---------------------------------------------------------------------


def test_v2_checksum_inventory_contains_exactly_six_files(
    v2_package: Path,
) -> None:
    p3 = v2_package / "P3"

    verified = verifier.verify_checksums(
        p3,
        (
            p3
            / "results"
            / "raw"
            / RUN_ID
            / "SHA256SUMS.txt"
        ),
        V2_CHECKSUM_PATHS,
    )

    assert len(verified) == 6
    assert set(verified) == V2_CHECKSUM_PATHS


def test_v2_checksum_inventory_rejects_missing_execution_identity(
    v2_package: Path,
) -> None:
    p3 = v2_package / "P3"

    names = set(V2_CHECKSUM_PATHS)
    names.remove(
        f"results/raw/{RUN_ID}/execution-identity.txt"
    )

    sums = (
        p3
        / "results"
        / "raw"
        / RUN_ID
        / "SHA256SUMS.txt"
    )

    write_checksums(
        p3,
        sums,
        names,
    )

    with pytest.raises(
        verifier.EvidenceError,
        match="path set mismatch",
    ):
        verifier.verify_v2(
            v2_package,
            RUN_ID,
            WORKFLOW,
            COMMIT,
        )


def test_v2_checksum_inventory_rejects_unexpected_file(
    v2_package: Path,
) -> None:
    p3 = v2_package / "P3"

    extra = (
        p3
        / "results"
        / "raw"
        / RUN_ID
        / "unexpected.txt"
    )

    extra.write_text(
        "unexpected evidence\n",
        encoding="utf-8",
    )

    names = set(V2_CHECKSUM_PATHS)
    names.add(
        f"results/raw/{RUN_ID}/unexpected.txt"
    )

    write_checksums(
        p3,
        (
            p3
            / "results"
            / "raw"
            / RUN_ID
            / "SHA256SUMS.txt"
        ),
        names,
    )

    with pytest.raises(
        verifier.EvidenceError,
        match="path set mismatch",
    ):
        verifier.verify_v2(
            v2_package,
            RUN_ID,
            WORKFLOW,
            COMMIT,
        )


def test_v2_checksum_inventory_rejects_tampered_report(
    v2_package: Path,
) -> None:
    p3 = v2_package / "P3"

    report_path = (
        p3
        / "results"
        / "raw"
        / RUN_ID
        / "benchmark-report.txt"
    )

    original = report_path.read_text(
        encoding="utf-8"
    )

    assert f"RUN_ID={RUN_ID}" in original
    assert "Validation=PASS" in original

    report_path.write_text(
        original.replace(
            "QFLPN P3 benchmark",
            "QFLPN P3 benchmark tampered",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        verifier.EvidenceError,
        match="SHA-256",
    ):
        verifier.verify_v2(
            v2_package,
            RUN_ID,
            WORKFLOW,
            COMMIT,
        )


def test_v2_checksum_inventory_rejects_csv_tampering(
    v2_package: Path,
) -> None:
    p3 = v2_package / "P3"

    csv_path = (
        p3
        / "benchmarks"
        / "benchmark_results_v2.csv"
    )

    csv_path.write_text(
        csv_path.read_text(encoding="utf-8")
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(verifier.EvidenceError):
        verifier.verify_v2(
            v2_package,
            RUN_ID,
            WORKFLOW,
            COMMIT,
        )


# ---------------------------------------------------------------------
# V2 shared RUN_ID / commit / workflow identity
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [
        ("P3_RUN_ID", "another-run"),
        ("P3_WORKFLOW_RUN_ID", "99999"),
        ("P3_SOURCE_COMMIT", "b" * 40),
        ("P3_V2_DIMENSION", "10000000"),
    ],
)
def test_v2_rejects_execution_identity_mismatch(
    v2_package: Path,
    field: str,
    wrong_value: str,
) -> None:
    p3 = v2_package / "P3"

    identity_path = (
        p3
        / "results"
        / "raw"
        / RUN_ID
        / "execution-identity.txt"
    )

    write_identity(
        identity_path,
        {field: wrong_value},
    )

    with pytest.raises(
        verifier.EvidenceError,
        match="mismatch",
    ):
        verifier.verify_v2(
            v2_package,
            RUN_ID,
            WORKFLOW,
            COMMIT,
        )


def test_v2_rejects_wrong_requested_workflow(
    v2_package: Path,
) -> None:
    with pytest.raises(
        verifier.EvidenceError,
        match="P3_WORKFLOW_RUN_ID",
    ):
        verifier.verify_v2(
            v2_package,
            RUN_ID,
            "99999",
            COMMIT,
        )


def test_v2_rejects_wrong_requested_commit(
    v2_package: Path,
) -> None:
    with pytest.raises(
        verifier.EvidenceError,
        match="P3_SOURCE_COMMIT",
    ):
        verifier.verify_v2(
            v2_package,
            RUN_ID,
            WORKFLOW,
            "b" * 40,
        )


def test_v2_rejects_invalid_execution_identity_format(
    v2_package: Path,
) -> None:
    p3 = v2_package / "P3"

    identity_path = (
        p3
        / "results"
        / "raw"
        / RUN_ID
        / "execution-identity.txt"
    )

    write_identity(
        identity_path,
        {"P3_V2_DIMENSION": "../1000000"},
    )

    with pytest.raises(
        verifier.EvidenceError,
        match="Invalid execution identity",
    ):
        verifier.verify_v2(
            v2_package,
            RUN_ID,
            WORKFLOW,
            COMMIT,
        )


# ---------------------------------------------------------------------
# V2 canonical benchmark contract
# ---------------------------------------------------------------------


def test_v2_rejects_dimension_12_as_timed_benchmark(
    tmp_path: Path,
) -> None:
    path = tmp_path / "benchmark_results_v2.csv"

    write_v2_csv(
        path,
        [
            v2_row(
                dimension=12,
                benchmark_id="QFLPN-12",
            )
        ],
    )

    with pytest.raises(
        v2_validator.ValidationError,
        match="correctness fixture",
    ):
        v2_validator.validate(path)


def test_v2_rejects_noncanonical_benchmark_id(
    tmp_path: Path,
) -> None:
    path = tmp_path / "benchmark_results_v2.csv"

    write_v2_csv(
        path,
        [
            v2_row(
                benchmark_id="QFLPN-30M",
            )
        ],
    )

    with pytest.raises(
        v2_validator.ValidationError,
        match="canonical catalog",
    ):
        v2_validator.validate(path)


def test_v2_rejects_duplicate_run_id(
    tmp_path: Path,
) -> None:
    path = tmp_path / "benchmark_results_v2.csv"

    write_v2_csv(
        path,
        [
            v2_row(),
            v2_row(),
        ],
    )

    with pytest.raises(
        v2_validator.ValidationError,
        match="duplicate run_id",
    ):
        v2_validator.validate(path)


# ---------------------------------------------------------------------
# V3 evidence and validator regression tests
# ---------------------------------------------------------------------


def test_v3_header_has_exact_46_column_contract() -> None:
    assert len(V3_HEADER) == 46
    assert set(V3_HEADER) == verifier.V3_REQUIRED


def test_v3_matrix_has_192_records(tmp_path: Path) -> None:
    path = tmp_path / "benchmark_results_v3.csv"

    make_v3_matrix(path)

    rows = verifier.read_csv(
        path,
        verifier.V3_REQUIRED,
    )

    assert len(rows) == 192


def test_v3_legacy_matrix_has_96_records(
    tmp_path: Path,
) -> None:
    path = tmp_path / "benchmark_results_v3.csv"

    make_v3_matrix(
        path,
        policies=("ROW_BOUNDARY_SCAN",),
    )

    rows = verifier.read_csv(
        path,
        verifier.V3_REQUIRED,
    )

    assert len(rows) == 96


def test_v3_validator_accepts_complete_ab_matrix(
    v3_package: Path,
) -> None:
    result = verifier.verify_v3(
        v3_package,
        RUN_ID,
        COMMIT,
        WORKFLOW,
    )

    assert result["validation"] == "PASS"
    assert result["run_contract"] == "AB_192"
    assert result["validated_records"] == 192


def test_v3_rejects_wrong_commit(
    v3_package: Path,
) -> None:
    with pytest.raises(
        verifier.EvidenceError,
        match="commit",
    ):
        verifier.verify_v3(
            v3_package,
            RUN_ID,
            "b" * 40,
            WORKFLOW,
        )


def test_v3_rejects_wrong_workflow_id(
    v3_package: Path,
) -> None:
    with pytest.raises(
        verifier.EvidenceError,
        match="workflow",
    ):
        verifier.verify_v3(
            v3_package,
            RUN_ID,
            COMMIT,
            "99999",
        )


def test_v3_rejects_tampered_csv(
    v3_package: Path,
) -> None:
    path = (
        v3_package
        / "P3"
        / "benchmarks"
        / "benchmark_results_v3.csv"
    )

    content = path.read_text(
        encoding="utf-8"
    )

    path.write_text(
        content.replace(
            "IMPROVEMENT",
            "REGRESSION",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(verifier.EvidenceError):
        verifier.verify_v3(
            v3_package,
            RUN_ID,
            COMMIT,
            WORKFLOW,
        )


def test_v3_rejects_tampered_persistent_report(
    v3_package: Path,
) -> None:
    path = (
        v3_package
        / "P3"
        / "reports"
        / "benchmark-v3-validation.json"
    )

    report = read_json(path)
    report["run_id"] = "another-run"

    write_json(
        path,
        report,
    )

    with pytest.raises(
        verifier.EvidenceError,
        match="RUN_ID",
    ):
        verifier.verify_v3(
            v3_package,
            RUN_ID,
            COMMIT,
            WORKFLOW,
        )


# ---------------------------------------------------------------------
# Generic safety and checksum parser tests
# ---------------------------------------------------------------------


def test_run_id_validation() -> None:
    with pytest.raises(
        verifier.EvidenceError,
        match="RUN_ID",
    ):
        verifier.verify_evidence(
            Path("."),
            run_id="../unsafe",
            source_commit=COMMIT,
        )


def test_source_commit_validation() -> None:
    with pytest.raises(
        verifier.EvidenceError,
        match="SOURCE_COMMIT",
    ):
        verifier.verify_evidence(
            Path("."),
            run_id=RUN_ID,
            source_commit="not-a-commit",
        )


def test_checksum_parser_rejects_duplicate_entries(
    tmp_path: Path,
) -> None:
    p3 = tmp_path / "P3"

    target = (
        p3
        / "benchmarks"
        / "benchmark_results_v3.csv"
    )

    target.parent.mkdir(
        parents=True,
    )

    target.write_text(
        "test\n",
        encoding="utf-8",
    )

    digest = checksum(target)

    sums = (
        p3
        / "reports"
        / "benchmark-v3-SHA256SUMS.txt"
    )

    sums.parent.mkdir(
        parents=True,
    )

    line = (
        f"{digest}  benchmarks/benchmark_results_v3.csv\n"
    )

    sums.write_text(
        line + line,
        encoding="ascii",
    )

    with pytest.raises(
        verifier.EvidenceError,
        match="Duplicate",
    ):
        verifier.verify_checksums(
            p3,
            sums,
            {"benchmarks/benchmark_results_v3.csv"},
        )


def test_checksum_parser_rejects_path_traversal(
    tmp_path: Path,
) -> None:
    p3 = tmp_path / "P3"

    sums = (
        p3
        / "reports"
        / "sums.txt"
    )

    sums.parent.mkdir(
        parents=True,
    )

    sums.write_text(
        f"{'0' * 64}  ../outside\n",
        encoding="ascii",
    )

    with pytest.raises(verifier.EvidenceError):
        verifier.verify_checksums(
            p3,
            sums,
            {"../outside"},
        )


def test_checksum_parser_rejects_tampering(
    tmp_path: Path,
) -> None:
    p3 = tmp_path / "P3"

    target = (
        p3
        / "benchmarks"
        / "benchmark_results_v3.csv"
    )

    target.parent.mkdir(
        parents=True,
    )

    target.write_text(
        "original\n",
        encoding="utf-8",
    )

    sums = (
        p3
        / "reports"
        / "sums.txt"
    )

    sums.parent.mkdir(
        parents=True,
    )

    sums.write_text(
        (
            f"{checksum(target)}  "
            "benchmarks/benchmark_results_v3.csv\n"
        ),
        encoding="ascii",
    )

    target.write_text(
        "modified\n",
        encoding="utf-8",
    )

    with pytest.raises(
        verifier.EvidenceError,
        match="SHA-256",
    ):
        verifier.verify_checksums(
            p3,
            sums,
            {"benchmarks/benchmark_results_v3.csv"},
        )
