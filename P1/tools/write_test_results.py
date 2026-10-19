"""Aggregate pytest/JUnit and numerical evidence without allowing false PASS."""
from __future__ import annotations

import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from P1.tools.constants import NUMERICAL_TOLERANCE

REPORTS = ROOT / "P1" / "reports"

RESIDUAL_KEYS = (
    "operator_unitarity_frobenius",
    "density_trace_absolute_error",
    "density_hermiticity_frobenius",
    "density_psd_residual",
    "state_norm_absolute_error",
    "state_evolution_l2_residual",
    "pure_state_density_frobenius",
)

INDEPENDENT_METRIC_KEYS = (
    "operator_difference_frobenius",
    "state_difference_l2",
    "state_fidelity_error",
)

REQUIRED_EVIDENCE = (
    "junit.xml",
    "pytest_exit_code.txt",
    "residuals.json",
    "independent_agreement.json",
)


def is_valid_numeric(value: object) -> bool:
    """Accept finite int/float values, but never bool."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def load_json_object(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    """Load a JSON object; record malformed or incorrectly typed reports."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(
            f"{label}: unable to read valid JSON "
            f"({type(exc).__name__}: {exc})"
        )
        return None

    if not isinstance(value, dict):
        errors.append(f"{label}: JSON root must be an object")
        return None

    return value


def validate_residual_report(
    report: dict[str, Any] | None,
    errors: list[str],
) -> dict[str, bool]:
    """Validate the actual residuals.json schema produced by compute_residuals.py."""
    if report is None:
        return {}

    valid = True

    if report.get("status") != "PASS":
        errors.append("residuals.json: status must be exactly 'PASS'")
        valid = False

    if report.get("all_checks_pass") is not True:
        errors.append("residuals.json: all_checks_pass must be exactly true")
        valid = False

    tolerance = report.get("numerical_tolerance")
    if not is_valid_numeric(tolerance) or tolerance != NUMERICAL_TOLERANCE:
        errors.append("residuals.json: numerical_tolerance is invalid or mismatched")
        valid = False

    finite_checks = report.get("finite_checks")
    if not isinstance(finite_checks, dict) or not finite_checks:
        errors.append("residuals.json: finite_checks must be a non-empty object")
        valid = False
        finite_checks = {}

    normalized_finite_checks: dict[str, bool] = {}
    for key in (
        "operator_finite",
        "initial_state_finite",
        "final_state_finite",
        "density_matrix_finite",
    ):
        value = finite_checks.get(key)
        if not isinstance(value, bool):
            errors.append(f"residuals.json: finite_checks.{key} must be boolean")
            valid = False
            normalized_finite_checks[key] = False
        else:
            normalized_finite_checks[key] = value
            if value is not True:
                errors.append(f"residuals.json: finite_checks.{key} is false")
                valid = False

    residual_checks: dict[str, bool] = {}
    for key in RESIDUAL_KEYS:
        value = report.get(key)
        if not is_valid_numeric(value):
            errors.append(f"residuals.json: {key} must be a finite numeric value")
            residual_checks[key] = False
            valid = False
            continue

        passed = 0.0 <= float(value) <= NUMERICAL_TOLERANCE
        residual_checks[key] = passed
        if not passed:
            errors.append(
                f"residuals.json: {key} is negative or exceeds tolerance"
            )
            valid = False

    # The producer writes a combined checks object containing all finite
    # checks and all seven numerical residual checks.
    checks = report.get("checks")
    if not isinstance(checks, dict) or not checks:
        errors.append("residuals.json: checks must be a non-empty object")
        valid = False
    else:
        expected_check_keys = set(finite_checks) | set(RESIDUAL_KEYS)
        if set(checks) != expected_check_keys:
            errors.append("residuals.json: checks keys do not match producer schema")
            valid = False

        for key, value in checks.items():
            if not isinstance(value, bool):
                errors.append(f"residuals.json: checks.{key} must be boolean")
                valid = False
            elif value is not True:
                errors.append(f"residuals.json: checks.{key} is false")
                valid = False

    if not valid:
        residual_checks["schema_and_values_valid"] = False
    else:
        residual_checks["schema_and_values_valid"] = True

    return residual_checks


def validate_independent_report(
    report: dict[str, Any] | None,
    errors: list[str],
) -> dict[str, bool]:
    """Validate the actual independent_agreement.json producer schema."""
    if report is None:
        return {}

    valid = True

    if report.get("status") != "PASS":
        errors.append("independent_agreement.json: status must be exactly 'PASS'")
        valid = False

    if report.get("all_checks_pass") is not True:
        errors.append(
            "independent_agreement.json: all_checks_pass must be exactly true"
        )
        valid = False

    tolerance = report.get("numerical_tolerance")
    if not is_valid_numeric(tolerance) or tolerance != NUMERICAL_TOLERANCE:
        errors.append(
            "independent_agreement.json: numerical_tolerance is invalid or mismatched"
        )
        valid = False

    checks = report.get("checks")
    if not isinstance(checks, dict) or not checks:
        errors.append("independent_agreement.json: checks must be a non-empty object")
        checks = {}
        valid = False
    else:
        for key, value in checks.items():
            if not isinstance(value, bool):
                errors.append(
                    f"independent_agreement.json: checks.{key} must be boolean"
                )
                valid = False
            elif value is not True:
                errors.append(
                    f"independent_agreement.json: checks.{key} is false"
                )
                valid = False

    metric_results: dict[str, bool] = {}
    for key in INDEPENDENT_METRIC_KEYS:
        value = report.get(key)
        if not is_valid_numeric(value):
            errors.append(
                f"independent_agreement.json: {key} must be finite numeric"
            )
            metric_results[key] = False
            valid = False
            continue

        passed = 0.0 <= float(value) <= NUMERICAL_TOLERANCE
        metric_results[key] = passed
        if not passed:
            errors.append(
                f"independent_agreement.json: {key} is negative or exceeds tolerance"
            )
            valid = False

    metric_results["schema_and_checks_valid"] = valid
    return metric_results


def junit_counts(
    path: Path,
) -> tuple[int, int, int, int, list[str], list[str]]:
    """Reconcile declared JUnit counters with observed testcase elements.

    Testcases are collected once from the complete XML tree. For declared
    counters, use the root testsuites/testsuites aggregate when present.
    Otherwise sum only leaf testsuite elements to avoid counting nested
    suite totals twice.
    """
    root = ET.parse(path).getroot()

    testcases = list(root.iter("testcase"))
    observed_tests = len(testcases)
    observed_failures = sum(bool(case.findall("failure")) for case in testcases)
    observed_errors = sum(bool(case.findall("error")) for case in testcases)
    observed_skipped = sum(bool(case.findall("skipped")) for case in testcases)

    if root.tag in ("testsuite", "testsuites") and all(
        key in root.attrib
        for key in ("tests", "failures", "errors", "skipped")
    ):
        declared_tests = int(root.attrib["tests"])
        declared_failures = int(root.attrib["failures"])
        declared_errors = int(root.attrib["errors"])
        declared_skipped = int(root.attrib["skipped"])
    else:
        suites = list(root.iter("testsuite"))
        leaf_suites = [
            suite
            for suite in suites
            if not suite.findall("testsuite")
        ]

        if not leaf_suites and root.tag == "testsuite":
            leaf_suites = [root]

        declared_tests = sum(int(s.attrib.get("tests", 0)) for s in leaf_suites)
        declared_failures = sum(
            int(s.attrib.get("failures", 0)) for s in leaf_suites
        )
        declared_errors = sum(
            int(s.attrib.get("errors", 0)) for s in leaf_suites
        )
        declared_skipped = sum(
            int(s.attrib.get("skipped", 0)) for s in leaf_suites
        )

    names = [
        case.attrib.get("classname", "") + "::" + case.attrib.get("name", "")
        for case in testcases
    ]

    reconciliation_errors: list[str] = []
    comparisons = (
        ("tests", declared_tests, observed_tests),
        ("failures", declared_failures, observed_failures),
        ("errors", declared_errors, observed_errors),
        ("skipped", declared_skipped, observed_skipped),
    )

    for label, declared, observed in comparisons:
        if declared != observed:
            reconciliation_errors.append(
                f"JUnit {label} mismatch: declared={declared}, observed={observed}"
            )

    return (
        observed_tests,
        observed_failures,
        observed_errors,
        observed_skipped,
        names,
        reconciliation_errors,
    )


def write_rejection(
    errors: list[str],
    *,
    pytest: dict[str, Any] | None = None,
    residual_checks: dict[str, bool] | None = None,
    independent_checks: dict[str, bool] | None = None,
    checks: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Always write a machine-readable rejected test log before exiting."""
    REPORTS.mkdir(parents=True, exist_ok=True)

    result = {
        "schema_version": 1,
        "pytest": pytest or {
            "exit_code": None,
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "test_cases": [],
        },
        "numerical_tolerance": NUMERICAL_TOLERANCE,
        "residual_checks": residual_checks or {},
        "independent_checks": independent_checks or {},
        "checks": checks or {},
        "verdict": "P1_REJECTED",
        "errors": errors,
        "note": (
            "Evidence aggregation failed. Final acceptance is decided only by "
            "verify_final_package.py after manifest and SHA-256 verification."
        ),
    }

    output = REPORTS / "test_log.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    evidence_paths = {name: REPORTS / name for name in REQUIRED_EVIDENCE}
    missing = [
        str(path.relative_to(ROOT))
        for path in evidence_paths.values()
        if not path.is_file()
    ]

    if missing:
        errors.append("Missing required evidence: " + ", ".join(missing))
        write_rejection(errors)
        raise SystemExit(1)

    # Parse JUnit without allowing malformed XML or invalid counters to
    # prevent creation of a rejection report.
    try:
        (
            tests,
            failures,
            test_errors,
            skipped,
            names,
            junit_errors,
        ) = junit_counts(evidence_paths["junit.xml"])
        errors.extend(junit_errors)
    except Exception as exc:
        tests = failures = test_errors = skipped = 0
        names = []
        errors.append(
            f"JUnit evidence invalid: {type(exc).__name__}: {exc}"
        )

    # The exit-code file must contain one integer and nothing else.
    exit_code: int | None = None
    try:
        raw_exit = evidence_paths["pytest_exit_code.txt"].read_text(
            encoding="utf-8"
        ).strip()
        if not raw_exit or not raw_exit.isdecimal():
            raise ValueError("exit code must be a non-negative decimal integer")
        exit_code = int(raw_exit)
    except Exception as exc:
        errors.append(
            f"pytest exit-code evidence invalid: {type(exc).__name__}: {exc}"
        )

    residual_report = load_json_object(
        evidence_paths["residuals.json"],
        "residuals.json",
        errors,
    )
    independent_report = load_json_object(
        evidence_paths["independent_agreement.json"],
        "independent_agreement.json",
        errors,
    )

    residual_checks = validate_residual_report(residual_report, errors)
    independent_checks = validate_independent_report(
        independent_report,
        errors,
    )

    checks = {
        "pytest_exit_code_zero": exit_code == 0,
        "pytest_tests_nonzero": tests > 0,
        "pytest_failures_zero": failures == 0,
        "pytest_errors_zero": test_errors == 0,
        "pytest_skipped_zero": skipped == 0,
        "junit_counters_reconciled": not any(
            message.startswith("JUnit ") for message in errors
        ),
        "residuals": bool(residual_checks)
        and all(residual_checks.values()),
        "independent_agreement": bool(independent_checks)
        and all(independent_checks.values()),
    }

    if exit_code != 0:
        errors.append(f"pytest exit code is not zero: {exit_code!r}")
    if tests <= 0:
        errors.append("JUnit contains no observed testcases")
    if failures:
        errors.append(f"JUnit reports {failures} failing testcases")
    if test_errors:
        errors.append(f"JUnit reports {test_errors} testcases with errors")
    if skipped:
        errors.append(f"JUnit reports {skipped} skipped testcases")

    pytest_section = {
        "exit_code": exit_code,
        "tests": tests,
        "failures": failures,
        "errors": test_errors,
        "skipped": skipped,
        "test_cases": names,
    }

    passed = not errors and all(checks.values())

    result = {
        "schema_version": 1,
        "pytest": pytest_section,
        "numerical_tolerance": NUMERICAL_TOLERANCE,
        "residual_checks": residual_checks,
        "independent_checks": independent_checks,
        "checks": checks,
        "verdict": (
            "P1_PENDING_PACKAGE_INTEGRITY"
            if passed
            else "P1_REJECTED"
        ),
        "errors": errors,
        "note": (
            "Final acceptance is decided only by verify_final_package.py "
            "after manifest and SHA-256 verification."
        ),
    }

    output = REPORTS / "test_log.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2))

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
