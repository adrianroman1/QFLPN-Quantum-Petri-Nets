"""Fail-closed semantic validation of QFLPN P2 JSON reports."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

P2_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = P2_ROOT / "reports"

SUMMARY_PATTERN = re.compile(
    r"(?:(\d+)\s+passed)?"
    r"(?:,\s*)?"
    r"(?:(\d+)\s+failed)?"
    r"(?:,\s*)?"
    r"(?:(\d+)\s+error(?:s)?)?",
)


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


def validate_pytest_report(data: Any) -> list[str]:
    errors: list[str] = []
    label = "pytest-run.json"

    if not isinstance(data, dict):
        return [f"{label}: root must be a JSON object"]

    required = {
        "schema_version",
        "runner",
        "command",
        "python_version",
        "exit_code",
        "status",
        "stdout",
        "stderr",
    }

    missing = required - set(data)
    if missing:
        errors.append(
            f"{label}: missing fields: {sorted(missing)}"
        )
        return errors

    if type(data["schema_version"]) is not int:
        errors.append(f"{label}: schema_version must be an integer")
    elif data["schema_version"] != 1:
        errors.append(f"{label}: unsupported schema_version")

    if data["runner"] != "pytest":
        errors.append(f"{label}: runner must equal 'pytest'")

    if not isinstance(data["command"], list) or not data["command"]:
        errors.append(f"{label}: command must be a non-empty list")

    if not isinstance(data["python_version"], str) or not data["python_version"]:
        errors.append(f"{label}: invalid python_version")

    # bool is deliberately rejected: bool is a subclass of int in Python.
    if type(data["exit_code"]) is not int:
        errors.append(f"{label}: exit_code must be an integer")
    elif data["exit_code"] != 0:
        errors.append(f"{label}: exit_code is not zero")

    if data["status"] != "PASS":
        errors.append(f"{label}: status must equal PASS")

    if not isinstance(data["stdout"], str):
        errors.append(f"{label}: stdout must be a string")

    if not isinstance(data["stderr"], str):
        errors.append(f"{label}: stderr must be a string")

    if isinstance(data["stderr"], str) and data["stderr"].strip():
        errors.append(f"{label}: stderr is not empty")

    stdout = data.get("stdout")
    if isinstance(stdout, str):
        summaries = list(
            re.finditer(
                r"=+\s*(.*?)\s+in\s+[\d.]+s\s*=+",
                stdout,
                flags=re.MULTILINE,
            )
        )

        if not summaries:
            errors.append(f"{label}: pytest summary not found")
        else:
            summary = summaries[-1].group(1)

            passed_match = re.search(r"(\d+)\s+passed", summary)
            failed_match = re.search(r"(\d+)\s+failed", summary)
            error_match = re.search(r"(\d+)\s+errors?", summary)

            if not passed_match or int(passed_match.group(1)) <= 0:
                errors.append(f"{label}: no successful tests reported")

            if failed_match and int(failed_match.group(1)) != 0:
                errors.append(f"{label}: pytest reports failures")

            if error_match and int(error_match.group(1)) != 0:
                errors.append(f"{label}: pytest reports errors")

    return errors


def validate_json_file(path: Path) -> list[str]:
    try:
        parsed = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"{path}: invalid or unreadable JSON: {exc}"]

    errors = validate_finite_values(parsed)

    if path.name == "pytest-run.json":
        errors.extend(validate_pytest_report(parsed))

    return [f"{path}: {error}" for error in errors]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed P2 JSON report validation."
    )
    parser.add_argument("--directory", type=Path, default=REPORTS_DIR)
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args(argv)

    directory = args.directory.resolve()

    if not directory.is_dir():
        print(f"FAIL: report directory not found: {directory}")
        return 2

    files = sorted(
        path
        for path in directory.rglob("*.json")
        if path.is_file()
    )

    if not files:
        if args.allow_empty:
            print("PASS: empty directory explicitly allowed")
            return 0

        print("FAIL: no JSON reports found")
        return 1

    errors: list[str] = []

    for path in files:
        current = validate_json_file(path)

        if current:
            errors.extend(current)
            print("FAIL:", path)
        else:
            print("PASS:", path)

    for error in errors:
        print("ERROR:", error)

    print("=" * 72)
    print("Reports checked:", len(files))
    print("Errors:", len(errors))
    print("VERDICT:", "P2_REPORTS_ACCEPTED" if not errors else "P2_REJECTED")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
