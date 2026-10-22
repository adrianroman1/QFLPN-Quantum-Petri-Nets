from __future__ import annotations

from copy import deepcopy

import pytest

from audit.run_numeric_equivalence import (
    PENNYLANE_CHECKS,
    REQUIRED_ARTIFACTS,
    REQUIRED_OPERATIONS,
    REQUIRED_TOLERANCE,
)


@pytest.fixture
def valid_comparison():
    return {
        "status": "PASS",
        "shape_match": True,
        "baseline_shape": [2, 2],
        "migrated_shape": [2, 2],
        "reference_shape": [2, 2],
        "frobenius_norm_error": 0.0,
        "max_absolute_error": 0.0,
        "tolerance": REQUIRED_TOLERANCE,
    }


@pytest.fixture
def valid_operations(valid_comparison):
    comparisons = (
        "baseline_vs_reference",
        "migrated_vs_reference",
        "baseline_vs_migrated",
    )

    return {
        operation: {
            "status": "PASS",
            **{
                name: deepcopy(valid_comparison)
                for name in comparisons
            },
        }
        for operation in REQUIRED_OPERATIONS
    }


@pytest.fixture
def valid_artifacts():
    return {
        name: {
            "status": "PASS",
            "exists": True,
        }
        for name in REQUIRED_ARTIFACTS
    }


@pytest.fixture
def valid_pennylane_checks():
    checks = {
        name: {
            "status": "PASS",
            "shape_match": True,
            "actual_shape": [2, 2],
            "expected_shape": [2, 2],
            "frobenius_norm_error": 0.0,
            "max_absolute_error": 0.0,
            "tolerance": REQUIRED_TOLERANCE,
        }
        for name in PENNYLANE_CHECKS
    }

    checks["status"] = "PASS"
    return checks


@pytest.fixture
def valid_migration_evidence():
    return {
        "status": "PASS",
        "same_blob": False,
        "baseline_blob_sha": "a" * 64,
        "current_blob_sha": "b" * 64,
        "function_equivalence_status": "PASS",
        "numeric_equivalence_status": "PASS",
        "reason": "Distinct source hashes and successful equivalence checks.",
    }


@pytest.fixture
def valid_report(
    valid_operations,
    valid_artifacts,
    valid_pennylane_checks,
    valid_migration_evidence,
):
    return {
        "audit": "numeric_equivalence",
        "audit_id": "P2-BENCH-CONFIG-01",
        "timestamp_utc": "2026-10-22T00:00:00+00:00",
        "status": "PASS",
        "tolerance": REQUIRED_TOLERANCE,
        "baseline": {
            "blob": "c" * 40,
            "sha256": "a" * 64,
        },
        "migrated": {
            "path": "P2/benchmarks/benchmark_runner.py",
            "sha256": "b" * 64,
        },
        "artifacts": deepcopy(valid_artifacts),
        "operations": deepcopy(valid_operations),
        "issues": [],
        "pennylane_execution_checks": deepcopy(
            valid_pennylane_checks
        ),
        "migration_evidence": deepcopy(
            valid_migration_evidence
        ),
        "components": {
            "operations_status": "PASS",
            "artifacts_status": "PASS",
            "pennylane_status": "PASS",
            "migration_status": "PASS",
        },
    }


@pytest.fixture
def report_factory(valid_report):
    def factory():
        return deepcopy(valid_report)

    return factory
