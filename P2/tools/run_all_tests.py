"""Run the complete P2 pytest suite and preserve JSON evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = P2_ROOT / "tests"
REPORTS_DIR = P2_ROOT / "reports"
REPORT_FILE = REPORTS_DIR / "pytest-run.json"


def write_report(
    command: list[str],
    exit_code: int,
    stdout: str,
    stderr: str,
) -> bool:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "schema_version": 1,
        "runner": "pytest",
        "command": command,
        "python_version": sys.version.split()[0],
        "exit_code": exit_code,
        "status": "PASS" if exit_code == 0 else "FAIL",
        "stdout": stdout,
        "stderr": stderr,
    }

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run all QFLPN P2 tests."
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
    )

    parser.add_argument(
        "-x",
        "--stop-on-first-failure",
        action="store_true",
    )

    args = parser.parse_args()

    if not TESTS_DIR.is_dir():
        print(f"ERROR: Test directory not found: {TESTS_DIR}")
        return 2

    command = [
        sys.executable,
        "-m",
        "pytest",
        str(TESTS_DIR),
        "--strict-markers",
    ]

    if args.verbose:
        command.append("-v")

    if args.stop_on_first_failure:
        command.append("-x")

    print("P2 root:", P2_ROOT)
    print("Test directory:", TESTS_DIR)
    print("Command:", " ".join(command))
    print("=" * 72)

    try:
        result = subprocess.run(
            command,
            cwd=P2_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        exit_code = int(result.returncode)
        stdout = result.stdout
        stderr = result.stderr

    except OSError as exc:
        exit_code = 2
        stdout = ""
        stderr = f"Could not execute pytest: {exc}"

    if stdout:
        print(stdout, end="")

    if stderr:
        print(stderr, file=sys.stderr, end="")

    print("=" * 72)
    print("Pytest exit code:", exit_code)

    try:
        write_report(
            command,
            exit_code,
            stdout,
            stderr,
        )
    except (OSError, TypeError, ValueError) as exc:
        print(f"ERROR: Could not write JSON evidence: {exc}")
        return 2

    print("JSON evidence:", REPORT_FILE)
    print("STATUS:", "PASS" if exit_code == 0 else "FAIL")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
