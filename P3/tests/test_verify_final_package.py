#!/usr/bin/env python3
"""Tests for the independent P3 final-package verifier.

The fixtures follow the current contracts implemented by
P3/tools/verify_final_package.py:

- CI outcomes use qflpn-p3-ci-outcomes-v1;
- mandatory pre-integrity stages are stored under "stages";
- integrity-generation and final-verification stages are not required
  as entries in ci-outcomes.json;
- RUN_ID, source_commit and workflow_run_id are bound explicitly;
- evidence consistency uses qflqn-p3-evidence-consistency-v2;
- global MANIFEST.txt and SHA256SUMS.txt are independently verified.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

MODULE_PATH = (
    REPOSITORY_ROOT
    / "P3"
    / "tools"
    / "verify_final_package.py"
)

if not MODULE_PATH.is_file():
    raise RuntimeError(
        f"Final-package verifier does not exist: {MODULE_PATH}"
    )

SPEC = importlib.util.spec_from_file_location(
    "p3_verify_final_package_under_test",
    MODULE_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        f"Cannot load final-package verifier: {MODULE_PATH}"
    )

MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


RUN_ID = "p3-12345-1"
SOURCE_COMMIT = "a" * 40
WRONG_SOURCE_COMMIT = "b" * 40
WORKFLOW_RUN_ID = "12345"

CI_SCHEMA = "qflqn-p3-ci-outcomes-v1"
EVIDENCE_SCHEMA = "qflqn-p3-evidence-consistency-v2"

EXPECTED = {
    "dimension": 1_000_000,
    "warmup_iterations": 5,
    "measured_iterations": 10,
    "threshold": 4096,
    "parallelism": 2,
}

EVIDENCE_ITEMS = (
    "environment",
    "benchmark_v2",
    "benchmark_v3",
    "v3_authoritative_validator",
    "v3_persistent_report",
    "v3_checksums",
)

REMOVED_OUTCOME_STAGES = (
    "p3_integrity_generate",
    "p3_integrity_verify",
    "p3_final_verification",
)

V3_AB_RESULT = {
    "schema": "qflqn-benchmark-v3-validation-v2",
    "run_id": RUN_ID,
    "run_contract": "AB_192",
    "validated_records": 192,
    "split_policies": [
        "BINARY_NNZ_SPLIT",
        "ROW_BOUNDARY_SCAN",
    ],
}


# ---------------------------------------------------------------------------
# Generic fixture helpers
# ---------------------------------------------------------------------------

def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: dict[str, Any]) -> None:
    write_text(
        path,
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def make_required_files(root: Path) -> None:
    """Create the structural files required by the package verifier."""
    for relative in MODULE.REQUIRED_PACKAGE_FILES:
        path = root / relative

        if not path.exists():
            write_text(path, "test fixture\n")


# ---------------------------------------------------------------------------
# Current CI outcomes contract
# ---------------------------------------------------------------------------

def make_ci_outcomes(
    path: Path,
    *,
    run_id: str = RUN_ID,
    source_commit: str = SOURCE_COMMIT,
    workflow_run_id: str = WORKFLOW_RUN_ID,
) -> None:
    """Create a valid qflqn-p3-ci-outcomes-v1 envelope."""
    write_json(
        path,
        {
            "schema": CI_SCHEMA,
            "run_id": run_id,
            "source_commit": source_commit,
            "workflow_run_id": workflow_run_id,
            "stages": {
                stage: "success"
                for stage in MODULE.REQUIRED_CI_STAGES
            },
        },
    )


def verify_ci_outcomes_fixture(
    path: Path,
    *,
    expected_run_id: str = RUN_ID,
    expected_commit: str = SOURCE_COMMIT,
    expected_workflow_run_id: str = WORKFLOW_RUN_ID,
) -> dict[str, str]:
    """Call the production verifier with its complete current signature."""
    return MODULE.verify_ci_outcomes(
        path,
        expected_run_id=expected_run_id,
        expected_commit=expected_commit,
        expected_workflow_run_id=expected_workflow_run_id,
    )


# ---------------------------------------------------------------------------
# Evidence-consistency report fixture
# ---------------------------------------------------------------------------

def make_evidence_report(
    root: Path,
    *,
    run_id: str = RUN_ID,
    source_commit: str = SOURCE_COMMIT,
    workflow_run_id: str = WORKFLOW_RUN_ID,
) -> None:
    """Create the current v2 evidence-consistency report contract."""
    write_json(
        root / "P3" / "reports" / "evidence-consistency.json",
        {
            "schema": EVIDENCE_SCHEMA,
            "validation": "PASS",
            "run_id": run_id,
            "source_commit": source_commit,
            "workflow_run_id": workflow_run_id,
            "evidence": {
                item: "PASS"
                for item in EVIDENCE_ITEMS
            },
        },
    )


def make_mpi_evidence(
    root: Path,
    *,
    run_id: str = RUN_ID,
    source_commit: str = SOURCE_COMMIT,
    workflow_run_id: str = WORKFLOW_RUN_ID,
) -> None:
    """Create internally consistent MPI evidence for package tests.

    This fixture follows the production report contract. The production
    verifier remains active: it checks the report, executable digest,
    build log, output logs, numerical tolerances and provenance.
    """
    executable_path = root / MODULE.MPI_EXECUTABLE
    executable_path.parent.mkdir(parents=True, exist_ok=True)

    write_text(
        executable_path,
        "#!/bin/sh\n"
        "exit 0\n",
    )
    executable_path.chmod(0o755)

    write_text(
        root / MODULE.MPI_BUILD_LOG,
        "MPI native build fixture\n"
        "STDOUT:\n"
        "MPI compiler test output\n"
        "STDERR:\n"
        "MPI compiler test diagnostics: none\n"
        "EXIT_CODE=0\n",
    )

    write_text(
        root / MODULE.MPI_STDOUT,
        "MPI test execution passed\n",
    )
    write_text(
        root / MODULE.MPI_STDERR,
        "",
    )

    write_json(
        root / MODULE.MPI_REPORT,
        {
            "schema": MODULE.MPI_SCHEMA,
            "validation": "PASS",
            "run_id": run_id,
            "source_commit": source_commit,
            "workflow_run_id": workflow_run_id,
            "workflow_run_attempt": 1,
            "repository": "adrianroman1/QFLPN-Quantum-Petri-Nets",
            "native_build": {
                "status": "PASS",
                "compiler": "mpicc",
                "compiler_path": "/test-tools/mpicc",
                "compiler_version": "MPI test compiler version",
                "source_file": MODULE.MPI_SOURCE,
                "executable": MODULE.MPI_EXECUTABLE,
                "executable_sha256": sha256_file(executable_path),
                "exit_code": 0,
            },
            "execution": {
                "status": "PASS",
                "launcher": "/test-tools/mpirun",
                "process_count": 2,
                "exit_code": 0,
                "skipped": False,
                "timeout": False,
                "stdout_file": MODULE.MPI_STDOUT,
                "stderr_file": MODULE.MPI_STDERR,
            },
            "numerical_validation": {
                "status": "PASS",
                "reference": "sequential_csr",
                "rows": 128,
                "columns": 128,
                "nnz": 384,
                "max_absolute_error": 0.0,
                "max_relative_error": 0.0,
                "absolute_tolerance": 1.0e-12,
                "relative_tolerance": 1.0e-12,
                "max_reference_magnitude": 12.0,
                "comparison": "PASS",
            },
            "provenance": {
                "commit_verified": True,
                "run_id_verified": True,
                "workflow_run_id_verified": True,
            },
        },
    )


def fake_evidence_consistency(
    root: Path,
    run_id: str,
    source_commit: str,
    workflow_run_id: str | None,
) -> dict[str, Any]:
    """Validate report provenance for isolated orchestration tests."""
    report_path = (
        root
        / "P3"
        / "reports"
        / "evidence-consistency.json"
    )

    if not report_path.is_file():
        raise MODULE.VerificationError(
            "P3 evidence consistency report is missing"
        )

    try:
        report = json.loads(
            report_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MODULE.VerificationError(
            f"P3 evidence consistency report is invalid: {exc}"
        ) from exc

    if not isinstance(report, dict):
        raise MODULE.VerificationError(
            "P3 evidence consistency report must be a JSON object"
        )

    if report.get("schema") != EVIDENCE_SCHEMA:
        raise MODULE.VerificationError(
            "Evidence consistency schema mismatch"
        )

    if report.get("validation") != "PASS":
        raise MODULE.VerificationError(
            "Evidence consistency report is not PASS"
        )

    if report.get("run_id") != run_id:
        raise MODULE.VerificationError(
            "Evidence consistency RUN_ID mismatch"
        )

    if report.get("source_commit") != source_commit:
        raise MODULE.VerificationError(
            "Evidence consistency source_commit mismatch"
        )

    if workflow_run_id is not None:
        if str(report.get("workflow_run_id")) != str(
            workflow_run_id
        ):
            raise MODULE.VerificationError(
                "Evidence consistency workflow_run_id mismatch"
            )

    evidence = report.get("evidence")

    if not isinstance(evidence, dict):
        raise MODULE.VerificationError(
            "Evidence consistency report has no evidence object"
        )

    for item in EVIDENCE_ITEMS:
        if evidence.get(item) != "PASS":
            raise MODULE.VerificationError(
                f"Evidence consistency item failed: {item}"
            )

    return {
        "validation": "PASS",
        "run_id": run_id,
        "source_commit": source_commit,
        "workflow_run_id": workflow_run_id,
        "items": sorted(evidence),
    }


# ---------------------------------------------------------------------------
# Global MANIFEST.txt and SHA256SUMS.txt fixtures
# ---------------------------------------------------------------------------

def make_global_integrity(root: Path) -> None:
    """Generate global integrity files from the independent inventory.

    MANIFEST.txt and SHA256SUMS.txt are excluded from the inventory itself.
    """
    p3_root = root / "P3"
    p3_root.mkdir(parents=True, exist_ok=True)

    inventory = MODULE.independent_inventory(root)

    assert all(isinstance(item, str) for item in inventory)
    assert inventory == sorted(inventory)

    manifest_path = p3_root / "MANIFEST.txt"
    checksums_path = p3_root / "SHA256SUMS.txt"

    manifest_content = "".join(
        f"{relative}\n"
        for relative in inventory
    )

    write_text(
        manifest_path,
        manifest_content,
    )

    checksum_content = "".join(
        f"{sha256_file(root / relative)}  {relative}\n"
        for relative in inventory
    )

    write_text(
        checksums_path,
        checksum_content,
    )


# ---------------------------------------------------------------------------
# Complete package fixture
# ---------------------------------------------------------------------------

def make_package(
    tmp_path: Path,
) -> tuple[Path, Path]:
    """Create a structurally complete package fixture."""
    root = tmp_path / "repository"
    root.mkdir()

    make_required_files(root)
    make_evidence_report(root)
    make_mpi_evidence(root)

    outcomes_path = tmp_path / "ci-outcomes.json"

    make_ci_outcomes(outcomes_path)

    make_global_integrity(root)

    return root, outcomes_path


# ---------------------------------------------------------------------------
# Controlled benchmark results
# ---------------------------------------------------------------------------

def fake_v2(
    root: Path,
    run_id: str,
    expected: dict[str, int],
) -> dict[str, Any]:
    """Controlled V2 result for package-orchestration tests."""
    assert run_id == RUN_ID
    assert expected == EXPECTED

    return {
        "schema": "qflqn-benchmark-v2",
        "run_id": RUN_ID,
        "records": 1,
        "dimension": EXPECTED["dimension"],
        "non_zero_count": EXPECTED["dimension"] * 2,
        "speedup": 2.0,
    }


def fake_v3(
    root: Path,
    run_id: str,
    commit_sha: str,
    workflow_run_id: str | None,
) -> dict[str, Any]:
    """Controlled V3 result for package-orchestration tests."""
    assert run_id == RUN_ID
    assert commit_sha == SOURCE_COMMIT
    assert workflow_run_id == WORKFLOW_RUN_ID

    return dict(V3_AB_RESULT)


def install_benchmark_stubs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Isolate orchestration from CSV parsing and external benchmark data."""
    monkeypatch.setattr(
        MODULE,
        "verify_v2",
        fake_v2,
    )

    monkeypatch.setattr(
        MODULE,
        "verify_v3",
        fake_v3,
    )

    monkeypatch.setattr(
        MODULE,
        "verify_evidence_consistency",
        fake_evidence_consistency,
    )


def call_package(
    root: Path,
    outcomes_path: Path,
) -> dict[str, Any]:
    return MODULE.verify_package(
        root,
        RUN_ID,
        EXPECTED,
        outcomes_path,
        source_commit=SOURCE_COMMIT,
        workflow_run_id=WORKFLOW_RUN_ID,
    )


# ---------------------------------------------------------------------------
# Inventory contract
# ---------------------------------------------------------------------------

def test_inventory_returns_sorted_relative_path_strings(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(root / "P3" / "z.txt", "z\n")
    write_text(root / "P3" / "a.txt", "a\n")

    inventory = MODULE.independent_inventory(root)

    assert inventory == sorted(inventory)
    assert "P3/a.txt" in inventory
    assert "P3/z.txt" in inventory
    assert all(isinstance(item, str) for item in inventory)


def test_inventory_excludes_global_integrity_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(root / "P3" / "data.txt", "data\n")
    write_text(
        root / "P3" / "MANIFEST.txt",
        "old manifest\n",
    )
    write_text(
        root / "P3" / "SHA256SUMS.txt",
        "old sums\n",
    )

    inventory = MODULE.independent_inventory(root)

    assert "P3/data.txt" in inventory
    assert "P3/MANIFEST.txt" not in inventory
    assert "P3/SHA256SUMS.txt" not in inventory


def test_inventory_excludes_generated_cache_directories(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(root / "P3" / "data.txt", "data\n")
    write_text(
        root / "P3" / "__pycache__" / "module.pyc",
        "cache\n",
    )
    write_text(
        root / "P3" / "target" / "compiled.class",
        "class\n",
    )

    inventory = MODULE.independent_inventory(root)

    assert inventory == ["P3/data.txt"]


def test_inventory_is_deterministic(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(root / "P3" / "nested" / "b.txt", "b\n")
    write_text(root / "P3" / "a.txt", "a\n")

    first = MODULE.independent_inventory(root)
    second = MODULE.independent_inventory(root)

    assert first == second
    assert first == sorted(first)


def test_inventory_rejects_missing_p3_directory(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    with pytest.raises(
        MODULE.VerificationError,
        match="P3 directory",
    ):
        MODULE.independent_inventory(root)


# ---------------------------------------------------------------------------
# MANIFEST.txt and SHA256SUMS.txt
# ---------------------------------------------------------------------------

def test_global_integrity_accepts_correct_manifest_and_checksums(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(root / "P3" / "a.txt", "alpha\n")
    write_text(root / "P3" / "b.txt", "beta\n")

    make_global_integrity(root)

    result = MODULE.verify_global_integrity(root)

    assert result["manifest_entries"] == 2
    assert result["sha256_entries_verified"] == 2


def test_global_integrity_rejects_tampered_file(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(root / "P3" / "a.txt", "original\n")
    make_global_integrity(root)

    write_text(root / "P3" / "a.txt", "modified\n")

    with pytest.raises(
        MODULE.VerificationError,
        match="SHA-256 mismatch",
    ):
        MODULE.verify_global_integrity(root)


def test_global_integrity_rejects_manifest_path_mismatch(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(root / "P3" / "a.txt", "alpha\n")
    make_global_integrity(root)

    write_text(
        root / "P3" / "MANIFEST.txt",
        "P3/not-present.txt\n",
    )

    with pytest.raises(MODULE.VerificationError):
        MODULE.verify_global_integrity(root)


def test_global_integrity_rejects_self_reference(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(root / "P3" / "a.txt", "alpha\n")
    make_global_integrity(root)

    manifest = root / "P3" / "MANIFEST.txt"

    write_text(
        manifest,
        manifest.read_text(encoding="utf-8")
        + "P3/MANIFEST.txt\n",
    )

    with pytest.raises(MODULE.VerificationError):
        MODULE.verify_global_integrity(root)


def test_global_integrity_rejects_missing_manifest(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(root / "P3" / "a.txt", "alpha\n")
    make_global_integrity(root)

    (root / "P3" / "MANIFEST.txt").unlink()

    with pytest.raises(
        MODULE.VerificationError,
        match="MANIFEST",
    ):
        MODULE.verify_global_integrity(root)


def test_global_integrity_rejects_missing_checksums(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(root / "P3" / "a.txt", "alpha\n")
    make_global_integrity(root)

    (root / "P3" / "SHA256SUMS.txt").unlink()

    with pytest.raises(
        MODULE.VerificationError,
        match="SHA256SUMS",
    ):
        MODULE.verify_global_integrity(root)


# ---------------------------------------------------------------------------
# p3_validation mandatory CI stages
# ---------------------------------------------------------------------------

def test_removed_integrity_stages_are_not_ci_outcomes_requirements() -> None:
    """Integrity execution is verified directly, not via early outcomes."""
    required = set(MODULE.REQUIRED_CI_STAGES)

    for stage in REMOVED_OUTCOME_STAGES:
        assert stage not in required


def test_artifact_upload_remains_a_mandatory_ci_stage() -> None:
    assert "p3_artifact_upload" in MODULE.REQUIRED_CI_STAGES


def test_ci_outcomes_requires_every_mandatory_stage(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"

    make_ci_outcomes(path)

    result = verify_ci_outcomes_fixture(path)

    assert set(result) == set(MODULE.REQUIRED_CI_STAGES)
    assert all(
        value == "success"
        for value in result.values()
    )


def test_ci_outcomes_accepts_absence_of_removed_integrity_stages(
    tmp_path: Path,
) -> None:
    """The three post-outcomes stages must not be required in the JSON."""
    path = tmp_path / "ci-outcomes.json"

    stages = {
        stage: "success"
        for stage in MODULE.REQUIRED_CI_STAGES
    }

    for stage in REMOVED_OUTCOME_STAGES:
        stages.pop(stage, None)

    write_json(
        path,
        {
            "schema": CI_SCHEMA,
            "run_id": RUN_ID,
            "source_commit": SOURCE_COMMIT,
            "workflow_run_id": WORKFLOW_RUN_ID,
            "stages": stages,
        },
    )

    result = verify_ci_outcomes_fixture(path)

    assert set(result) == set(MODULE.REQUIRED_CI_STAGES)
    assert not (set(REMOVED_OUTCOME_STAGES) & set(result))


def test_ci_outcomes_rejects_missing_stage(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"

    stages = {
        stage: "success"
        for stage in MODULE.REQUIRED_CI_STAGES
    }

    stages.pop(MODULE.REQUIRED_CI_STAGES[0])

    write_json(
        path,
        {
            "schema": CI_SCHEMA,
            "run_id": RUN_ID,
            "source_commit": SOURCE_COMMIT,
            "workflow_run_id": WORKFLOW_RUN_ID,
            "stages": stages,
        },
    )

    with pytest.raises(
        MODULE.VerificationError,
        match="Missing mandatory",
    ):
        verify_ci_outcomes_fixture(path)


def test_ci_outcomes_rejects_failed_stage(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"

    stages = {
        stage: "success"
        for stage in MODULE.REQUIRED_CI_STAGES
    }

    stages[MODULE.REQUIRED_CI_STAGES[0]] = "failure"

    write_json(
        path,
        {
            "schema": CI_SCHEMA,
            "run_id": RUN_ID,
            "source_commit": SOURCE_COMMIT,
            "workflow_run_id": WORKFLOW_RUN_ID,
            "stages": stages,
        },
    )

    with pytest.raises(
        MODULE.VerificationError,
        match="did not succeed",
    ):
        verify_ci_outcomes_fixture(path)


def test_ci_outcomes_rejects_non_object_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"

    write_text(
        path,
        json.dumps(["success", "success"]),
    )

    with pytest.raises(MODULE.VerificationError):
        verify_ci_outcomes_fixture(path)


def test_ci_outcomes_rejects_wrong_run_id(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"

    make_ci_outcomes(
        path,
        run_id="p3-other-run",
    )

    with pytest.raises(
        MODULE.VerificationError,
        match="RUN_ID mismatch",
    ):
        verify_ci_outcomes_fixture(path)


def test_ci_outcomes_rejects_wrong_source_commit(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"

    make_ci_outcomes(
        path,
        source_commit=WRONG_SOURCE_COMMIT,
    )

    with pytest.raises(
        MODULE.VerificationError,
        match="source_commit mismatch",
    ):
        verify_ci_outcomes_fixture(path)


def test_ci_outcomes_rejects_wrong_workflow_run_id(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"

    make_ci_outcomes(
        path,
        workflow_run_id="99999",
    )

    with pytest.raises(
        MODULE.VerificationError,
        match="workflow_run_id mismatch",
    ):
        verify_ci_outcomes_fixture(path)


def test_ci_outcomes_rejects_wrong_schema(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"

    make_ci_outcomes(path)

    outcomes = json.loads(
        path.read_text(encoding="utf-8")
    )

    outcomes["schema"] = "obsolete-schema"

    write_json(path, outcomes)

    with pytest.raises(
        MODULE.VerificationError,
        match="schema mismatch",
    ):
        verify_ci_outcomes_fixture(path)


# ---------------------------------------------------------------------------
# V2 + V3 final-package orchestration
# ---------------------------------------------------------------------------

def test_valid_package_orchestration_is_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)

    install_benchmark_stubs(monkeypatch)

    result = call_package(root, outcomes_path)

    assert result["verdict"] == "P3_ACCEPTED"
    assert result["run_id"] == RUN_ID
    assert result["source_commit"] == SOURCE_COMMIT
    assert result["workflow_run_id"] == WORKFLOW_RUN_ID

    assert (
        result["benchmark_v2"]["schema"]
        == "qflqn-benchmark-v2"
    )

    assert (
        result["benchmark_v3"]["schema"]
        == "qflqn-benchmark-v3-validation-v2"
    )

    assert result["benchmark_v3"]["run_contract"] == "AB_192"
    assert result["benchmark_v3"]["validated_records"] == 192

    evidence_consistency = result["evidence_consistency"]

    assert evidence_consistency["validation"] == "PASS"
    assert evidence_consistency["run_id"] == RUN_ID
    assert evidence_consistency["source_commit"] == SOURCE_COMMIT
    assert (
        evidence_consistency["workflow_run_id"]
        == WORKFLOW_RUN_ID
    )

    assert set(result["ci_stages"]) == set(
        MODULE.REQUIRED_CI_STAGES
    )


def test_package_rejects_failed_ci_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)

    install_benchmark_stubs(monkeypatch)

    outcomes = json.loads(
        outcomes_path.read_text(encoding="utf-8")
    )

    outcomes["stages"][
        MODULE.REQUIRED_CI_STAGES[0]
    ] = "failure"

    write_json(outcomes_path, outcomes)

    with pytest.raises(MODULE.VerificationError):
        call_package(root, outcomes_path)


def test_package_rejects_missing_required_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)

    install_benchmark_stubs(monkeypatch)

    required = root / MODULE.REQUIRED_PACKAGE_FILES[0]
    required.unlink()

    with pytest.raises(
        MODULE.VerificationError,
        match="Required P3 package files",
    ):
        call_package(root, outcomes_path)


def test_package_rejects_wrong_source_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)

    install_benchmark_stubs(monkeypatch)

    make_evidence_report(
        root,
        source_commit=WRONG_SOURCE_COMMIT,
    )

    with pytest.raises(
        MODULE.VerificationError,
        match="source_commit mismatch",
    ):
        call_package(root, outcomes_path)


def test_package_rejects_wrong_run_id_in_evidence_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)

    install_benchmark_stubs(monkeypatch)

    make_evidence_report(
        root,
        run_id="p3-other-run",
    )

    with pytest.raises(
        MODULE.VerificationError,
        match="RUN_ID mismatch",
    ):
        call_package(root, outcomes_path)


def test_package_rejects_wrong_workflow_id_in_evidence_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)

    install_benchmark_stubs(monkeypatch)

    make_evidence_report(
        root,
        workflow_run_id="99999",
    )

    with pytest.raises(
        MODULE.VerificationError,
        match="workflow_run_id mismatch",
    ):
        call_package(root, outcomes_path)


def test_package_rejects_failed_evidence_item(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)

    install_benchmark_stubs(monkeypatch)

    report_path = (
        root
        / "P3"
        / "reports"
        / "evidence-consistency.json"
    )

    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    report["evidence"]["benchmark_v3"] = "FAIL"

    write_json(report_path, report)

    with pytest.raises(
        MODULE.VerificationError,
        match="Evidence consistency item failed",
    ):
        call_package(root, outcomes_path)


def test_package_rejects_tampered_global_integrity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)

    install_benchmark_stubs(monkeypatch)

    write_text(
        root / "P3" / "reports" / "evidence-consistency.json",
        "tampered\n",
    )

    with pytest.raises(MODULE.VerificationError):
        call_package(root, outcomes_path)


def test_package_rejects_invalid_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)

    install_benchmark_stubs(monkeypatch)

    with pytest.raises(
        MODULE.VerificationError,
        match="Invalid RUN_ID",
    ):
        MODULE.verify_package(
            root,
            "../invalid",
            EXPECTED,
            outcomes_path,
            source_commit=SOURCE_COMMIT,
            workflow_run_id=WORKFLOW_RUN_ID,
        )


def test_package_rejects_invalid_source_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)

    install_benchmark_stubs(monkeypatch)

    with pytest.raises(
        MODULE.VerificationError,
        match="Invalid SOURCE_COMMIT",
    ):
        MODULE.verify_package(
            root,
            RUN_ID,
            EXPECTED,
            outcomes_path,
            source_commit="not-a-commit",
            workflow_run_id=WORKFLOW_RUN_ID,
        )


def test_package_rejects_invalid_workflow_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)

    install_benchmark_stubs(monkeypatch)

    with pytest.raises(
        MODULE.VerificationError,
        match="Invalid workflow_run_id",
    ):
        MODULE.verify_package(
            root,
            RUN_ID,
            EXPECTED,
            outcomes_path,
            source_commit=SOURCE_COMMIT,
            workflow_run_id="not-numeric",
        )


# ---------------------------------------------------------------------------
# Manifest determinism
# ---------------------------------------------------------------------------

def test_manifest_inventory_is_deterministic(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(
        root / "P3" / "nested" / "b.txt",
        "b\n",
    )

    write_text(
        root / "P3" / "a.txt",
        "a\n",
    )

    first = MODULE.independent_inventory(root)
    second = MODULE.independent_inventory(root)

    assert first == second
    assert first == sorted(first)
