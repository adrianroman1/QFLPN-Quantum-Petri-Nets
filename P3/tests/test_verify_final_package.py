#!/usr/bin/env python3
"""Tests for the P3 final-package verifier.

The tests exercise package acceptance and rejection paths using isolated
temporary repositories. They do not modify the actual P3 repository.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VERIFIER_PATH = REPOSITORY_ROOT / "P3" / "tools" / "verify_final_package.py"

if not VERIFIER_PATH.is_file():
    raise RuntimeError(f"Missing final-package verifier: {VERIFIER_PATH}")

SPEC = importlib.util.spec_from_file_location(
    "p3_verify_final_package_under_test",
    VERIFIER_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load verify_final_package.py")

MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


RUN_ID = "p3-12345-1"
SOURCE_COMMIT = "a" * 40

EXPECTED = {
    "dimension": 12,
    "warmup": 2,
    "iterations": 3,
    "threshold": 4,
    "parallelism": 2,
}

V2_COLUMNS = [
    "timestamp",
    "run_id",
    "dimension",
    "non_zero_count",
    "warmup_iterations",
    "measured_iterations",
    "sequential_mean_ms",
    "parallel_mean_ms",
    "speedup",
    "max_absolute_error",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_v2_csv(root: Path) -> Path:
    path = root / "P3" / "benchmarks" / "benchmark_results_v2.csv"
    path.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "timestamp": "2026-01-01T00:00:00Z",
        "run_id": RUN_ID,
        "dimension": str(EXPECTED["dimension"]),
        "non_zero_count": str(EXPECTED["dimension"] * 2),
        "warmup_iterations": str(EXPECTED["warmup"]),
        "measured_iterations": str(EXPECTED["iterations"]),
        "sequential_mean_ms": "10.0",
        "parallel_mean_ms": "5.0",
        "speedup": "2.0",
        "max_absolute_error": "0.0",
    }

    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=V2_COLUMNS)
        writer.writeheader()
        writer.writerow(row)

    return path


def write_run_evidence(root: Path) -> None:
    raw = root / "P3" / "results" / "raw" / RUN_ID

    write_json(
        raw / "validation-report.json",
        {
            "schema": "qflpn-benchmark-v2",
            "run_id": RUN_ID,
            "verdict": "PASS",
            "all_records_valid": True,
            "latest_record": {
                "dimension": EXPECTED["dimension"],
                "non_zero_count": EXPECTED["dimension"] * 2,
                "warmup_iterations": EXPECTED["warmup"],
                "measured_iterations": EXPECTED["iterations"],
                "sequential_mean_ms": 10.0,
                "parallel_mean_ms": 5.0,
                "speedup": 2.0,
                "max_absolute_error": 0.0,
            },
        },
    )

    write_json(
        raw / "benchmark-report.json",
        {
            "schema": "qflpn-java-benchmark-v2",
            "run_id": RUN_ID,
            "verdict": "PASS",
            "dimension": EXPECTED["dimension"],
            "non_zero_count": EXPECTED["dimension"] * 2,
        },
    )

    write_text(
        raw / "benchmark-report.txt",
        f"RUN_ID={RUN_ID}\nVERDICT=PASS\n",
    )
    write_text(
        raw / "benchmark-report.md",
        f"# P3 benchmark\n\nRUN_ID: `{RUN_ID}`\n\nVerdict: **PASS**\n",
    )


def write_environment(root: Path) -> None:
    write_json(
        root / "P3" / "results" / "raw" / RUN_ID / "environment.json",
        {
            "schema": "qflpn-p3-environment-v1",
            "run_id": RUN_ID,
            "source_commit": SOURCE_COMMIT,
            "dimension": EXPECTED["dimension"],
            "warmup": EXPECTED["warmup"],
            "iterations": EXPECTED["iterations"],
            "threshold": EXPECTED["threshold"],
            "parallelism": EXPECTED["parallelism"],
        },
    )


def write_run_checksums(root: Path) -> None:
    p3 = root / "P3"
    raw = p3 / "results" / "raw" / RUN_ID
    targets = [
        p3 / "benchmarks" / "benchmark_results_v2.csv",
        raw / "benchmark-report.json",
        raw / "benchmark-report.txt",
        raw / "benchmark-report.md",
        raw / "validation-report.json",
    ]

    lines = [
        f"{sha256(path)}  {path.relative_to(p3).as_posix()}"
        for path in targets
    ]
    write_text(raw / "SHA256SUMS.txt", "\n".join(lines) + "\n")


def write_required_package_files(root: Path) -> None:
    """Create minimal regular files for required package-path checks."""
    required = getattr(MODULE, "REQUIRED_PACKAGE_FILES", ())
    for relative in required:
        path = root / relative
        if path.name in {"MANIFEST.txt", "SHA256SUMS.txt"}:
            continue
        if not path.exists():
            write_text(path, "test fixture\n")


def write_ci_outcomes(root: Path) -> Path:
    path = root / "P3" / "reports" / "ci-outcomes.json"
    stages = getattr(MODULE, "REQUIRED_CI_STAGES", ())
    write_json(
        path,
        {
            stage: "success"
            for stage in stages
        },
    )
    return path


def write_global_integrity(root: Path) -> None:
    """Create the global inventory using the verifier's own inventory rules."""
    p3 = root / "P3"
    p3.mkdir(parents=True, exist_ok=True)

    inventory_function = getattr(MODULE, "independent_inventory", None)
    if inventory_function is None:
        raise AssertionError(
            "verify_final_package.py must expose independent_inventory()."
        )

    inventory = inventory_function(root)
    manifest = p3 / "MANIFEST.txt"
    checksums = p3 / "SHA256SUMS.txt"

    manifest_lines = [
        f"{entry['path']}  {entry['sha256']}"
        for entry in inventory
    ]
    write_text(manifest, "\n".join(manifest_lines) + "\n")

    checksum_lines = [
        f"{entry['sha256']}  {entry['path']}"
        for entry in inventory
    ]
    write_text(checksums, "\n".join(checksum_lines) + "\n")


def make_valid_package(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    root.mkdir()

    write_v2_csv(root)
    write_run_evidence(root)
    write_environment(root)
    write_run_checksums(root)
    write_required_package_files(root)

    outcomes = write_ci_outcomes(root)
    write_global_integrity(root)

    return root, outcomes


def call_verify(root: Path, outcomes: Path):
    verify = getattr(MODULE, "verify_package", None)
    if verify is None:
        raise AssertionError(
            "verify_final_package.py must expose verify_package()."
        )

    return verify(
        root=root,
        run_id=RUN_ID,
        expected=EXPECTED,
        outcomes_path=outcomes,
    )


def test_valid_package_is_accepted(tmp_path: Path) -> None:
    root, outcomes = make_valid_package(tmp_path)

    result = call_verify(root, outcomes)

    assert result["verdict"] == "P3_ACCEPTED"
    assert result["run_id"] == RUN_ID


def test_missing_ci_stage_is_rejected(tmp_path: Path) -> None:
    root, outcomes = make_valid_package(tmp_path)

    payload = json.loads(outcomes.read_text(encoding="utf-8"))
    stages = list(payload)
    assert stages, "The verifier must define required CI stages."

    payload[stages[0]] = "failure"
    write_json(outcomes, payload)

    with pytest.raises(Exception):
        call_verify(root, outcomes)


def test_missing_v2_csv_is_rejected(tmp_path: Path) -> None:
    root, outcomes = make_valid_package(tmp_path)

    (root / "P3" / "benchmarks" / "benchmark_results_v2.csv").unlink()

    with pytest.raises(Exception):
        call_verify(root, outcomes)


def test_tampered_run_checksum_is_rejected(tmp_path: Path) -> None:
    root, outcomes = make_valid_package(tmp_path)

    report = (
        root / "P3" / "results" / "raw" / RUN_ID / "benchmark-report.txt"
    )
    write_text(report, "tampered evidence\n")

    with pytest.raises(Exception):
        call_verify(root, outcomes)


def test_wrong_run_id_is_rejected(tmp_path: Path) -> None:
    root, outcomes = make_valid_package(tmp_path)

    csv_path = root / "P3" / "benchmarks" / "benchmark_results_v2.csv"
    content = csv_path.read_text(encoding="utf-8")
    csv_path.write_text(
        content.replace(RUN_ID, "p3-99999-1"),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        call_verify(root, outcomes)


def test_missing_environment_evidence_is_rejected(tmp_path: Path) -> None:
    root, outcomes = make_valid_package(tmp_path)

    environment = (
        root / "P3" / "results" / "raw" / RUN_ID / "environment.json"
    )
    environment.unlink()

    with pytest.raises(Exception):
        call_verify(root, outcomes)


def test_global_manifest_is_required(tmp_path: Path) -> None:
    root, outcomes = make_valid_package(tmp_path)

    (root / "P3" / "MANIFEST.txt").unlink()

    with pytest.raises(Exception):
        call_verify(root, outcomes)


def test_global_sha256_file_is_required(tmp_path: Path) -> None:
    root, outcomes = make_valid_package(tmp_path)

    (root / "P3" / "SHA256SUMS.txt").unlink()

    with pytest.raises(Exception):
        call_verify(root, outcomes)


def test_global_integrity_rejects_tampered_file(tmp_path: Path) -> None:
    root, outcomes = make_valid_package(tmp_path)

    write_text(
        root / "P3" / "results" / "raw" / RUN_ID / "benchmark-report.md",
        "tampered markdown\n",
    )

    with pytest.raises(Exception):
        call_verify(root, outcomes)


def test_global_integrity_files_are_not_self_referential(
    tmp_path: Path,
) -> None:
    root, _ = make_valid_package(tmp_path)

    manifest = (root / "P3" / "MANIFEST.txt").read_text(encoding="utf-8")
    checksums = (root / "P3" / "SHA256SUMS.txt").read_text(
        encoding="utf-8"
    )

    assert "MANIFEST.txt" not in manifest
    assert "SHA256SUMS.txt" not in manifest
    assert "MANIFEST.txt" not in checksums
    assert "SHA256SUMS.txt" not in checksums


def test_symlink_evidence_is_rejected_when_supported(
    tmp_path: Path,
) -> None:
    root, outcomes = make_valid_package(tmp_path)

    source = root / "P3" / "results" / "raw" / RUN_ID / "benchmark-report.txt"
    link = root / "P3" / "results" / "raw" / RUN_ID / "benchmark-report-link.txt"

    try:
        link.symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable on this platform.")

    with pytest.raises(Exception):
        call_verify(root, outcomes)


def test_manifest_inventory_is_deterministic(tmp_path: Path) -> None:
    root, _ = make_valid_package(tmp_path)

    inventory_function = getattr(MODULE, "independent_inventory", None)
    assert inventory_function is not None

    first = inventory_function(root)
    second = inventory_function(root)

    assert first == second
