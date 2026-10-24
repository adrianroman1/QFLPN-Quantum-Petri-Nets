"""Fail-closed regression tests for the independent P3 package verifier.

The fixture uses the real P3 benchmark validator. It does not replace the
validator with a placeholder, mock, or simplified implementation.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "verify_final_package.py"
)

VALIDATOR_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "results"
    / "validate_benchmark.py"
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
    "timestamp",
    "run_id",
    "benchmark_id",
    "dimension",
    "non_zero_count",
    "parallelism",
    "threshold",
    "warmup_iterations",
    "measured_iterations",
    "sequential_mean_ms",
    "sequential_median_ms",
    "sequential_stddev_ms",
    "parallel_mean_ms",
    "parallel_median_ms",
    "parallel_stddev_ms",
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

REQUIRED_FIXTURE_FILES = (
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


def sha256(path: Path) -> str:
    """Calculate the SHA-256 digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write deterministic, strict JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def make_csv_row() -> dict[str, str]:
    """Create one valid qflpn-benchmark-v2 record."""
    dimension = EXPECTED["dimension"]
    sequential_mean = 2.0
    parallel_mean = 1.0

    return {
        "timestamp": "2026-10-24T12:00:00+00:00",
        "run_id": RUN_ID,
        "benchmark_id": "QFLPN-12",
        "dimension": str(dimension),
        "non_zero_count": str(2 * dimension),
        "parallelism": str(EXPECTED["parallelism"]),
        "threshold": str(EXPECTED["threshold"]),
        "warmup_iterations": str(EXPECTED["warmup_iterations"]),
        "measured_iterations": str(
            EXPECTED["measured_iterations"]
        ),
        "sequential_mean_ms": str(sequential_mean),
        "sequential_median_ms": str(sequential_mean),
        "sequential_stddev_ms": "0.0",
        "parallel_mean_ms": str(parallel_mean),
        "parallel_median_ms": str(parallel_mean),
        "parallel_stddev_ms": "0.0",
        "speedup": str(sequential_mean / parallel_mean),
        "sequential_throughput_states_per_s": str(
            dimension / (sequential_mean / 1000.0)
        ),
        "parallel_throughput_states_per_s": str(
            dimension / (parallel_mean / 1000.0)
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


def write_csv(path: Path, row: dict[str, str]) -> None:
    """Write a canonical V2 CSV containing exactly one record."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=CSV_HEADER,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerow(row)


def write_run_checksums(
    p3_root: Path,
    run_id: str,
) -> None:
    """Generate the exact run-specific checksum set used by P3."""
    targets = (
        "benchmarks/benchmark_results_v2.csv",
        f"results/raw/{run_id}/benchmark-report.json",
        f"results/raw/{run_id}/benchmark-report.md",
        f"results/raw/{run_id}/benchmark-report.txt",
        f"results/raw/{run_id}/validation-report.json",
    )

    lines = []

    for relative in sorted(targets):
        digest = sha256(p3_root / relative)
        lines.append(f"{digest}  {relative}")

    checksum_path = (
        p3_root
        / "results"
        / "raw"
        / run_id
        / "SHA256SUMS.txt"
    )

    checksum_path.write_text(
        "".join(line + "\n" for line in lines),
        encoding="ascii",
    )


def write_global_integrity(root: Path) -> None:
    """Create the P1-compatible global P3 inventory."""
    p3_root = root / "P3"

    manifest_paths = MODULE.independent_inventory(root)

    manifest_content = "".join(
        relative + "\n"
        for relative in manifest_paths
    )

    (p3_root / "MANIFEST.txt").write_text(
        manifest_content,
        encoding="utf-8",
    )

    checksum_lines = []

    for relative in manifest_paths:
        digest = sha256(root / relative)
        checksum_lines.append(f"{digest}  {relative}")

    (p3_root / "SHA256SUMS.txt").write_text(
        "".join(line + "\n" for line in checksum_lines),
        encoding="ascii",
    )


def create_fixture(
    tmp_path: Path,
) -> tuple[Path, Path]:
    """Create a complete isolated P3 repository fixture.

    The actual benchmark validator is copied from the checked-out P3
    source tree. This is essential because verify_benchmark() dynamically
    imports and executes validate_benchmark.py.
    """
    if not VALIDATOR_SOURCE.is_file():
        raise AssertionError(
            "The real P3/results/validate_benchmark.py is missing"
        )

    root = tmp_path / "repository"
    p3_root = root / "P3"

    p3_root.mkdir(parents=True)

    # Create the required package paths.
    for relative in REQUIRED_FIXTURE_FILES:
        path = p3_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)

        if relative == "results/validate_benchmark.py":
            continue

        path.write_text(
            "P3 package test fixture\n",
            encoding="utf-8",
        )

    # Copy the real authoritative validator.
    validator_destination = (
        p3_root / "results" / "validate_benchmark.py"
    )
    shutil.copyfile(
        VALIDATOR_SOURCE,
        validator_destination,
    )

    # Create the canonical V2 benchmark CSV.
    csv_path = (
        p3_root
        / "benchmarks"
        / "benchmark_results_v2.csv"
    )

    row = make_csv_row()
    write_csv(csv_path, row)

    # Create run-specific benchmark evidence.
    run_directory = (
        p3_root
        / "results"
        / "raw"
        / RUN_ID
    )
    run_directory.mkdir(parents=True, exist_ok=True)

    (run_directory / "benchmark-report.txt").write_text(
        "P3 benchmark report\n",
        encoding="utf-8",
    )

    (run_directory / "benchmark-report.md").write_text(
        "# P3 benchmark report\n",
        encoding="utf-8",
    )

    (run_directory / "benchmark-report.json").write_text(
        json.dumps(
            {
                "schema": "qflpn-benchmark-v2",
                "run_id": RUN_ID,
                "status": "generated",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Produce the validation report using the real validator.
    expected_latest = {
        "row": 1,
        "run_id": RUN_ID,
        "dimension": EXPECTED["dimension"],
        "nnz": 2 * EXPECTED["dimension"],
        "speedup": 2.0,
        "sequential_mean_ms": 2.0,
        "parallel_mean_ms": 1.0,
        "max_error": 0.0,
    }

    validation_report = {
        "schema": "qflpn-benchmark-v2",
        "validation": "PASS",
        "records": 1,
        "all_records_valid": True,
        "latest_record": expected_latest,
    }

    validation_report_path = (
        run_directory / "validation-report.json"
    )

    write_json(
        validation_report_path,
        validation_report,
    )

    # Verify the fixture CSV with the actual production validator.
    validator_spec = importlib.util.spec_from_file_location(
        "p3_fixture_authoritative_validator",
        validator_destination,
    )

    if (
        validator_spec is None
        or validator_spec.loader is None
    ):
        raise AssertionError(
            "Cannot load the real P3 benchmark validator"
        )

    validator_module = importlib.util.module_from_spec(
        validator_spec
    )
    validator_spec.loader.exec_module(validator_module)

    authoritative_result = validator_module.validate(
        csv_path,
        expected=EXPECTED,
    )

    assert authoritative_result["schema"] == "qflpn-benchmark-v2"
    assert authoritative_result["validation"] == "PASS"
    assert authoritative_result["all_records_valid"] is True
    assert authoritative_result["records"] == 1
    assert authoritative_result["latest_record"] == expected_latest

    # The run-specific checksum file is generated only after all
    # run-specific evidence has been written.
    write_run_checksums(p3_root, RUN_ID)

    # All mandatory CI stages are represented explicitly.
    outcomes = {
        stage: "success"
        for stage in MODULE.REQUIRED_CI_STAGES
    }

    outcomes_path = tmp_path / "ci-outcomes.json"
    write_json(outcomes_path, outcomes)

    # Global inventory is generated last, after all P3 fixture evidence.
    write_global_integrity(root)

    return root, outcomes_path


def expect_verification_failure(
    root: Path,
    run_id: str,
    outcomes: Path,
    message: str | None = None,
) -> None:
    """Assert that the final verifier rejects the supplied package."""
    try:
        MODULE.verify_package(
            root,
            run_id,
            EXPECTED,
            outcomes,
        )
    except MODULE.VerificationError as exc:
        if message is not None:
            assert message in str(exc)
    else:
        raise AssertionError(
            "Invalid P3 package was incorrectly accepted"
        )


def test_complete_valid_package_is_accepted(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    result = MODULE.verify_package(
        root,
        RUN_ID,
        EXPECTED,
        outcomes,
    )

    assert result["verdict"] == "P3_ACCEPTED"

    assert result["integrity"]["manifest_entries"] > 0

    assert (
        result["integrity"]["manifest_entries"]
        == result["integrity"]["sha256_entries_verified"]
    )

    assert result["benchmark"]["run_id"] == RUN_ID
    assert result["benchmark"]["schema"] == "qflpn-benchmark-v2"
    assert result["benchmark"]["records"] == 1
    assert result["benchmark"]["dimension"] == EXPECTED["dimension"]


def test_manifest_must_contain_paths_only(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    manifest = root / "P3" / "MANIFEST.txt"

    manifest.write_text(
        "# P3 manifest\n"
        "# File count: 1\n"
        "P3/pom.xml\n",
        encoding="utf-8",
    )

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "MANIFEST.txt paths are not sorted",
    )


def test_manifest_must_not_contain_integrity_files(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    manifest = root / "P3" / "MANIFEST.txt"

    entries = manifest.read_text(
        encoding="utf-8"
    ).splitlines()

    entries.append("P3/MANIFEST.txt")
    entries.sort()

    manifest.write_text(
        "".join(entry + "\n" for entry in entries),
        encoding="utf-8",
    )

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "self-referential global integrity path",
    )


def test_modified_source_file_fails_global_hash_check(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    source = root / "P3" / "pom.xml"
    source.write_text(
        "tampered content\n",
        encoding="utf-8",
    )

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "SHA-256 mismatch",
    )


def test_missing_manifest_fails_closed(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    (root / "P3" / "MANIFEST.txt").unlink()

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "P3/MANIFEST.txt is missing or unsafe",
    )


def test_missing_checksum_file_fails_closed(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    (root / "P3" / "SHA256SUMS.txt").unlink()

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "P3/SHA256SUMS.txt is missing or unsafe",
    )


def test_checksum_path_set_must_equal_manifest_path_set(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    checksum_path = root / "P3" / "SHA256SUMS.txt"
    checksum_path.write_text(
        "",
        encoding="ascii",
    )

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "path sets differ",
    )


def test_wrong_run_id_fails_benchmark_verification(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    expect_verification_failure(
        root,
        "p3-wrong-run",
        outcomes,
        "RUN_ID",
    )


def test_csv_json_run_id_mismatch_fails(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    report_path = (
        root
        / "P3"
        / "results"
        / "raw"
        / RUN_ID
        / "validation-report.json"
    )

    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    report["latest_record"]["run_id"] = "different-run"

    write_json(report_path, report)

    # The run-specific checksum is deliberately not regenerated.
    # The verifier must reject the changed evidence.
    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
    )


def test_invalid_benchmark_report_status_fails(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    report_path = (
        root
        / "P3"
        / "results"
        / "raw"
        / RUN_ID
        / "validation-report.json"
    )

    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    report["validation"] = "FAIL"
    write_json(report_path, report)

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
    )


def test_missing_run_evidence_fails(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    evidence = (
        root
        / "P3"
        / "results"
        / "raw"
        / RUN_ID
        / "benchmark-report.md"
    )

    evidence.unlink()

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
    )


def test_modified_run_evidence_fails_its_checksum(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    evidence = (
        root
        / "P3"
        / "results"
        / "raw"
        / RUN_ID
        / "benchmark-report.txt"
    )

    evidence.write_text(
        "tampered benchmark report\n",
        encoding="utf-8",
    )

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "run-specific SHA-256 mismatch",
    )


def test_failed_ci_stage_rejects_package(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    value = json.loads(
        outcomes.read_text(encoding="utf-8")
    )

    value["p3_benchmark"] = "failure"
    write_json(outcomes, value)

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "p3_benchmark",
    )


def test_missing_ci_stage_rejects_package(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    value = json.loads(
        outcomes.read_text(encoding="utf-8")
    )

    del value["p3_display_sha256"]
    write_json(outcomes, value)

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "p3_display_sha256",
    )


def test_invalid_run_id_is_rejected(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    expect_verification_failure(
        root,
        "../unsafe",
        outcomes,
        "RUN_ID contains unsupported characters",
    )


def test_invalid_ci_outcomes_json_fails(
    tmp_path: Path,
) -> None:
    root, _ = create_fixture(tmp_path)

    outcomes = tmp_path / "bad-outcomes.json"
    outcomes.write_text(
        "{invalid",
        encoding="utf-8",
    )

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "CI outcomes JSON is invalid",
    )


def test_unexpected_csv_record_fails_authoritative_validation(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    csv_path = (
        root
        / "P3"
        / "benchmarks"
        / "benchmark_results_v2.csv"
    )

    row = make_csv_row()
    row["speedup"] = "99"

    write_csv(csv_path, row)

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
    )


def test_duplicate_csv_run_id_fails_authoritative_validation(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    csv_path = (
        root
        / "P3"
        / "benchmarks"
        / "benchmark_results_v2.csv"
    )

    row = make_csv_row()

    with csv_path.open(
        "a",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=CSV_HEADER,
            extrasaction="raise",
        )
        writer.writerow(row)

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
    )


def test_missing_required_package_file_fails(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    (root / "P3" / "results" / "run_benchmark.sh").unlink()

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "required P3 package files are missing",
    )


def test_corrupted_run_checksum_file_fails(
    tmp_path: Path,
) -> None:
    root, outcomes = create_fixture(tmp_path)

    checksum_path = (
        root
        / "P3"
        / "results"
        / "raw"
        / RUN_ID
        / "SHA256SUMS.txt"
    )

    checksum_path.write_text(
        "not-a-valid-checksum-line\n",
        encoding="ascii",
    )

    expect_verification_failure(
        root,
        RUN_ID,
        outcomes,
        "malformed run-specific checksum",
    )
