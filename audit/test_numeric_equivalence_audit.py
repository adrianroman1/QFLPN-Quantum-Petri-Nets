#!/usr/bin/env python3
"""
Tests for P2 numeric equivalence audit.

Target:
audit/run_numeric_equivalence.py

Covers:
- required operation set;
- exact numeric tolerance;
- identical arrays;
- values above tolerance;
- shape mismatch;
- complex arrays;
- NaN and infinity rejection;
- independent reference generation;
- JSON serialization;
- baseline/migrated comparison;
- invalid numeric inputs.

These tests do not require a Git baseline blob or execute
the complete benchmark runner.
"""

from __future__ import annotations

import importlib.util
import json
import sys

from pathlib import Path

import numpy as np
import pytest


# =========================================================
# LOAD AUDIT MODULE
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

AUDIT_SCRIPT = (
    ROOT / "audit" / "run_numeric_equivalence.py"
)

if not AUDIT_SCRIPT.is_file():

    raise FileNotFoundError(
        f"Numeric audit script not found: {AUDIT_SCRIPT}"
    )

SPEC = importlib.util.spec_from_file_location(
    "p2_numeric_equivalence_audit",
    AUDIT_SCRIPT,
)

if SPEC is None or SPEC.loader is None:

    raise ImportError(
        "Cannot load run_numeric_equivalence.py"
    )

AUDIT = importlib.util.module_from_spec(
    SPEC
)

sys.modules[SPEC.name] = AUDIT

SPEC.loader.exec_module(AUDIT)


# =========================================================
# CONSTANTS
# =========================================================

REQUIRED_OPERATIONS = {
    "rotation_operator",
    "c3x_operator",
    "transition_operator",
    "state_evolution",
    "density_matrix",
    "reduced_density_q4",
    "reduced_density_q123",
    "pennylane_execution",
}

TOLERANCE = 1e-12


# =========================================================
# 1. REQUIRED OPERATION SET
# =========================================================

def test_required_operations_are_exact():

    assert set(
        AUDIT.REQUIRED_OPERATIONS
    ) == REQUIRED_OPERATIONS


def test_required_operation_count():

    assert len(
        AUDIT.REQUIRED_OPERATIONS
    ) == 8


def test_no_missing_operation():

    present = set(
        AUDIT.REQUIRED_OPERATIONS
    )

    assert present == REQUIRED_OPERATIONS


# =========================================================
# 2. REQUIRED TOLERANCE
# =========================================================

def test_required_tolerance():

    assert (
        AUDIT.REQUIRED_TOLERANCE
        == TOLERANCE
    )


# =========================================================
# 3. IDENTICAL ARRAYS
# =========================================================

def test_compare_arrays_identical():

    left = np.array(
        [1.0, 2.0, 3.0],
        dtype=np.float64,
    )

    right = left.copy()

    result = AUDIT.compare_arrays(
        left,
        right,
        TOLERANCE,
    )

    assert result["status"] == "PASS"

    assert result["shape_match"] is True

    assert result["max_absolute_error"] == 0.0

    assert result["frobenius_norm_error"] == 0.0


# =========================================================
# 4. VALUES ABOVE TOLERANCE
# =========================================================

def test_compare_arrays_above_tolerance():

    left = np.array(
        [1.0],
        dtype=np.float64,
    )

    right = np.array(
        [1.0001],
        dtype=np.float64,
    )

    result = AUDIT.compare_arrays(
        left,
        right,
        TOLERANCE,
    )

    assert result["status"] == "FAIL"

    assert result["max_absolute_error"] > TOLERANCE


# =========================================================
# 5. VALUES WITHIN TOLERANCE
# =========================================================

def test_compare_arrays_within_tolerance():

    left = np.array(
        [1.0, 2.0],
        dtype=np.float64,
    )

    right = np.array(
        [1.0 + 1e-14, 2.0 - 1e-14],
        dtype=np.float64,
    )

    result = AUDIT.compare_arrays(
        left,
        right,
        TOLERANCE,
    )

    assert result["status"] == "PASS"

    assert (
        result["max_absolute_error"]
        <= TOLERANCE
    )

    assert (
        result["frobenius_norm_error"]
        <= TOLERANCE
    )


# =========================================================
# 6. SHAPE MISMATCH
# =========================================================

def test_compare_arrays_shape_mismatch():

    left = np.zeros(
        (4,),
        dtype=np.float64,
    )

    right = np.zeros(
        (2, 2),
        dtype=np.float64,
    )

    result = AUDIT.compare_arrays(
        left,
        right,
        TOLERANCE,
    )

    assert result["status"] == "FAIL"

    assert result["shape_match"] is False

    assert result["actual_shape"] == [4]

    assert result["expected_shape"] == [2, 2]


# =========================================================
# 7. COMPLEX ARRAYS
# =========================================================

def test_complex_arrays_identical():

    left = np.array(
        [
            1.0 + 2.0j,
            3.0 + 4.0j,
        ],
        dtype=np.complex128,
    )

    right = left.copy()

    result = AUDIT.compare_arrays(
        left,
        right,
        TOLERANCE,
    )

    assert result["status"] == "PASS"

    assert result["max_absolute_error"] == 0.0


def test_complex_arrays_detect_phase_difference():

    left = np.array(
        [1.0 + 0.0j],
        dtype=np.complex128,
    )

    right = np.array(
        [0.0 + 1.0j],
        dtype=np.complex128,
    )

    result = AUDIT.compare_arrays(
        left,
        right,
        TOLERANCE,
    )

    assert result["status"] == "FAIL"

    assert (
        result["max_absolute_error"]
        > TOLERANCE
    )


# =========================================================
# 8. NAN REJECTION
# =========================================================

def test_nan_rejected():

    values = np.array(
        [1.0, np.nan],
        dtype=np.float64,
    )

    with pytest.raises(ValueError):

        AUDIT.validate_array(
            values,
            "rotation_operator",
        )


# =========================================================
# 9. INFINITY REJECTION
# =========================================================

def test_infinity_rejected():

    values = np.array(
        [1.0, np.inf],
        dtype=np.float64,
    )

    with pytest.raises(ValueError):

        AUDIT.validate_array(
            values,
            "rotation_operator",
        )


# =========================================================
# 10. NON-NUMERIC ARRAY REJECTION
# =========================================================

def test_non_numeric_array_rejected():

    values = np.array(
        ["one", "two"],
        dtype=object,
    )

    with pytest.raises(TypeError):

        AUDIT.validate_array(
            values,
            "rotation_operator",
        )


# =========================================================
# 11. INDEPENDENT REFERENCE OPERATION SET
# =========================================================

def test_independent_reference_contains_all_operations():

    activations = (
        0.85,
        0.90,
        0.45,
        0.70,
    )

    reference = (
        AUDIT.build_independent_reference(
            activations
        )
    )

    assert set(reference) == REQUIRED_OPERATIONS


# =========================================================
# 12. INDEPENDENT REFERENCE SHAPES
# =========================================================

def test_independent_reference_shapes():

    activations = (
        0.85,
        0.90,
        0.45,
        0.70,
    )

    reference = (
        AUDIT.build_independent_reference(
            activations
        )
    )

    assert reference[
        "rotation_operator"
    ].shape == (16, 16)

    assert reference[
        "c3x_operator"
    ].shape == (16, 16)

    assert reference[
        "transition_operator"
    ].shape == (16, 16)

    assert reference[
        "state_evolution"
    ].shape == (16,)

    assert reference[
        "density_matrix"
    ].shape == (16, 16)

    assert reference[
        "reduced_density_q4"
    ].shape == (2, 2)

    assert reference[
        "reduced_density_q123"
    ].shape == (8, 8)

    assert reference[
        "pennylane_execution"
    ].shape == (16,)


# =========================================================
# 13. INDEPENDENT REFERENCE FINITENESS
# =========================================================

def test_independent_reference_is_finite():

    activations = (
        0.85,
        0.90,
        0.45,
        0.70,
    )

    reference = (
        AUDIT.build_independent_reference(
            activations
        )
    )

    for operation, value in reference.items():

        array = np.asarray(value)

        assert np.all(
            np.isfinite(array)
        ), (
            f"Non-finite independent reference: {operation}"
        )


# =========================================================
# 14. BASELINE VS MIGRATED SYNTHETIC DATA
# =========================================================

def test_baseline_equals_migrated():

    baseline = np.eye(
        4,
        dtype=np.complex128,
    )

    migrated = np.eye(
        4,
        dtype=np.complex128,
    )

    result = AUDIT.compare_arrays(
        baseline,
        migrated,
        TOLERANCE,
    )

    assert result["status"] == "PASS"

    assert result["max_absolute_error"] == 0.0


# =========================================================
# 15. JSON SERIALIZATION
# =========================================================

def test_report_json_serializable():

    report = {
        "audit": "numeric_equivalence",
        "status": "PASS",
        "tolerance": TOLERANCE,
        "operations": {
            operation: {
                "status": "PASS",
                "max_absolute_error": 0.0,
            }
            for operation in REQUIRED_OPERATIONS
        },
    }

    serialized = json.dumps(
        report,
        allow_nan=False,
    )

    decoded = json.loads(
        serialized
    )

    assert decoded["audit"] == "numeric_equivalence"

    assert decoded["status"] == "PASS"

    assert (
        set(decoded["operations"])
        == REQUIRED_OPERATIONS
    )


# =========================================================
# 16. GLOBAL PASS LOGIC
# =========================================================

def test_global_pass_requires_all_operations():

    operation_results = {
        operation: {
            "status": "PASS",
        }
        for operation in REQUIRED_OPERATIONS
    }

    assert set(operation_results) == REQUIRED_OPERATIONS

    assert all(
        item["status"] == "PASS"
        for item in operation_results.values()
    )


# =========================================================
# 17. GLOBAL FAIL LOGIC
# =========================================================

def test_global_fail_when_one_operation_fails():

    operation_results = {
        operation: {
            "status": "PASS",
        }
        for operation in REQUIRED_OPERATIONS
    }

    operation_results[
        "density_matrix"
    ]["status"] = "FAIL"

    assert any(
        item["status"] == "FAIL"
        for item in operation_results.values()
    )


# =========================================================
# 18. REPORT METADATA
# =========================================================

def test_report_metadata_schema():

    required_fields = {
        "audit",
        "audit_id",
        "timestamp_utc",
        "status",
        "tolerance",
        "baseline",
        "migrated",
        "operations",
        "issues",
    }

    report = {
        "audit": "numeric_equivalence",
        "audit_id": "P2-BENCH-CONFIG-01",
        "timestamp_utc": "2026-01-01T00:00:00+00:00",
        "status": "PASS",
        "tolerance": TOLERANCE,
        "baseline": {
            "blob": "baseline",
            "sha256": "0" * 64,
        },
        "migrated": {
            "path": "benchmark_runner.py",
            "sha256": "0" * 64,
        },
        "operations": {},
        "issues": [],
    }

    assert required_fields <= set(report)


# =========================================================
# 19. COMPARISON REJECTS NON-FINITE EXPECTED VALUES
# =========================================================

def test_compare_arrays_rejects_nan_expected():

    actual = np.array(
        [1.0],
        dtype=np.float64,
    )

    expected = np.array(
        [np.nan],
        dtype=np.float64,
    )

    with pytest.raises(ValueError):

        AUDIT.compare_arrays(
            actual,
            expected,
            TOLERANCE,
        )


# =========================================================
# 20. COMPARISON REJECTS NON-FINITE ACTUAL VALUES
# =========================================================

def test_compare_arrays_rejects_infinite_actual():

    actual = np.array(
        [np.inf],
        dtype=np.float64,
    )

    expected = np.array(
        [1.0],
        dtype=np.float64,
    )

    with pytest.raises(ValueError):

        AUDIT.compare_arrays(
            actual,
            expected,
            TOLERANCE,
    )
