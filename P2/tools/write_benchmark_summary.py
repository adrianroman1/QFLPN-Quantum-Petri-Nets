"""Write the P2 benchmark results to the GitHub Actions step summary."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = P2_ROOT / "benchmarks"

REPORT_PATH = BENCHMARK_DIR / "benchmark_report.json"
MARKDOWN_PATH = BENCHMARK_DIR / "BENCHMARK_RESULTS.md"
CSV_PATH = BENCHMARK_DIR / "benchmark_results.csv"
ENVIRONMENT_PATH = BENCHMARK_DIR / "environment.txt"


def valid_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def format_number(value) -> str:
    if not valid_number(value):
        return "INVALID"
    return f"{value:.3f}"


def build_summary(report: dict) -> str:
    runtime = report.get("total_runtime_seconds")

    if valid_number(runtime) and runtime > 0:
        runtime_text = f"{runtime:.6f} seconds"
    else:
        runtime_text = "INVALID"

    lines = [
        "## QFLPN P2 — Benchmark",
        "",
        f"**Status:** `{report.get('status', 'UNKNOWN')}`",
        "",
        f"**Total benchmark runtime:** `{runtime_text}`",
        "",
        (
            "**Runtime measurement scope:** "
            f"{report.get('runtime_measurement_scope', 'MISSING')}"
        ),
        "",
        f"- Benchmark ID: `{report.get('benchmark_id', 'UNKNOWN')}`",
        f"- Qubits: `{report.get('qubits', 'UNKNOWN')}`",
        f"- Hilbert dimension: `{report.get('hilbert_dimension', 'UNKNOWN')}`",
        f"- Basis order: `{report.get('basis_order', 'UNKNOWN')}`",
        f"- Operator order: `{report.get('operator_order', 'UNKNOWN')}`",
        f"- Warmups: `{report.get('warmups', 'UNKNOWN')}`",
        f"- Repetitions: `{report.get('repetitions', 'UNKNOWN')}`",
        f"- Timer: `{report.get('timer', 'UNKNOWN')}`",
        "",
        "| Operation | Median (ns) | Mean (ns) | Std. dev. (ns) | Throughput (ops/s) | Numerical error | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]

    operations = report.get("operations", [])

    if not isinstance(operations, list):
        operations = []

    for row in operations:
        if not isinstance(row, dict):
            continue

        numerical_error = row.get("numerical_error")
        if valid_number(numerical_error):
            error_text = f"{numerical_error:.3e}"
        else:
            error_text = "INVALID"

        lines.append(
            "| "
            + str(row.get("operation", "UNKNOWN"))
            + " | "
            + format_number(row.get("median_ns"))
            + " | "
            + format_number(row.get("mean_ns"))
            + " | "
            + format_number(row.get("standard_deviation_ns"))
            + " | "
            + format_number(row.get("operations_per_second"))
            + " | "
            + error_text
            + " | "
            + ("PASS" if row.get("passed") is True else "FAIL")
            + " |"
        )

    parity = report.get("pennylane_numpy_maximum_difference")

    if valid_number(parity):
        parity_text = f"{parity:.6e}"
    else:
        parity_text = "INVALID"

    lines.extend([
        "",
        (
            "PennyLane / independent NumPy maximum state difference: "
            f"`{parity_text}`"
        ),
        "",
        "### Evidence files",
        "",
        "- `BENCHMARK_RESULTS.md`",
        "- `benchmark_report.json`",
        "- `benchmark_results.csv`",
        "- `environment.txt`",
        "",
        (
            "Benchmark results are supplementary performance evidence. "
            "They do not independently determine mathematical acceptance."
        ),
        "",
    ])

    return "\n".join(lines)


def main() -> int:
    """Append the benchmark summary to GITHUB_STEP_SUMMARY."""

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")

    if not summary_path:
        print(
            "GITHUB_STEP_SUMMARY is not set; "
            "GitHub summary was not written."
        )
        return 0

    required_files = (
        REPORT_PATH,
        MARKDOWN_PATH,
        CSV_PATH,
        ENVIRONMENT_PATH,
    )

    missing = [
        path.name
        for path in required_files
        if not path.is_file()
    ]

    if missing:
        print(
            "FAIL: benchmark evidence files are missing:",
            ", ".join(missing),
        )
        return 1

    try:
        report = json.loads(
            REPORT_PATH.read_text(encoding="utf-8")
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        print("FAIL: cannot read benchmark JSON:", exc)
        return 1

    if not isinstance(report, dict):
        print("FAIL: benchmark JSON root is not an object.")
        return 1

    runtime = report.get("total_runtime_seconds")
    if not valid_number(runtime) or runtime <= 0:
        print("FAIL: total benchmark runtime is missing or invalid.")
        return 1

    try:
        summary = build_summary(report)

        with Path(summary_path).open(
            "a",
            encoding="utf-8",
        ) as stream:
            stream.write(summary)
    except (
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        print("FAIL: cannot write GitHub benchmark summary:", exc)
        return 1

    print("P2 benchmark summary written.")
    print("Evidence files verified:", len(required_files))
    print("Benchmark status:", report.get("status", "UNKNOWN"))
    print(f"Total benchmark runtime: {runtime:.6f} seconds")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
