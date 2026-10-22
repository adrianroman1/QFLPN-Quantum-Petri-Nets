"""Tests for P2-BENCH-CONFIG-01 numeric equivalence audit.

Test matrix:
    R1: 9 tests — numeric classification
    R2: 9 tests — PennyLane execution evidence
    R3: 7 tests — migration evidence
    R4: 7 tests — global verdict aggregation

Run:
    pytest -q audit/test_numeric_equivalence.py
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "audit" / "run_numeric_equivalence.py"

SPEC = importlib.util.spec_from_file_location(
    "run_numeric_equivalence_under_test",
    AUDIT_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        f"Cannot load numeric audit module: {AUDIT_PATH}"
    )

audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


TOLERANCE = 1e-12

PENNYLANE_CHECK_NAMES = (
    "baseline_qnode_vs_callable",
    "migrated_qnode_vs_callable",
    "baseline_qnode_vs_reference",
    "migrated_qnode_vs_reference",
)

REQUIRED_COMPONENTS = (
    "operations_status",
    "artifacts_status",
    "pennylane_status",
    "migration_status",
)


# ============================================================
# SHARED TEST FIXTURES
# ============================================================

def passing_pennylane_checks():
    return {
        name: {
            "status": "PASS",
            "shape_match": True,
            "actual_shape": [2, 2],
            "expected_shape": [2, 2],
            "frobenius_norm_error": 0.0,
            "max_absolute_error": 0.0,
            "tolerance": TOLERANCE,
        }
        for name in PENNYLANE_CHECK_NAMES
    }


def passing_comparison():
    return {
        "status": "PASS",
        "shape_match": True,
        "actual_shape": [2, 2],
        "expected_shape": [2, 2],
        "frobenius_norm_error": 0.0,
        "max_absolute_error": 0.0,
        "tolerance": TOLERANCE,
    }


def passing_report():
    operations = {}

    for name in audit.REQUIRED_OPERATIONS:
        operations[name] = {
            "status": "PASS",
            "baseline_vs_reference": passing_comparison(),
            "migrated_vs_reference": passing_comparison(),
            "baseline_vs_migrated": passing_comparison(),
        }

    artifacts = {
        name: {"status": "PASS", "exists": True}
        for name in audit.REQUIRED_ARTIFACTS
    }

    components = {
        "operations_status": "PASS",
        "artifacts_status": "PASS",
        "pennylane_status": "PASS",
        "migration_status": "PASS",
    }

    return {
        "audit": "numeric_equivalence",
        "audit_id": "P2-BENCH-CONFIG-01",
        "timestamp_utc": "2026-01-01T00:00:00+00:00",
        "status": "PASS",
        "tolerance": TOLERANCE,
        "baseline": {
            "blob": "baseline",
            "sha256": "a" * 40,
        },
        "migrated": {
            "path": "P2/benchmarks/benchmark_runner.py",
            "sha256": "b" * 40,
        },
        "artifacts": artifacts,
        "operations": operations,
        "pennylane_execution_checks": passing_pennylane_checks(),
        "migration_evidence": {
            "status": "PASS",
            "same_blob": False,
            "baseline_blob_sha": "a" * 40,
            "current_blob_sha": "b" * 40,
            "function_equivalence_status": "PASS",
            "numeric_equivalence_status": "PASS",
        },
        "components": components,
        "issues": [],
    }


# ============================================================
# R1 — NUMERIC CLASSIFICATION (9 TESTS)
# ============================================================

def test_r1_error_below_tolerance_pass():
    result = audit.compare_arrays(
        np.array([1.0, 2.0]),
        np.array([1.0 + 1e-13, 2.0]),
        TOLERANCE,
    )

    assert result["status"] == "PASS"
    assert result["frobenius_norm_error"] <= TOLERANCE


def test_r1_error_equal_tolerance_pass():
    result = audit.compare_arrays(
        np.array([0.0]),
        np.array([TOLERANCE]),
        TOLERANCE,
    )

    assert result["status"] == "PASS"
    assert result["max_absolute_error"] <= TOLERANCE


def test_r1_error_above_tolerance_fail():
    result = audit.compare_arrays(
        np.array([0.0]),
        np.array([2.0 * TOLERANCE]),
        TOLERANCE,
    )

    assert result["status"] == "FAIL"


def test_r1_error_just_above_tolerance_fail():
    result = audit.compare_arrays(
        np.array([0.0]),
        np.array([np.nextafter(TOLERANCE, math.inf)]),
        TOLERANCE,
    )

    assert result["status"] == "FAIL"


def test_r1_shape_mismatch_fail():
    result = audit.compare_arrays(
        np.array([1.0, 2.0]),
        np.array([[1.0, 2.0]]),
        TOLERANCE,
    )

    assert result["status"] == "FAIL"
    assert result["shape_match"] is False


def test_r1_nan_fail():
    with pytest.raises(audit.NumericAuditFailure):
        audit.validate_array(
            np.array([1.0, np.nan]),
            "nan_test",
        )


def test_r1_positive_inf_fail():
    with pytest.raises(audit.NumericAuditFailure):
        audit.validate_array(
            np.array([1.0, np.inf]),
            "positive_inf_test",
        )


def test_r1_negative_inf_fail():
    with pytest.raises(audit.NumericAuditFailure):
        audit.validate_array(
            np.array([1.0, -np.inf]),
            "negative_inf_test",
        )


def test_r1_missing_operand_not_verified():
    # Missing operands are operational/input failures, not numeric
    # defects. They must not be converted into NumericAuditFailure.
    with pytest.raises((TypeError, ValueError)):
        audit.validate_array(None, "missing_operand")


# ============================================================
# R2 — PENNYLANE EXECUTION EVIDENCE (9 TESTS)
# ============================================================

def test_r2_missing_section_not_verified():
    result = audit._validate_pennylane_checks(None)

    assert result["status"] == "NOT VERIFIED"


def test_r2_missing_check_not_verified():
    checks = passing_pennylane_checks()
    del checks["baseline_qnode_vs_callable"]

    result = audit._validate_pennylane_checks(checks)

    assert result["status"] == "NOT VERIFIED"


def test_r2_missing_required_field_not_verified():
    checks = passing_pennylane_checks()
    del checks["migrated_qnode_vs_callable"]["max_absolute_error"]

    result = audit._validate_pennylane_checks(checks)

    assert result["status"] == "NOT VERIFIED"


def test_r2_nan_error_fail():
    checks = passing_pennylane_checks()
    checks["baseline_qnode_vs_callable"][
        "frobenius_norm_error"
    ] = float("nan")

    result = audit._validate_pennylane_checks(checks)

    assert result["status"] == "FAIL"


def test_r2_inf_error_fail():
    checks = passing_pennylane_checks()
    checks["baseline_qnode_vs_callable"][
        "max_absolute_error"
    ] = float("inf")

    result = audit._validate_pennylane_checks(checks)

    assert result["status"] == "FAIL"


def test_r2_error_above_tolerance_fail():
    checks = passing_pennylane_checks()
    checks["migrated_qnode_vs_reference"][
        "frobenius_norm_error"
    ] = 2.0 * TOLERANCE
    checks["migrated_qnode_vs_reference"]["status"] = "FAIL"

    result = audit._validate_pennylane_checks(checks)

    assert result["status"] == "FAIL"


def test_r2_all_checks_pass():
    result = audit._validate_pennylane_checks(
        passing_pennylane_checks()
    )

    assert result["status"] == "PASS"
    assert result["errors"] == []


def test_r2_shape_match_false_fail():
    checks = passing_pennylane_checks()
    checks["baseline_qnode_vs_callable"]["shape_match"] = False
    checks["baseline_qnode_vs_callable"]["status"] = "FAIL"

    result = audit._validate_pennylane_checks(checks)

    assert result["status"] == "FAIL"


def test_r2_shape_values_mismatch_fail():
    checks = passing_pennylane_checks()
    checks["baseline_qnode_vs_callable"]["actual_shape"] = [2, 3]

    result = audit._validate_pennylane_checks(checks)

    assert result["status"] == "FAIL"


# ============================================================
# R3 — MIGRATION EVIDENCE (7 TESTS)
# ============================================================

def migration(
    baseline="a" * 40,
    current="b" * 40,
    function_status="PASS",
    numeric_status="PASS",
):
    return audit.evaluate_migration_evidence(
        baseline_blob_sha=baseline,
        current_blob_sha=current,
        function_equivalence_status=function_status,
        numeric_equivalence_status=numeric_status,
    )


def test_r3_function_fail_priority():
    result = migration(
        baseline="a" * 40,
        current="a" * 40,
        function_status="FAIL",
        numeric_status="PASS",
    )

    assert result["status"] == "FAIL"


def test_r3_numeric_fail_priority():
    result = migration(
        baseline="a" * 40,
        current="a" * 40,
        function_status="PASS",
        numeric_status="FAIL",
    )

    assert result["status"] == "FAIL"


def test_r3_identical_blobs_not_verified():
    result = migration(
        baseline="a" * 40,
        current="a" * 40,
    )

    assert result["status"] == "NOT VERIFIED"
    assert result["same_blob"] is True


def test_r3_unknown_status_not_verified():
    result = migration(
        function_status="UNKNOWN",
        numeric_status="PASS",
    )

    assert result["status"] == "NOT VERIFIED"


def test_r3_distinct_blobs_pass():
    result = migration(
        baseline="a" * 40,
        current="b" * 40,
        function_status="PASS",
        numeric_status="PASS",
    )

    assert result["status"] == "PASS"
    assert result["same_blob"] is False


def test_r3_identical_blobs_do_not_hide_fail():
    result = migration(
        baseline="a" * 40,
        current="a" * 40,
        function_status="FAIL",
        numeric_status="PASS",
    )

    assert result["status"] == "FAIL"


def test_r3_missing_sha_not_verified():
    result = migration(
        baseline="",
        current="b" * 40,
    )

    assert result["status"] == "NOT VERIFIED"


# ============================================================
# R4 — GLOBAL VERDICT AGGREGATION (7 TESTS)
# ============================================================

def components(
    operations="PASS",
    artifacts="PASS",
    pennylane="PASS",
    migration_status="PASS",
):
    return {
        "operations_status": operations,
        "artifacts_status": artifacts,
        "pennylane_status": pennylane,
        "migration_status": migration_status,
    }


def test_r4_all_pass():
    result = audit.aggregate_global_status(components())

    assert result == "PASS"


def test_r4_fail_priority():
    result = audit.aggregate_global_status(
        components(
            operations="FAIL",
            artifacts="PASS",
            pennylane="NOT VERIFIED",
            migration_status="PASS",
        )
    )

    assert result == "FAIL"


def test_r4_not_verified_priority():
    result = audit.aggregate_global_status(
        components(
            operations="PASS",
            artifacts="NOT VERIFIED",
            pennylane="PASS",
            migration_status="PASS",
        )
    )

    assert result == "NOT VERIFIED"


def test_r4_missing_component_not_verified():
    values = components()
    del values["migration_status"]

    result = audit.aggregate_global_status(values)

    assert result == "NOT VERIFIED"


def test_r4_invalid_status_not_verified():
    result = audit.aggregate_global_status(
        components(operations="UNKNOWN")
    )

    assert result == "NOT VERIFIED"


def test_r4_report_status_mismatch_fail():
    report = passing_report()
    report["components"]["operations_status"] = "FAIL"
    report["status"] = "PASS"

    result = audit.validate_numeric_report(report)

    assert result["status"] == "FAIL"
    assert any(
        "contradicts" in error.lower()
        for error in result["errors"]
    )


def test_r4_fail_over_not_verified():
    result = audit.aggregate_global_status(
        components(
            operations="NOT VERIFIED",
            artifacts="FAIL",
            pennylane="NOT VERIFIED",
            migration_status="PASS",
        )
    )

    assert result == "FAIL"
  
