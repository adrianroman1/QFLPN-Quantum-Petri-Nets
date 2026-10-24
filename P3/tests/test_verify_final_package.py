"""Fail-closed tests for the independent P3 final package verifier."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "verify_final_package.py"
)

SPEC = importlib.util.spec_from_file_location(
    "p3_verify_final_package",
    MODULE_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

RUN_ID = "p3-test-100-1"
EXPECTED = {
    "dimension": 12,
    "warmup_iterations": 2,
    "measured_iterations": 3,
    "threshold": 4,
    "parallelism": 2,
}

CSV_HEADER = [
    "timestamp", "run_id", "benchmark_id", "dimension",
    "non_zero_count", "parallelism", "threshold",
    "warmup_iterations", "measured_iterations",
    "sequential_mean_ms", "sequential_median_ms",
    "sequential_stddev_ms", "parallel_mean_ms",
    "parallel_median_ms", "parallel_stddev_ms", "speedup",
    "sequential_throughput_states_per_s",
    "parallel_throughput_states_per_s",
    "sequential_expected_error", "parallel_expected_error",
    "max_absolute_error", "setup_time_ms", "cpu",
    "max_jvm_memory_bytes", "free_jvm_heap_bytes",
    "java_version", "operating_system", "notes",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def make_csv_row() -> dict[str, str]:
    seq_mean = 2.0
    par_mean = 1.0
    dimension = EXPECTED["dimension"]

    return {
        "timestamp": "2026-10-24T12:00:00+00:00",
        "run_id": RUN_ID,
        "benchmark_id": "QFLPN-12",
        "dimension": str(dimension),
        "non_zero_count": str(2 * dimension),
        "parallelism": str(EXPECTED["parallelism"]),
        "threshold": str(EXPECTED["threshold"]),
        "warmup_iterations": str(EXPECTED["warmup_iterations"]),
        "measured_iterations": str(EXPECTED["measured_iterations"]),
        "sequential_mean_ms": str(seq_mean),
        "sequential_median_ms": str(seq_mean),
        "sequential_stddev_ms": "0.0",
        "parallel_mean_ms": str(par_mean),
        "parallel_median_ms": str(par_mean),
        "parallel_stddev_ms": "0.0",
        "speedup": str(seq_mean / par_mean),
        "sequential_throughput_states_per_s": str(
            dimension / (seq_mean / 1000.0)
        ),
        "parallel_throughput_states_per_s": str(
            dimension / (par_mean / 1000.0)
        ),
        "sequential_expected_error": "0.0",
        "parallel_expected_error": "0.0",
        "max_absolute_error": "0.0",
        "setup_time_ms": "0.0",
        "cpu": "test-cpu",
        "max_jvm_memory_bytes": "1000000",
        "free_jvm_heap_bytes": "500000",
        "java_version": "21",
        "operating_system": "test-os",
        "notes": "test fixture",
    }


def create_fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    p3 = root / "P3"

    required_files = (
        "pom.xml",
        "results/run_benchmark.sh",
        "results/validate_benchmark.py",
        "results/test_validate_benchmark.py",
        "results/generate_benchmark_summary.py",
        "reports/environment.txt",
        "reports/benchmark-validator-tests.log",
        "reports/manifest-generator-tests.log",
        "reports/final-package-verifier-tests.log",
        "reports/python-validation-tests.log",
        "reports/root-maven-validation.log",
        "reports/p3-benchmark-execution.log",
    )

    for relative in required_files:
        path = p3 / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")

    csv_path = p3 / "benchmarks" / "benchmark_results_v2.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    row = make_csv_row()

    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerow(row)

    run_dir = p3 / "results" / "raw" / RUN_ID
    run_dir.mkdir(parents=True)

    for filename, content in (
        ("benchmark-report.txt", "Benchmark report\n"),
        ("benchmark-report.md", "# Benchmark report\n"),
        ("benchmark-report.json", '{"status":"generated"}\n'),
    ):
        (run_dir / filename).write_text(content, encoding="utf-8")

    latest = {
        "row": 1,
        "run_id": RUN_ID,
        "dimension": EXPECTED["dimension"],
        "nnz": 2 * EXPECTED["dimension"],
        "speedup": 2.0,
        "sequential_mean_ms": 2.0,
        "parallel_mean_ms": 1.0,
        "max_error": 0.0,
    }

    report = {
        "schema": "qflpn-benchmark-v2",
        "validation": "PASS",
        "records": 1,
        "all_records_valid": True,
        "latest_record": latest,
    }

    validation_report = run_dir / "validation-report.json"
    write_json(validation_report, report)

    run_checksum_targets = (
        "benchmarks/benchmark_results_v2.csv",
        f"results/raw/{RUN_ID}/benchmark-report.json",
        f"results/raw/{RUN_ID}/benchmark-report.md",
        f"results/raw/{RUN_ID}/benchmark-report.txt",
        f"results/raw/{RUN_ID}/validation-report.json",
    )

    checksum_content = "".join(
        f"{sha256(p3 / relative)}  {relative}\n"
        for relative in sorted(run_checksum_targets)
    )

    (run_dir / "SHA256SUMS.txt").write_text(
        checksum_content,
        encoding="ascii",
    )

    outcomes = {
        stage: "success"
        for stage in MODULE.REQUIRED_CI_STAGES
    }
    outcomes_path = tmp_path / "ci-outcomes.json"
    write_json(outcomes_path, outcomes)

    # Generate the global inventory only after all fixture evidence exists.
    manifest_paths = MODULE.independent_inventory(root)
    manifest = "".join(path + "\n" for path in manifest_paths)
    (p3 / "MANIFEST.txt").write_text(manifest, encoding="utf-8")

    checksums = "".join(
        f"{sha256(root / relative)}  {relative}\n"
        for relative in manifest_paths
    )
    (p3 / "SHA256SUMS.txt").write_text(
        checksums,
        encoding="ascii",
    )

    return root, outcomes_path


def test_complete_valid_package_is_accepted(tmp_path: Path) -> None:
    root, outcomes = create_fixture(tmp_path)

    result = MODULE.verify_package(
        root,
        RUN_ID,
        EXPECTED,
        outcomes,
    )

    assert result["verdict"] == "P3_ACCEPTED"
    assert result["integrity"]["manifest_entries"] > 0
    assert result["integrity"]["manifest_entries"] == (
        result["integrity"]["sha256_entries_verified"]
    )
    assert result["benchmark"]["run_id"] == RUN_ID
    assert result["benchmark"]["schema"] == "qflpn-benchmark-v2"


def test_manifest_must_not_contain_headers_or_count(tmp_path: Path) -> None:
    root, outcomes = create_fixture(tmp_path)
    manifest = root / "P3" / "MANIFEST.txt"

    manifest.write_text(
        "# P3 manifest\n# File count: 1\nP3/pom.xml\n",
        encoding="utf-8",
    )

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError:
        pass
    else:
        raise AssertionError("P1-style manifest must contain paths only")


def test_manifest_and_checksums_must_exclude_each_other(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    manifest = root / "P3" / "MANIFEST.txt"
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + "P3/MANIFEST.txt\n",
        encoding="utf-8",
    )

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError:
        pass
    else:
        raise AssertionError("Self-referential manifest entry must fail")


def test_modified_source_file_fails_global_hash_check(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    source = root / "P3" / "pom.xml"
    source.write_text("tampered\n", encoding="utf-8")

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError as exc:
        assert "SHA-256 mismatch" in str(exc)
    else:
        raise AssertionError("Modified source must fail verification")


def test_missing_manifest_fails_closed(tmp_path: Path) -> None:
    root, outcomes = create_fixture(tmp_path)
    (root / "P3" / "MANIFEST.txt").unlink()

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError:
        pass
    else:
        raise AssertionError("Missing manifest must fail")


def test_missing_checksum_file_fails_closed(tmp_path: Path) -> None:
    root, outcomes = create_fixture(tmp_path)
    (root / "P3" / "SHA256SUMS.txt").unlink()

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError:
        pass
    else:
        raise AssertionError("Missing SHA256SUMS must fail")


def test_checksum_path_set_must_equal_manifest_path_set(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    checksum_path = root / "P3" / "SHA256SUMS.txt"
    checksum_path.write_text("", encoding="ascii")

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError as exc:
        assert "path sets differ" in str(exc)
    else:
        raise AssertionError("Different path sets must fail")


def test_wrong_run_id_fails_benchmark_verification(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    try:
        MODULE.verify_package(
            root,
            "p3-wrong-run",
            EXPECTED,
            outcomes,
        )
    except MODULE.VerificationError:
        pass
    else:
        raise AssertionError("Wrong RUN_ID must fail")


def test_csv_json_run_id_mismatch_fails(tmp_path: Path) -> None:
    root, outcomes = create_fixture(tmp_path)

    report_path = (
        root / "P3" / "results" / "raw" / RUN_ID
        / "validation-report.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["latest_record"]["run_id"] = "different-run"
    write_json(report_path, report)

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError:
        pass
    else:
        raise AssertionError("CSV/JSON run mismatch must fail")


def test_invalid_benchmark_report_status_fails(tmp_path: Path) -> None:
    root, outcomes = create_fixture(tmp_path)

    report_path = (
        root / "P3" / "results" / "raw" / RUN_ID
        / "validation-report.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["validation"] = "FAIL"
    write_json(report_path, report)

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError:
        pass
    else:
        raise AssertionError("Failed benchmark report must fail")


def test_missing_run_evidence_fails(tmp_path: Path) -> None:
    root, outcomes = create_fixture(tmp_path)

    evidence = (
        root / "P3" / "results" / "raw" / RUN_ID
        / "benchmark-report.md"
    )
    evidence.unlink()

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError:
        pass
    else:
        raise AssertionError("Missing benchmark evidence must fail")


def test_modified_run_evidence_fails_its_checksum(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    evidence = (
        root / "P3" / "results" / "raw" / RUN_ID
        / "benchmark-report.txt"
    )
    evidence.write_text("tampered report\n", encoding="utf-8")

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError as exc:
        assert "run-specific SHA-256 mismatch" in str(exc)
    else:
        raise AssertionError("Modified run evidence must fail")


def test_failed_ci_stage_rejects_package(tmp_path: Path) -> None:
    root, outcomes = create_fixture(tmp_path)

    value = json.loads(outcomes.read_text(encoding="utf-8"))
    value["p3_benchmark"] = "failure"
    write_json(outcomes, value)

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError as exc:
        assert "p3_benchmark" in str(exc)
    else:
        raise AssertionError("Failed CI stage must reject package")


def test_missing_ci_stage_rejects_package(tmp_path: Path) -> None:
    root, outcomes = create_fixture(tmp_path)

    value = json.loads(outcomes.read_text(encoding="utf-8"))
    del value["p3_display_sha256"]
    write_json(outcomes, value)

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError as exc:
        assert "p3_display_sha256" in str(exc)
    else:
        raise AssertionError("Missing mandatory CI stage must fail")


def test_invalid_run_id_is_rejected(tmp_path: Path) -> None:
    root, outcomes = create_fixture(tmp_path)

    try:
        MODULE.verify_package(
            root,
            "../unsafe",
            EXPECTED,
            outcomes,
        )
    except MODULE.VerificationError:
        pass
    else:
        raise AssertionError("Unsafe RUN_ID must fail")


def test_invalid_ci_outcomes_json_fails(tmp_path: Path) -> None:
    root, _ = create_fixture(tmp_path)
    outcomes = tmp_path / "bad-outcomes.json"
    outcomes.write_text("{invalid", encoding="utf-8")

    try:
        MODULE.verify_package(root, RUN_ID, EXPECTED, outcomes)
    except MODULE.VerificationError:
        pass
    else:
        raise AssertionError("Malformed CI outcomes JSON must fail")
