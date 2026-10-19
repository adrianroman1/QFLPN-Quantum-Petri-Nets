"""Run the complete P2 pytest suite and preserve its exit status."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


P2_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = P2_ROOT / "tests"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run all QFLPN P2 tests."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose pytest output.",
    )
    parser.add_argument(
        "-x",
        "--stop-on-first-failure",
        action="store_true",
        help="Stop after the first test failure.",
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
            check=False,
        )
    except OSError as exc:
        print(f"ERROR: Could not start pytest: {exc}")
        return 2

    print("=" * 72)
    print("Pytest exit code:", result.returncode)

    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
