"""Fail-closed validation of JSON reports."""

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
    raise ValueError(f"Non-standard JSON constant: {value}")


def validate_finite_values(value: Any, location: str = "$") -> list[str]:
    errors: list[str] = []

    if isinstance(value, float) and not math.isfinite(value):
        errors.append(f"{location}: non-finite number")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(validate_finite_values(item, f"{location}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            errors.extend(validate_finite_values(item, f"{location}.{key}"))

    return errors


def validate_json_file(path: Path) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw, parse_constant=reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"{path}: invalid or unreadable JSON: {exc}"]

    return [f"{path}: {error}" for error in validate_finite_values(parsed)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=REPORTS_DIR)
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Explicitly allow a report directory with no JSON files.",
    )
    args = parser.parse_args(argv)

    directory = args.directory.resolve()
    if not directory.is_dir():
        print(f"FAIL: report directory does not exist: {directory}")
        return 2

    files = sorted(path for path in directory.rglob("*.json") if path.is_file())
    if not files:
        if args.allow_empty:
            print(f"PASS: no JSON reports; empty directory explicitly allowed: {directory}")
            return 0
        print(f"FAIL: no JSON reports found in {directory}")
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

    print(f"Checked: {len(files)}; errors: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
