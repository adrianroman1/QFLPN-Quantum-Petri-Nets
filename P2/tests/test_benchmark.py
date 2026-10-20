"""Regression and adversarial tests for the P2 benchmark validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

P2_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = (
    P2_ROOT
    / "benchmarks"
    / "validate_benchmark.py"
)

SPEC = importlib.util.spec_from_file_location(
    "p2_benchmark_validator",
    VALIDATOR_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load P2 benchmark validator.")

VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


EXPECTED_OPERATIONS = sorted(
    VALIDATOR.EXPECTED_OPERATIONS
)


def valid_report() -> dict:
    rows = []

    for name in EXPECTED_OPERATIONS:
        rows.append(
            {
                "operation": name,
                "warmups": 5,
                "repetitions": 30,
                "minimum_ns": 100,
                "median_ns": 150,
                "mean_ns": 160.0,
                "maximum_ns": 250,
                "standard_deviation_ns": 20.0,
                "numerical_error": 1e-14,
                "numerical_tolerance": 1e-12,
                "passed": True,
            }
        )

    return {
        "schema_version": 1,
        "project": "QFLPN P2",
        "qubits": 4,
        "hilbert_dimension": 16,
        "basis_order": "big-endian",
        "operator_order": "U = C3X @ U_rot",
        "warmups": 5,
        "repetitions": 30,
        "pennylane_numpy_maximum_difference": 1e-14,
        "numerical_tolerance": 1e-12,
        "operations": rows,
        "all_checks_pass": True,
        "status": "PASS",
    }


def test_valid_benchmark_report_is_accepted():
    assert VALIDATOR.validate_report(valid_report()) == []


def test_report_rejects_wrong_qubit_count():
    report = valid_report()
    report["qubits"] = 5

    errors = VALIDATOR.validate_report(report)

    assert any("four qubits" in error for error in errors)


def test_report_rejects_wrong_hilbert_dimension():
    report = valid_report()
    report["hilbert_dimension"] = 32

    errors = VALIDATOR.validate_report(report)

    assert any("dimension must be 16" in error for error in errors)


def test_report_rejects_insufficient_warmups():
    report = valid_report()
    report["warmups"] = 1

    errors = VALIDATOR.validate_report(report)

    assert any("five warmups" in error for error in errors)


def test_report_rejects_insufficient_repetitions():
    report = valid_report()
    report["repetitions"] = 2

    errors = VALIDATOR.validate_report(report)

    assert any("30 repetitions" in error for error in errors)


def test_report_rejects_failed_operation():
    report = valid_report()
    report["operations"][0]["passed"] = False

    errors = VALIDATOR.validate_report(report)

    assert any(
        "numerical validation did not pass" in error
        for error in errors
    )


def test_report_rejects_missing_operation():
    report = valid_report()
    report["operations"].pop()

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Missing benchmark operations" in error
        for error in errors
    )


def test_report_rejects_duplicate_operation():
    report = valid_report()
    report["operations"].append(
        dict(report["operations"][0])
    )

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Duplicate benchmark operation" in error
        for error in errors
    )


def test_report_rejects_non_finite_timing():
    report = valid_report()
    report["operations"][0]["median_ns"] = float("nan")

    errors = VALIDATOR.validate_report(report)

    assert any(
        "invalid numeric field median_ns" in error
        for error in errors
    )


def test_report_rejects_negative_standard_deviation():
    report = valid_report()
    report["operations"][0]["standard_deviation_ns"] = -1.0

    errors = VALIDATOR.validate_report(report)

    assert any(
        "negative standard deviation" in error
        for error in errors
    )


def test_report_rejects_excessive_numerical_error():
    report = valid_report()
    report["operations"][0]["numerical_error"] = 1e-5

    errors = VALIDATOR.validate_report(report)

    assert any(
        "exceeds tolerance" in error
        for error in errors
    )


def test_report_rejects_failed_pennylane_parity():
    report = valid_report()
    report["pennylane_numpy_maximum_difference"] = 1e-3

    errors = VALIDATOR.validate_report(report)

    assert any(
        "PennyLane/NumPy parity check failed" in error
        for error in errors
    )


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        [],
        "invalid",
        1,
    ],
)
def test_report_rejects_non_object_root(invalid):
    assert VALIDATOR.validate_report(invalid)


def test_report_rejects_non_pass_status():
    report = valid_report()
    report["status"] = "WARNING"

    errors = VALIDATOR.validate_report(report)

    assert any(
        "status must be PASS" in error
        for error in errors
    )
