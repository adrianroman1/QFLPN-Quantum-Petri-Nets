"""Publish P1 benchmark measurements in the GitHub Actions job summary."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = ROOT / "P1" / "benchmarks"
REPORT_PATH = BENCHMARK_DIR / "benchmark_report.json"
CSV_PATH = BENCHMARK_DIR / "benchmark_results.csv"
ENVIRONMENT_PATH = BENCHMARK_DIR / "environment.txt"
MARKDOWN_PATH = BENCHMARK_DIR / "BENCHMARK_RESULTS.md"

SUMMARY_PATH = os.environ.get("GITHUB_STEP_SUMMARY")


def read_report() -> dict[str, Any] | None:
    """Read the benchmark JSON report without hiding invalid evidence."""

    if not REPORT_PATH.is_file():
        return None

    try:
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return report if isinstance(report, dict) else None


def finite_number(value: Any) -> bool:
    """Return True only for finite numeric values, excluding booleans."""

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def format_ms(value: Any) -> str:
    if not finite_number(value):
        return "N/A"
    return f"{float(value):.6f}"


def format_ratio(value: Any) -> str:
    if not finite_number(value):
        return "N/A"
    return f"{float(value):.6f}×"


def build_summary() -> str:
    lines: list[str] = []

    lines.extend([
        "",
        "## P1 — Execution-time benchmark",
        "",
    ])

    report = read_report()

    if report is None:
        lines.extend([
            "**Status:** `NOT AVAILABLE`",
            "",
            "The benchmark report is missing or is not valid JSON.",
            f"Expected file: `{REPORT_PATH.relative_to(ROOT)}`",
            "",
        ])
        return "\n".join(lines)

    status = report.get("status", "UNKNOWN")
    lines.append(f"**Benchmark status:** `{status}`")
    lines.append("")

    if status != "PASS":
        error_type = report.get("error_type", "UNKNOWN")
        error = report.get("error", "No error details available.")

        lines.extend([
            "**No valid timing result is available.**",
            "",
            f"- Error type: `{error_type}`",
            f"- Error: `{str(error).replace('|', '/')}`",
            "",
            "The benchmark is supplementary and does not determine "
            "the mathematical P1 acceptance verdict.",
            "",
        ])
        return "\n".join(lines)

    workload = report.get("workload")
    configuration = report.get("configuration")
    equivalence = report.get("equivalence_check")
    results = report.get("results")
    comparison = report.get("comparison")
    environment = report.get("environment")

    if not isinstance(workload, dict):
        workload = {}
    if not isinstance(configuration, dict):
        configuration = {}
    if not isinstance(equivalence, dict):
        equivalence = {}
    if not isinstance(results, dict):
        results = {}
    if not isinstance(comparison, dict):
        comparison = {}
    if not isinstance(environment, dict):
        environment = {}

    production = results.get("production")
    independent = results.get("independent")

    if not isinstance(production, dict):
        production = {}
    if not isinstance(independent, dict):
        independent = {}

    lines.extend([
        "### Workload",
        "",
        "| Parameter | Measured configuration |",
        "|---|---:|",
        f"| Qubit count | {workload.get('qubit_count', 'N/A')} |",
        f"| Hilbert dimension | {workload.get('hilbert_dimension', 'N/A')} |",
        f"| Operation | `{workload.get('operation', 'N/A')}` |",
        f"| Warm-ups | {configuration.get('warmups', 'N/A')} |",
        f"| Repetitions per implementation | {configuration.get('repetitions', 'N/A')} |",
        f"| Timer | `{configuration.get('timer', 'N/A')}` |",
        f"| Numerical equivalence | `{equivalence.get('status', 'N/A')}` |",
        f"| Frobenius difference | `{equivalence.get('frobenius_difference', 'N/A')}` |",
        f"| Numerical tolerance | `{equivalence.get('tolerance', 'N/A')}` |",
        "",
        "### Measured execution times",
        "",
        "| Metric | Production | Independent reference |",
        "|---|---:|---:|",
        f"| Minimum (ms) | {format_ms(production.get('minimum_ms'))} | {format_ms(independent.get('minimum_ms'))} |",
        f"| Median (ms) | {format_ms(production.get('median_ms'))} | {format_ms(independent.get('median_ms'))} |",
        f"| Mean (ms) | {format_ms(production.get('mean_ms'))} | {format_ms(independent.get('mean_ms'))} |",
        f"| Maximum (ms) | {format_ms(production.get('maximum_ms'))} | {format_ms(independent.get('maximum_ms'))} |",
        f"| Standard deviation (ms) | {format_ms(production.get('standard_deviation_ms'))} | {format_ms(independent.get('standard_deviation_ms'))} |",
        f"| Samples | {production.get('sample_count', 'N/A')} | {independent.get('sample_count', 'N/A')} |",
        "",
        "### Relative execution time",
        "",
        f"**Independent / production median-time ratio:** "
        f"`{format_ratio(comparison.get('speedup_independent_over_production'))}`",
        "",
        "A value greater than 1 means that the production implementation "
        "had a lower median execution time in this run. This is a relative "
        "runtime ratio, not a parallel speedup or an asymptotic complexity result.",
        "",
        "### Environment",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Timestamp UTC | `{report.get('timestamp_utc', 'N/A')}` |",
        f"| Git commit | `{environment.get('git_commit', 'N/A')}` |",
        f"| Python | `{environment.get('python_version', 'N/A')}` |",
        f"| NumPy | `{environment.get('numpy_version', 'N/A')}` |",
        f"| SciPy | `{environment.get('scipy_version', 'N/A')}` |",
        f"| Operating system | `{environment.get('operating_system', 'N/A')}` |",
        f"| CPU | `{environment.get('cpu_model', 'N/A')}` |",
        "",
        "### Benchmark evidence files",
        "",
    ])

    for path in (
        REPORT_PATH,
        CSV_PATH,
        ENVIRONMENT_PATH,
        MARKDOWN_PATH,
    ):
        relative = path.relative_to(ROOT)
        state = "present" if path.is_file() else "missing"
        lines.append(f"- `{relative}` — {state}")

    lines.extend([
        "",
        "### Scope and limitations",
        "",
        "This benchmark measures only the canonical P1 four-qubit "
        "operator-construction workload (q=4, D=16). It does not establish "
        "large-scale quantum simulation, distributed execution, HPC "
        "scalability, or parallel speedup.",
        "",
        "The reported values describe this GitHub Actions execution "
        "environment and should not be treated as universal performance "
        "guarantees.",
        "",
    ])

    return "\n".join(lines)


def main() -> int:
    summary = build_summary()

    if SUMMARY_PATH:
        with open(SUMMARY_PATH, "a", encoding="utf-8") as handle:
            handle.write(summary)

        print("P1 benchmark summary published.")
    else:
        print(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
