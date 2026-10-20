"""Write a concise P2 benchmark summary for GitHub Actions."""

from __future__ import annotations

import json
import os
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]

REPORT_PATH = (
    P2_ROOT
    / "benchmarks"
    / "results"
    / "benchmark_report.json"
)


def main() -> int:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")

    if not summary_path:
        print("GITHUB_STEP_SUMMARY is not set.")
        return 0

    if not REPORT_PATH.is_file():
        print("No P2 benchmark report exists; skipping summary.")
        return 0

    try:
        report = json.loads(
            REPORT_PATH.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print("FAIL: cannot read benchmark report:", exc)
        return 1

    lines = [
        "## QFLPN P2 — Benchmark",
        "",
        f"**Status:** `{report.get('status', 'UNKNOWN')}`",
        "",
        f"- Qubits: `{report.get('qubits')}`",
        f"- Hilbert dimension: `{report.get('hilbert_dimension')}`",
        f"- Warmups: `{report.get('warmups')}`",
        f"- Repetitions: `{report.get('repetitions')}`",
        f"- Timer: `{report.get('timer')}`",
        "",
        "| Operation | Median (ns) | Mean (ns) | Std. dev. (ns) | Error |",
        "|---|---:|---:|---:|---:|",
    ]

    for row in report.get("operations", []):
        lines.append(
            "| "
            + str(row.get("operation"))
            + " | "
            + f"{row.get('median_ns', 0):.2f}"
            + " | "
            + f"{row.get('mean_ns', 0):.2f}"
            + " | "
            + f"{row.get('standard_deviation_ns', 0):.2f}"
            + " | "
            + f"{row.get('numerical_error', 0):.3e}"
            + " |"
        )

    lines.extend(
        [
            "",
            "PennyLane / NumPy maximum difference: "
            f"`{report.get('pennylane_numpy_maximum_difference')}`",
            "",
            "Benchmark results are supplementary performance evidence. "
            "They do not independently determine mathematical acceptance.",
            "",
        ]
    )

    with Path(summary_path).open(
        "a",
        encoding="utf-8",
    ) as stream:
        stream.write("\n".join(lines))

    print("P2 benchmark summary written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
