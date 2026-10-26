#!/usr/bin/env python3
"""Regression tests for the P3 V2/V3 evidence consistency verifier."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "verify_evidence_consistency.py"

spec = importlib.util.spec_from_file_location("evidence_verifier", TOOL)
assert spec is not None and spec.loader is not None
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)

RUN_ID = "p3-12345-1"
COMMIT = "a" * 40
WORKFLOW = "12345"

V3_HEADER = [
    "timestamp", "run_id", "workflow_run_id", "commit_sha",
    "benchmark_id", "workload_id", "matrix_family", "distribution",
    "dimension", "non_zero_count", "nnz_min_per_row",
    "nnz_avg_per_row", "nnz_max_per_row", "parallelism",
    "threshold_rows", "parallel_strategy", "split_policy",
    "warmup_iterations", "measured_iterations",
    "sequential_mean_ms", "sequential_median_ms",
    "sequential_stddev_ms", "sequential_min_ms",
    "sequential_max_ms", "parallel_mean_ms", "parallel_median_ms",
    "parallel_stddev_ms", "parallel_min_ms", "parallel_max_ms",
    "speedup", "sequential_rows_per_second",
    "parallel_rows_per_second", "sequential_nnz_per_second",
    "parallel_nnz_per_second", "sequential_expected_error",
    "parallel_expected_error", "max_absolute_error",
    "setup_time_ms", "cpu", "max_jvm_memory_bytes",
    "free_jvm_heap_bytes", "java_version", "operating_system",
    "status", "verdict", "notes",
]


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_checksums(p3: Path, path: Path, names: set[str]) -> None:
    lines = []
    for name in sorted(names):
        target = p3 / name
        lines.append(f"{checksum(target)}  {name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def v3_row(workload: str, policy: str, parallelism: int, threshold: int) -> dict:
    dimension = 4096
    density = {"UNIFORM_2": 2, "UNIFORM_20": 20, "UNIFORM_100": 100}.get(workload, 2)
    nnz = dimension * density
    seq = 10.0
    par = 5.0
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
        "sequential_mean_ms": str(seq),
        "sequential_median_ms": str(seq),
        "sequential_stddev_ms": "0",
        "sequential_min_ms": str(seq),
        "sequential_max_ms": str(seq),
        "parallel_mean_ms": str(par),
        "parallel_median_ms": str(par),
        "parallel_stddev_ms": "0",
        "parallel_min_ms": str(par),
        "parallel_max_ms": str(par),
        "speedup": str(seq / par),
        "sequential_rows_per_second": str(dimension / (seq / 1000)),
        "parallel_rows_per_second": str(dimension / (par / 1000)),
        "sequential_nnz_per_second": str(nnz / (seq / 1000)),
        "parallel_nnz_per_second": str(nnz / (par / 1000)),
        "sequential_expected_error": "0",
        "parallel_expected_error": "0",
        "max_absolute_error": "0",
        "setup_time_ms": "0",
        "cpu": "test-cpu",
        "max_jvm_memory_bytes": "1000000",
        "free_jvm_heap_bytes": "500000",
        "java_version": "21",
        "operating_system": "Linux",
        "status": "PASS",
        "verdict": "IMPROVEMENT",
        "notes": "automated-test",
    }


def make_v3_matrix(path: Path, policies=("ROW_BOUNDARY_SCAN", "BINARY_NNZ_SPLIT")) -> None:
    workloads = ("UNIFORM_2", "UNIFORM_20", "UNIFORM_100", "BANDED", "BLOCK", "POWERLAW")
    rows = [
        v3_row(workload, policy, parallelism, threshold)
        for workload in workloads
        for policy in policies
        for parallelism in (1, 2, 4, 8)
        for threshold in (1024, 2048, 4096, 8192)
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=V3_HEADER)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def package(tmp_path: Path) -> Path:
    root = tmp_path
    p3 = root / "P3"
    raw = p3 / "results" / "raw" / RUN_ID
    reports = p3 / "reports"
    raw.mkdir(parents=True)
    reports.mkdir(parents=True)

    write_json(reports / "environment.json", {
        "schema": "qflpn-p3-environment-v1",
        "run_id": RUN_ID,
        "repository": {"commit": COMMIT},
        "benchmark": {"dimension": 4096, "warmup_iterations": 1, "measured_iterations": 2},
    })

    v3_path = p3 / "benchmarks" / "benchmark_results_v3.csv"
    make_v3_matrix(v3_path)

    # V3 validator is copied from the checked-out project so the test exercises
    # the actual authoritative validator, not a mock.
    source_validator = ROOT / "results" / "validate_benchmark_v3.py"
    destination_validator = p3 / "results" / "validate_benchmark_v3.py"
    destination_validator.parent.mkdir(parents=True, exist_ok=True)
    destination_validator.write_bytes(source_validator.read_bytes())

    spec_v3 = importlib.util.spec_from_file_location("test_v3_validator", destination_validator)
    assert spec_v3 is not None and spec_v3.loader is not None
    module = importlib.util.module_from_spec(spec_v3)
    spec_v3.loader.exec_module(module)
    result = module.validate(
        v3_path, run_id=RUN_ID, workflow_run_id=WORKFLOW, commit_sha=COMMIT
    )
    write_json(reports / "benchmark-v3-validation.json", result)

    write_checksums(
        p3,
        reports / "benchmark-v3-SHA256SUMS.txt",
        {"benchmarks/benchmark_results_v3.csv"},
    )

    # V2 evidence is intentionally not fabricated: V2 remains tested by
    # the existing V2 benchmark validator tests. This fixture verifies the
    # V3-specific helper independently.
    return root


def test_v3_csv_has_exact_46_column_contract() -> None:
    assert len(V3_HEADER) == 46
    assert set(V3_HEADER) == verifier.V3_REQUIRED


def test_v3_matrix_has_192_records(tmp_path: Path) -> None:
    path = tmp_path / "benchmark_results_v3.csv"
    make_v3_matrix(path)
    rows = verifier.read_csv(path, verifier.V3_REQUIRED)
    assert len(rows) == 192


def test_v3_legacy_matrix_has_96_records(tmp_path: Path) -> None:
    path = tmp_path / "benchmark_results_v3.csv"
    make_v3_matrix(path, policies=("ROW_BOUNDARY_SCAN",))
    rows = verifier.read_csv(path, verifier.V3_REQUIRED)
    assert len(rows) == 96


def test_v3_validator_accepts_complete_ab_matrix(package: Path) -> None:
    p3 = package / "P3"
    result = verifier.verify_v3(package, RUN_ID, COMMIT, WORKFLOW)
    assert result["validation"] == "PASS"
    assert result["run_contract"] == "AB_192"
    assert result["validated_records"] == 192


def test_v3_rejects_wrong_commit(package: Path) -> None:
    with pytest.raises(verifier.EvidenceError, match="commit"):
        verifier.verify_v3(package, RUN_ID, "b" * 40, WORKFLOW)


def test_v3_rejects_wrong_workflow_id(package: Path) -> None:
    with pytest.raises(verifier.EvidenceError, match="workflow"):
        verifier.verify_v3(package, RUN_ID, COMMIT, "99999")


def test_v3_rejects_tampered_csv(package: Path) -> None:
    path = package / "P3" / "benchmarks" / "benchmark_results_v3.csv"
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace("IMPROVEMENT", "REGRESSION", 1), encoding="utf-8")
    with pytest.raises(verifier.EvidenceError):
        verifier.verify_v3(package, RUN_ID, COMMIT, WORKFLOW)


def test_v3_rejects_tampered_persistent_report(package: Path) -> None:
    path = package / "P3" / "reports" / "benchmark-v3-validation.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["run_id"] = "another-run"
    write_json(path, report)
    with pytest.raises(verifier.EvidenceError, match="RUN_ID"):
        verifier.verify_v3(package, RUN_ID, COMMIT, WORKFLOW)


def test_run_id_validation() -> None:
    with pytest.raises(verifier.EvidenceError, match="RUN_ID"):
        verifier.verify_evidence(
            Path("."), run_id="../unsafe", source_commit=COMMIT
        )


def test_source_commit_validation() -> None:
    with pytest.raises(verifier.EvidenceError, match="SOURCE_COMMIT"):
        verifier.verify_evidence(
            Path("."), run_id=RUN_ID, source_commit="not-a-commit"
        )


def test_checksum_parser_rejects_duplicate_entries(tmp_path: Path) -> None:
    p3 = tmp_path / "P3"
    target = p3 / "benchmarks" / "benchmark_results_v3.csv"
    target.parent.mkdir(parents=True)
    target.write_text("test\n", encoding="utf-8")
    digest = checksum(target)
    sums = p3 / "reports" / "benchmark-v3-SHA256SUMS.txt"
    sums.parent.mkdir(parents=True)
    line = f"{digest}  benchmarks/benchmark_results_v3.csv\n"
    sums.write_text(line + line, encoding="ascii")
    with pytest.raises(verifier.EvidenceError, match="Duplicate"):
        verifier.verify_checksums(
            p3, sums, {"benchmarks/benchmark_results_v3.csv"}
        )


def test_checksum_parser_rejects_path_traversal(tmp_path: Path) -> None:
    p3 = tmp_path / "P3"
    sums = p3 / "reports" / "sums.txt"
    sums.parent.mkdir(parents=True)
    sums.write_text(f"{'0' * 64}  ../outside\n", encoding="ascii")
    with pytest.raises(verifier.EvidenceError):
        verifier.verify_checksums(p3, sums, {"../outside"})


def test_checksum_parser_rejects_tampering(tmp_path: Path) -> None:
    p3 = tmp_path / "P3"
    target = p3 / "benchmarks" / "benchmark_results_v3.csv"
    target.parent.mkdir(parents=True)
    target.write_text("original\n", encoding="utf-8")
    sums = p3 / "reports" / "sums.txt"
    sums.parent.mkdir(parents=True)
    sums.write_text(
        f"{checksum(target)}  benchmarks/benchmark_results_v3.csv\n",
        encoding="ascii",
    )
    target.write_text("modified\n", encoding="utf-8")
    with pytest.raises(verifier.EvidenceError, match="SHA-256"):
        verifier.verify_checksums(
            p3, sums, {"benchmarks/benchmark_results_v3.csv"}
        )
