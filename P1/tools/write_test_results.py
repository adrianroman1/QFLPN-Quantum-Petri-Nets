"""Aggregate pytest/JUnit and numerical evidence without allowing false PASS."""
from __future__ import annotations

import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from P1.tools.constants import NUMERICAL_TOLERANCE

REPORTS = ROOT / "P1" / "reports"


def junit_counts(path: Path) -> tuple[int, int, int, int, list[str]]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = failures = errors = skipped = 0
    names: list[str] = []
    for suite in suites:
        tests += int(suite.attrib.get("tests", 0))
        failures += int(suite.attrib.get("failures", 0))
        errors += int(suite.attrib.get("errors", 0))
        skipped += int(suite.attrib.get("skipped", 0))
        names.extend(case.attrib.get("classname", "") + "::" + case.attrib.get("name", "")
                     for case in suite.findall("testcase"))
    return tests, failures, errors, skipped, names


def main() -> None:
    junit = REPORTS / "junit.xml"
    exit_file = REPORTS / "pytest_exit_code.txt"
    residual_file = REPORTS / "residuals.json"
    independent_file = REPORTS / "independent_agreement.json"
    required = [junit, exit_file, residual_file, independent_file]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("Missing evidence: " + ", ".join(missing))

    tests, failures, errors, skipped, names = junit_counts(junit)
    exit_code = int(exit_file.read_text(encoding="utf-8").strip())
    residuals = json.loads(residual_file.read_text(encoding="utf-8"))
    independent = json.loads(independent_file.read_text(encoding="utf-8"))

    residual_keys = [
        "operator_unitarity_frobenius", "density_trace_absolute_error",
        "density_hermiticity_frobenius", "density_psd_residual",
        "state_norm_absolute_error", "state_evolution_l2_residual",
        "pure_state_density_frobenius",
    ]
    residual_checks = {}
    for key in residual_keys:
        value = residuals.get(key)
        residual_checks[key] = (
            isinstance(value, (int, float)) and math.isfinite(float(value))
            and float(value) <= NUMERICAL_TOLERANCE
        )
    finite_checks = residuals.get("finite_checks", {})
    residual_checks["all_arrays_finite"] = bool(finite_checks) and all(finite_checks.values())
    independent_checks = independent.get("checks", {})
    checks = {
        "pytest_exit_code_zero": exit_code == 0,
        "pytest_tests_nonzero": tests > 0,
        "pytest_failures_zero": failures == 0,
        "pytest_errors_zero": errors == 0,
        "pytest_skipped_zero": skipped == 0,
        "residuals": all(residual_checks.values()),
        "independent_agreement": bool(independent_checks) and all(independent_checks.values()),
    }
    passed = all(checks.values())
    result = {
        "schema_version": 1,
        "pytest": {"exit_code": exit_code, "tests": tests, "failures": failures,
                   "errors": errors, "skipped": skipped, "test_cases": names},
        "numerical_tolerance": NUMERICAL_TOLERANCE,
        "residual_checks": residual_checks,
        "independent_checks": independent_checks,
        "checks": checks,
        "verdict": "P1_PENDING_PACKAGE_INTEGRITY" if passed else "P1_REJECTED",
        "note": "Final acceptance is decided only by verify_final_package.py after manifest and SHA-256 verification.",
    }
    (REPORTS / "test_log.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
