"""Capture the execution environment for reproducible P2 validation."""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = P2_ROOT / "reports"

JSON_OUTPUT = REPORTS_DIR / "environment_report.json"
TEXT_OUTPUT = REPORTS_DIR / "environment.txt"

PACKAGES = (
    "numpy",
    "scipy",
    "pytest",
    "PennyLane",
    "autoray",
)


def command_output(command: list[str]) -> str:
    """Run a local diagnostic command without requiring success."""

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"UNAVAILABLE: {exc}"

    output = (result.stdout + result.stderr).strip()

    return output or f"NO OUTPUT (exit={result.returncode})"


def git_value(*arguments: str) -> str:
    """Read a Git value from the current repository."""

    return command_output(
        ["git", "-C", str(P2_ROOT.parent), *arguments]
    )


def package_versions() -> dict[str, str | None]:
    """Return installed package versions."""

    versions: dict[str, str | None] = {}

    for package in PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None

    return versions


def collect_environment() -> dict:
    """Collect reproducibility metadata without modifying source files."""

    return {
        "schema_version": 1,
        "project": "QFLPN P2",
        "captured_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "platform_string": platform.platform(),
        },
        "packages": package_versions(),
        "git": {
            "commit": git_value("rev-parse", "HEAD"),
            "branch": os.environ.get(
                "GITHUB_REF_NAME",
                git_value("branch", "--show-current"),
            ),
            "remote": git_value(
                "remote",
                "get-url",
                "origin",
            ),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get(
                "GITHUB_RUN_ATTEMPT"
            ),
            "github_workflow": os.environ.get(
                "GITHUB_WORKFLOW"
            ),
        },
        "diagnostics": {
            "uname": command_output(["uname", "-a"]),
            "cpu": command_output(["lscpu"]),
            "memory": command_output(["free", "-h"]),
        },
        "status": "OBSERVED_AT_GENERATION",
    }


def write_outputs(data: dict) -> None:
    """Write JSON and human-readable environment reports."""

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    JSON_OUTPUT.write_text(
        json.dumps(
            data,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    lines = [
        "QFLPN P2 EXECUTION ENVIRONMENT",
        "=" * 72,
        f"Captured UTC: {data['captured_at_utc']}",
        "",
        "PYTHON",
        json.dumps(data["python"], indent=2),
        "",
        "PLATFORM",
        json.dumps(data["platform"], indent=2),
        "",
        "PACKAGES",
        json.dumps(data["packages"], indent=2),
        "",
        "GIT",
        json.dumps(data["git"], indent=2),
        "",
        "DIAGNOSTICS",
        json.dumps(data["diagnostics"], indent=2),
        "",
        f"STATUS: {data['status']}",
    ]

    TEXT_OUTPUT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    try:
        data = collect_environment()
        write_outputs(data)
    except (OSError, TypeError, ValueError) as exc:
        print("FAIL:", exc)
        return 2

    print("Environment JSON:", JSON_OUTPUT)
    print("Environment text:", TEXT_OUTPUT)
    print("Python:", data["python"]["version"])
    print("Packages:", json.dumps(data["packages"], sort_keys=True))
    print("VERDICT: ENVIRONMENT_CAPTURED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
