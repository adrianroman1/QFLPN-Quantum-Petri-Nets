"""Fail-closed validation of P2 JSON and JUnit test evidence."""

from __future__ import annotations

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET

from pathlib import Path
from typing import Any

P2_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = P2_ROOT / "reports"
PYTEST_REPORT = REPORTS_DIR / "pytest-run.json"


def reject_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON constant: {value}")


def validate_finite_values(
    value: Any,
    location: str = "$",
) -> list[str]:
    errors: list[str] = []

    if isinstance(value, float):
        if not math.isfinite(value):
            errors.append(f"{location}: non-finite number")

    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(
                validate_finite_values(item, f"{location}[{index}]")
            )

    elif isinstance(value, dict):
        for key, item in value.items():
            errors.extend(
                validate_finite_values(item, f"{location}.{key}")
            )

    return errors


def validate_pytest_json(path: Path) -> list[str]:
    errors: list[str] = []

    try:
        data = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"Invalid pytest JSON report: {exc}"]

    if not isinstance(data, dict):
        return ["Pytest report root must be a JSON object"]

    required = {
        "schema_version",
        "runner",
        "command",
        "python_version",
        "working_directory",
        "test_directory",
        "junit_report",
        "exit_code",
        "status",
        "stdout",
        "stderr",
    }

    missing = required - set(data)
    if missing:
        return [f"Missing report fields: {sorted(missing)}"]

    if type(data["schema_version"]) is not int or data["schema_version"] != 2:
        errors.append("Unsupported schema_version")

    if data["runner"] != "pytest":
        errors.append("runner must equal 'pytest'")

    if not isinstance(data["command"], list) or not data["command"]:
        errors.append("command must be a non-empty list")

    if not isinstance(data["python_version"], str) or not data["python_version"]:
        errors.append("python_version is missing")

    if type(data["exit_code"]) is not int or data["exit_code"] != 0:
        errors.append("pytest exit_code must be integer zero")

    if data["status"] != "PASS":
        errors.append("pytest status must equal PASS")

    if not isinstance(data["stdout"], str):
        errors.append("stdout must be a string")

    if not isinstance(data["stderr"], str):
        errors.append("stderr must be a string")

    if isinstance(data["stdout"], str):
        if "no tests ran" in data["stdout"].lower():
            errors.append("pytest reports that no tests ran")

    errors.extend(validate_finite_values(data))
    return errors


def validate_junit(path: Path) -> list[str]:
    errors: list[str] = []

    if not path.is_file():
        return [f"JUnit report does not exist: {path}"]

    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        return [f"Invalid JUnit XML: {exc}"]

    if root.tag not in {"testsuite", "testsuites"}:
        return [f"Unexpected JUnit root element: {root.tag}"]

    suites = (
        [root]
        if root.tag == "testsuite"
        else list(root.iter("testsuite"))
    )

    test_count = 0
    failure_count = 0
    error_count = 0

    for suite in suites:
        test_count += int(suite.attrib.get("tests", "0"))
        failure_count += int(suite.attrib.get("failures", "0"))
        error_count += int(suite.attrib.get("errors", "0"))

    if test_count <= 0:
        errors.append("JUnit contains zero tests")

    if failure_count != 0:
        errors.append(f"JUnit reports {failure_count} failures")

    if error_count != 0:
        errors.append(f"JUnit reports {error_count} errors")

    print("JUnit tests:", test_count)
    print("JUnit failures:", failure_count)
    print("JUnit errors:", error_count)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate P2 machine-readable test evidence."
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=REPORTS_DIR,
    )
    args = parser.parse_args()

    directory = args.directory.resolve()

    if not directory.is_dir():
        print("FAIL: report directory does not exist:", directory)
        return 2

    pytest_report = directory / "pytest-run.json"

    errors = validate_pytest_json(pytest_report)

    junit_path = directory / "junit.xml"
    errors.extend(validate_junit(junit_path))

    print("=" * 72)

    if errors:
        for error in errors:
            print("FAIL:", error)

        print("VERDICT: P2_REPORTS_REJECTED")
        return 1

    print("PASS: JSON schema and execution status")
    print("PASS: JUnit test evidence")
    print("VERDICT: P2_REPORTS_ACCEPTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
