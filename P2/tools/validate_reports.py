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

EXPECTED_SCHEMA_VERSION = 2
EXPECTED_RUNNER = "pytest"


def reject_constant(value: str) -> None:
    """Reject non-standard JSON constants such as NaN and Infinity."""
    raise ValueError(f"Non-standard JSON constant: {value}")


def validate_finite_values(
    value: Any,
    location: str = "$",
) -> list[str]:
    """Reject non-finite floating-point values recursively."""
    errors: list[str] = []

    if isinstance(value, float):
        if not math.isfinite(value):
            errors.append(f"{location}: non-finite number")

    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(
                validate_finite_values(
                    item,
                    f"{location}[{index}]",
                )
            )

    elif isinstance(value, dict):
        for key, item in value.items():
            errors.extend(
                validate_finite_values(
                    item,
                    f"{location}.{key}",
                )
            )

    return errors


def validate_pytest_report(data: Any) -> list[str]:
    """
    Validate a pytest report dictionary against schema version 2.

    This function is intentionally independent of file I/O so that
    report validation can be tested directly.
    """
    if not isinstance(data, dict):
        return ["Pytest report root must be a JSON object"]

    errors: list[str] = []

    required_fields = {
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

    missing = required_fields - set(data)

    if missing:
        return [
            f"Missing report fields: {sorted(missing)}"
        ]

    if (
        type(data["schema_version"]) is not int
        or data["schema_version"] != EXPECTED_SCHEMA_VERSION
    ):
        errors.append(
            f"schema_version must be integer "
            f"{EXPECTED_SCHEMA_VERSION}"
        )

    if data["runner"] != EXPECTED_RUNNER:
        errors.append(
            f"runner must equal '{EXPECTED_RUNNER}'"
        )

    command = data["command"]

    if (
        not isinstance(command, list)
        or not command
        or any(
            not isinstance(argument, str) or not argument
            for argument in command
        )
    ):
        errors.append(
            "command must be a non-empty list of non-empty strings"
        )

    string_fields = (
        "python_version",
        "working_directory",
        "test_directory",
        "junit_report",
        "stdout",
        "stderr",
    )

    for field in string_fields:
        if not isinstance(data[field], str):
            errors.append(f"{field} must be a string")

    for field in (
        "python_version",
        "working_directory",
        "test_directory",
        "junit_report",
    ):
        value = data[field]

        if isinstance(value, str) and not value.strip():
            errors.append(f"{field} must not be empty")

    if (
        type(data["exit_code"]) is not int
        or data["exit_code"] != 0
    ):
        errors.append(
            "exit_code must be integer zero"
        )

    if data["status"] != "PASS":
        errors.append(
            "status must equal 'PASS'"
        )

    stdout = data["stdout"]

    if isinstance(stdout, str):
        if not stdout.strip():
            errors.append("stdout must not be empty")

        if "no tests ran" in stdout.lower():
            errors.append(
                "pytest reports that no tests ran"
            )

        if "failed" in stdout.lower():
            errors.append(
                "pytest output contains a failure indicator"
            )

    errors.extend(validate_finite_values(data))

    return errors


def validate_pytest_json(path: Path) -> list[str]:
    """Read and validate a schema-version-2 pytest JSON report."""
    try:
        raw = path.read_text(encoding="utf-8")

        data = json.loads(
            raw,
            parse_constant=reject_constant,
        )

    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        return [
            f"Invalid pytest JSON report: {exc}"
        ]

    return validate_pytest_report(data)


def validate_junit(path: Path) -> list[str]:
    """Validate JUnit XML structure and execution counters."""
    errors: list[str] = []

    if not path.is_file():
        return [
            f"JUnit report does not exist: {path}"
        ]

    try:
        root = ET.parse(path).getroot()

    except (OSError, ET.ParseError) as exc:
        return [
            f"Invalid JUnit XML: {exc}"
        ]

    if root.tag not in {
        "testsuite",
        "testsuites",
    }:
        return [
            f"Unexpected JUnit root element: {root.tag}"
        ]

    suites = (
        [root]
        if root.tag == "testsuite"
        else list(root.iter("testsuite"))
    )

    if not suites:
        return [
            "JUnit contains no testsuite elements"
        ]

    test_count = 0
    failure_count = 0
    error_count = 0
    skipped_count = 0

    for suite in suites:
        try:
            tests = int(suite.attrib.get("tests", "0"))
            failures = int(suite.attrib.get("failures", "0"))
            suite_errors = int(suite.attrib.get("errors", "0"))
            skipped = int(suite.attrib.get("skipped", "0"))

        except (TypeError, ValueError):
            errors.append(
                "JUnit contains invalid numeric counters"
            )
            continue

        if min(tests, failures, suite_errors, skipped) < 0:
            errors.append(
                "JUnit counters must not be negative"
            )
            continue

        test_count += tests
        failure_count += failures
        error_count += suite_errors
        skipped_count += skipped

    if test_count <= 0:
        errors.append(
            "JUnit contains zero tests"
        )

    if failure_count != 0:
        errors.append(
            f"JUnit reports {failure_count} failures"
        )

    if error_count != 0:
        errors.append(
            f"JUnit reports {error_count} errors"
        )

    if skipped_count > test_count:
        errors.append(
            "JUnit skipped count exceeds total test count"
        )

    print("JUnit tests:", test_count)
    print("JUnit failures:", failure_count)
    print("JUnit errors:", error_count)
    print("JUnit skipped:", skipped_count)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate P2 machine-readable test evidence."
        )
    )

    parser.add_argument(
        "--directory",
        type=Path,
        default=REPORTS_DIR,
    )

    args = parser.parse_args()
    directory = args.directory.resolve()

    if not directory.is_dir():
        print(
            "FAIL: report directory does not exist:",
            directory,
        )
        return 2

    pytest_report = directory / "pytest-run.json"
    junit_report = directory / "junit.xml"

    errors = validate_pytest_json(pytest_report)
    errors.extend(validate_junit(junit_report))

    print("=" * 72)

    if errors:
        for error in errors:
            print("FAIL:", error)

        print("VERDICT: P2_REPORTS_REJECTED")
        return 1

    print("PASS: JSON schema version 2")
    print("PASS: pytest execution status")
    print("PASS: JUnit test evidence")
    print("VERDICT: P2_REPORTS_ACCEPTED")

    return 0


if __name__ == "__main__":
    sys.exit(main())
