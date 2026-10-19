"""Validate JSON report syntax and reject non-finite numeric values."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


P2_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = P2_ROOT / "reports"


def reject_constant(value: str) -> None:
    """Reject non-standard JSON constants such as NaN and Infinity."""
    raise ValueError(f"Non-standard JSON numeric constant: {value}")


def validate_finite_values(value: Any, location: str = "$") -> list[str]:
    """Return validation errors for non-finite floating-point values."""
    errors: list[str] = []

    if isinstance(value, bool) or value is None:
        return errors

    if isinstance(value, float):
        if not math.isfinite(value):
            errors.append(f"{location}: non-finite float")
        return errors

    if isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(
                validate_finite_values(item, f"{location}[{index}]")
            )
        return errors

    if isinstance(value, dict):
        for key, item in value.items():
            errors.extend(
                validate_finite_values(item, f"{location}.{key}")
            )
        return errors

    return errors


def validate_json_file(path: Path) -> list[str]:
    """Validate one JSON file and return all detected errors."""
    errors: list[str] = []

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: read error: {exc}"]

    try:
        parsed = json.loads(
            raw,
            parse_constant=reject_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        return [f"{path}: invalid JSON: {exc}"]

    errors.extend(validate_finite_values(parsed))

    return [f"{path}: {error}" for error in errors]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate JSON reports in P2/reports."
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=REPORTS_DIR,
        help="Directory containing JSON reports.",
    )
    args = parser.parse_args()

    report_dir = args.directory.resolve()

    if not report_dir.is_dir():
        print(f"ERROR: Report directory does not exist: {report_dir}")
        return 2

    files = sorted(
        path
        for path in report_dir.rglob("*.json")
        if path.is_file()
    )

    if not files:
        print(f"INFO: No JSON reports found in {report_dir}")
        return 0

    all_errors: list[str] = []

    for path in files:
        errors = validate_json_file(path)

        if errors:
            all_errors.extend(errors)
            print("FAIL:", path)
        else:
            print("PASS: JSON syntax and finite-value checks:", path)

    print("-" * 72)
    print("JSON files checked:", len(files))
    print("Validation errors:", len(all_errors))

    for error in all_errors:
        print("ERROR:", error)

    return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
