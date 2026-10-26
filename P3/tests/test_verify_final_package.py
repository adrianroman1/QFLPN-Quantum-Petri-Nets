#!/usr/bin/env python3
"""Tests for the independent P3 final-package verifier.

The fixture follows the current verifier's actual inventory contract:
independent_inventory(root) returns sorted repository-relative strings.

These tests cover:
- deterministic and safe global inventory;
- MANIFEST.txt and SHA256SUMS.txt consistency;
- exclusion of self-referential integrity files and generated caches;
- mandatory p3_validation stage outcomes;
- RUN_ID, source commit and workflow-run provenance;
- final-package orchestration for V2 and V3;
- rejection of tampered or incomplete evidence.

The V2/V3 orchestration tests replace the benchmark verification functions
with controlled results. The authoritative V2/V3 validators are tested by
their dedicated test modules.
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
WORKFLOW_RUN_ID = "12345"

EXPECTED = {
    "dimension": 1_000_000,
    "warmup_iterations": 5,
    "measured_iterations": 10,
    "threshold": 4096,
    "parallelism": 2,
}

V3_AB_RESULT = {
    "schema": "qflpn-benchmark-v3-validation-v2",
    "run_id": RUN_ID,
    "run_contract": "AB_192",
    "validated_records": 192,
    "split_policies": [
        "BINARY_NNZ_SPLIT",
        "ROW_BOUNDARY_SCAN",
    ],
}


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
    """Create only the structural files required by the package verifier."""
    for relative in MODULE.REQUIRED_PACKAGE_FILES:
        path = root / relative

        if not path.exists():
            write_text(path, "test fixture\n")


def make_ci_outcomes(path: Path) -> None:
    """Create a successful outcome for every mandatory CI stage."""
    write_json(
        path,
        {
            stage: "success"
            for stage in MODULE.REQUIRED_CI_STAGES
        },
    )


def make_evidence_report(root: Path) -> None:
    """Create the provenance record consumed by verify_package()."""
    write_json(
        root / "P3" / "reports" / "evidence-consistency.json",
        {
            "schema": "qflpn-p3-evidence-consistency-v1",
            "validation": "PASS",
            "run_id": RUN_ID,
            "source_commit": SOURCE_COMMIT,
        },
    )


def make_global_integrity(root: Path) -> None:
    """Generate global integrity files from list[str] inventory entries.

    The two global integrity files are excluded by independent_inventory(),
    so neither file hashes itself or the other integrity file.
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
    write_text(manifest_path, manifest_content)

    checksum_content = "".join(
        f"{sha256_file(root / relative)}  {relative}\n"
        for relative in inventory
    )
    write_text(checksums_path, checksum_content)


def make_package(tmp_path: Path) -> tuple[Path, Path]:
    """Create a structurally complete package fixture."""
    root = tmp_path / "repository"
    root.mkdir()

    make_required_files(root)
    make_evidence_report(root)

    outcomes_path = tmp_path / "ci-outcomes.json"
    make_ci_outcomes(outcomes_path)

    make_global_integrity(root)

    return root, outcomes_path


def fake_v2(
    root: Path,
    run_id: str,
    expected: dict[str, int],
) -> dict[str, Any]:
    """Controlled V2 result for package-orchestration tests."""
    assert run_id == RUN_ID
    assert expected == EXPECTED

    return {
        "schema": "qflpn-benchmark-v2",
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
    """Isolate final-package orchestration from benchmark CSV parsing."""
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
    write_text(root / "P3" / "MANIFEST.txt", "old manifest\n")
    write_text(root / "P3" / "SHA256SUMS.txt", "old sums\n")

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
# MANIFEST and SHA256SUMS
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

def test_ci_outcomes_requires_every_mandatory_stage(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"

    make_ci_outcomes(path)

    result = MODULE.verify_ci_outcomes(path)

    assert set(result) == set(MODULE.REQUIRED_CI_STAGES)
    assert all(
        value == "success"
        for value in result.values()
    )


def test_ci_outcomes_rejects_missing_stage(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"

    outcomes = {
        stage: "success"
        for stage in MODULE.REQUIRED_CI_STAGES
    }
    outcomes.pop(MODULE.REQUIRED_CI_STAGES[0])

    write_json(path, outcomes)

    with pytest.raises(MODULE.VerificationError):
        MODULE.verify_ci_outcomes(path)


def test_ci_outcomes_rejects_failed_stage(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"

    outcomes = {
        stage: "success"
        for stage in MODULE.REQUIRED_CI_STAGES
    }
    outcomes[MODULE.REQUIRED_CI_STAGES[0]] = "failure"

    write_json(path, outcomes)

    with pytest.raises(
        MODULE.VerificationError,
        match="failed",
    ):
        MODULE.verify_ci_outcomes(path)


def test_ci_outcomes_rejects_non_object_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ci-outcomes.json"
    write_text(path, json.dumps(["success", "success"]))

    with pytest.raises(MODULE.VerificationError):
        MODULE.verify_ci_outcomes(path)


# ---------------------------------------------------------------------------
# V2 + V3 final package orchestration
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

    assert result["benchmark_v2"]["schema"] == "qflpn-benchmark-v2"
    assert result["benchmark_v3"]["schema"] == (
        "qflpn-benchmark-v3-validation-v2"
    )

    assert result["benchmark_v3"]["run_contract"] == "AB_192"
    assert result["benchmark_v3"]["validated_records"] == 192

    assert result["evidence_consistency"] == "PASS"

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
    outcomes[MODULE.REQUIRED_CI_STAGES[0]] = "failure"
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
        match="Required P3 files",
    ):
        call_package(root, outcomes_path)


def test_package_rejects_wrong_source_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)
    install_benchmark_stubs(monkeypatch)

    write_json(
        root / "P3" / "reports" / "evidence-consistency.json",
        {
            "schema": "qflpn-p3-evidence-consistency-v1",
            "validation": "PASS",
            "run_id": RUN_ID,
            "source_commit": "b" * 40,
        },
    )

    with pytest.raises(
        MODULE.VerificationError,
        match="commit mismatch",
    ):
        call_package(root, outcomes_path)


def test_package_rejects_wrong_run_id_in_evidence_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, outcomes_path = make_package(tmp_path)
    install_benchmark_stubs(monkeypatch)

    write_json(
        root / "P3" / "reports" / "evidence-consistency.json",
        {
            "schema": "qflpn-p3-evidence-consistency-v1",
            "validation": "PASS",
            "run_id": "p3-other-run",
            "source_commit": SOURCE_COMMIT,
        },
    )

    with pytest.raises(
        MODULE.VerificationError,
        match="RUN_ID mismatch",
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


def test_manifest_inventory_is_deterministic(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"

    write_text(root / "P3" / "nested" / "b.txt", "b\n")
    write_text(root / "P3" / "a.txt", "a\n")

    first = MODULE.independent_inventory(root)
    second = MODULE.independent_inventory(root)

    assert first == second
    assert first == sorted(first)
