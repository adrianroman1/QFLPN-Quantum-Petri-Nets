"""Write the P2 validation result to the GitHub Actions job summary."""

from __future__ import annotations

import json
import os
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
REPORTS = P2_ROOT / "reports"


def read_json(name: str) -> dict | None:
    path = REPORTS / name

    if not path.is_file():
        return None

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def status(data: dict | None) -> str:
    if data is None:
        return "MISSING"

    return str(data.get("status", "UNKNOWN"))


def main() -> int:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")

    if not summary_path:
        print("GITHUB_STEP_SUMMARY is not set; summary not written.")
        return 0

    environment = read_json("environment_report.json")
    artifacts = read_json("artifact_validation.json")
    numerical = read_json("numerical_validation.json")
    parity = read_json("pennylane_parity.json")
    pytest = read_json("pytest-run.json")

    verdict = os.environ.get(
        "P2_VERDICT",
        "P2_PENDING",
    )

    lines = [
        "# QFLPN P2 — Validation Summary",
        "",
        f"**Final verdict:** `{verdict}`",
        "",
        "| Validation component | Status |",
        "|---|---|",
        f"| Execution environment | {status(environment)} |",
        f"| Reference artifacts | {status(artifacts)} |",
        f"| Numerical validation | {status(numerical)} |",
        f"| PennyLane / NumPy parity | {status(parity)} |",
        f"| Pytest | {status(pytest)} |",
        "",
    ]

    if pytest is not None:
        lines.extend(
            [
                f"Pytest exit code: `{pytest.get('exit_code')}`",
                "",
            ]
        )

    if environment is not None:
        git = environment.get("git", {})
        lines.extend(
            [
                f"Commit: `{git.get('commit', 'unknown')}`",
                f"Branch: `{git.get('branch', 'unknown')}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Evidence files",
            "",
            "- `P2/reports/environment_report.json`",
            "- `P2/reports/artifact_validation.json`",
            "- `P2/reports/numerical_validation.json`",
            "- `P2/reports/pennylane_parity.json`",
            "- `P2/reports/pytest-run.json`",
            "- `P2/reports/junit.xml`",
            "- `P2/MANIFEST.txt`",
            "- `P2/SHA256SUMS.txt`",
            "",
        ]
    )

    Path(summary_path).write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("P2 GitHub summary written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
