"""Run the complete P2 pytest suite and preserve machine-readable evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = P2_ROOT / "code"
TESTS_DIR = P2_ROOT / "tests"
REPORTS_DIR = P2_ROOT / "reports"
REPORT_FILE = REPORTS_DIR / "pytest-run.json"
JUNIT_FILE = REPORTS_DIR / "junit.xml"


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")

    temporary.write_text(
        json.dumps(
            data,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete QFLPN P2 pytest suite."
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-x", "--stop-on-first-failure", action="store_true")
    args = parser.parse_args()

    if not CODE_DIR.is_dir():
        print(f"FAIL: code directory not found: {CODE_DIR}")
        return 2

    if not TESTS_DIR.is_dir():
        print(f"FAIL: test directory not found: {TESTS_DIR}")
        return 2

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    code_path = str(CODE_DIR.resolve())

    env["PYTHONPATH"] = (
        code_path
        if not existing_pythonpath
        else code_path + os.pathsep + existing_pythonpath
    )

    command = [
        sys.executable,
        "-m",
        "pytest",
        str(TESTS_DIR),
        "--strict-markers",
        "-ra",
        f"--junitxml={JUNIT_FILE}",
    ]

    if args.verbose:
        command.append("-v")

    if args.stop_on_first_failure:
        command.append("-x")

    print("P2 root:", P2_ROOT)
    print("Code directory:", CODE_DIR)
    print("Test directory:", TESTS_DIR)
    print("Report directory:", REPORTS_DIR)
    print("Command:", " ".join(command))
    print("=" * 72)

    try:
        result = subprocess.run(
            command,
            cwd=P2_ROOT,
            env=env,
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

    report = {
        "schema_version": 2,
        "runner": "pytest",
        "command": command,
        "python_version": sys.version.split()[0],
        "working_directory": str(P2_ROOT),
        "test_directory": str(TESTS_DIR),
        "junit_report": str(JUNIT_FILE.relative_to(P2_ROOT)),
        "exit_code": exit_code,
        "status": "PASS" if exit_code == 0 else "FAIL",
        "stdout": stdout,
        "stderr": stderr,
    }

    try:
        atomic_write_json(REPORT_FILE, report)
    except (OSError, TypeError, ValueError) as exc:
        print(f"FAIL: could not write test report: {exc}")
        return 2

    print("=" * 72)
    print("Pytest exit code:", exit_code)
    print("JSON evidence:", REPORT_FILE)
    print("JUnit evidence:", JUNIT_FILE)
    print("STATUS:", "PASS" if exit_code == 0 else "FAIL")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
