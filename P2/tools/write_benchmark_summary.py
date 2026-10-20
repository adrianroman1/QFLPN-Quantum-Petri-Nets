"""Write paired P2 benchmark results to the GitHub Actions summary."""

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


def format_number(value, digits: int = 3) -> str:
    if not valid_number(value):
        return "INVALID"

    return f"{value:.{digits}f}"


def build_summary(report: dict) -> str:
    runtime = report.get("total_runtime_seconds")

    if valid_number(runtime) and runtime > 0:
        runtime_text = f"{runtime:.6f} seconds"
    else:
        runtime_text = "INVALID"

    production_total = report.get(
        "production_total_execution_seconds"
    )

    independent_total = report.get(
        "independent_total_execution_seconds"
    )

    combined_total = report.get(
        "combined_timed_execution_seconds"
    )

    lines = [
        "## QFLPN P2 — Paired Benchmark",
        "",
        f"**Status:** `{report.get('status', 'UNKNOWN')}`",
        "",
        f"**Total benchmark runtime:** `{runtime_text}`",
        "",
        (
            "**Production total execution time:** "
            f"`{format_number(production_total, 9)} seconds`"
        ),
        (
            "**Independent total execution time:** "
            f"`{format_number(independent_total, 9)} seconds`"
        ),
        (
            "**Combined timed execution time:** "
            f"`{format_number(combined_total, 9)} seconds`"
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
        (
            "| Operation | Production median (ns) | "
            "Independent median (ns) | "
            "Production reduction (%) | "
            "Production wins (%) | World record |"
        ),
        "|---|---:|---:|---:|---:|---|",
    ]

    operations = report.get("operations", [])

    if not isinstance(operations, list):
        operations = []

    for row in operations:
        if not isinstance(row, dict):
            continue

        production = row.get("production", {})
        independent = row.get("independent", {})
        paired = row.get("paired_comparison", {})
        world_record = row.get("world_record", {})

        lines.append(
            f"| {row.get('operation', 'UNKNOWN')}"
            f" | {format_number(production.get('median_ns'), 2)}"
            f" | {format_number(independent.get('median_ns'), 2)}"
            f" | {format_number(paired.get('production_reduction_percent_vs_independent'), 3)}"
            f" | {format_number(paired.get('production_win_rate_percent'), 2)}"
            f" | {world_record.get('display', 'MISSING')} |"
        )

    parity = report.get(
        "pennylane_numpy_maximum_difference"
    )

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
        "### World-record interpretation",
        "",
        (
            "A published result is not labelled a P2 world record unless "
            "the workload, operation, hardware, software and timing "
            "protocol are directly comparable."
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

    required_totals = (
        "production_total_execution_seconds",
        "independent_total_execution_seconds",
        "combined_timed_execution_seconds",
    )

    for field in required_totals:
        value = report.get(field)

        if not valid_number(value) or value < 0:
            print(f"FAIL: invalid benchmark total: {field}")
            return 1

    operations = report.get("operations")

    if not isinstance(operations, list) or not operations:
        print("FAIL: benchmark operation list is missing.")
        return 1

    for row in operations:
        if not isinstance(row, dict):
            print("FAIL: invalid operation record.")
            return 1

        if not isinstance(row.get("production"), dict):
            print("FAIL: production timing statistics are missing.")
            return 1

        if not isinstance(row.get("independent"), dict):
            print("FAIL: independent timing statistics are missing.")
            return 1

        if not isinstance(row.get("paired_comparison"), dict):
            print("FAIL: paired comparison statistics are missing.")
            return 1

        world_record = row.get("world_record")

        if not isinstance(world_record, dict):
            print("FAIL: world-record metadata is missing.")
            return 1

        if not isinstance(world_record.get("display"), str):
            print("FAIL: world-record display field is invalid.")
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

    print("P2 paired benchmark summary written.")
    print("Evidence files verified:", len(required_files))
    print("Benchmark status:", report.get("status", "UNKNOWN"))

    print(
        f"Total benchmark runtime: {runtime:.6f} seconds"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
