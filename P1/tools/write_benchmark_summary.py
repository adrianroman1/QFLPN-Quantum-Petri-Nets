"""Publish P1 benchmark measurements in GitHub Actions."""

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
    if not REPORT_PATH.is_file():
        return None

    try:
        report = json.loads(
            REPORT_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None

    return report if isinstance(report, dict) else None


def finite_number(value: Any) -> bool:
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


def format_pct(value: Any) -> str:
    if not finite_number(value):
        return "N/A"
    return f"{float(value):.3f}%"


def safe_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def build_summary() -> str:
    lines = [
        "",
        "## P1 — Execution-time benchmark",
        "",
    ]

    report = read_report()

    if report is None:
        lines.extend([
            "**Status:** `NOT AVAILABLE`",
            "",
            "The benchmark report is missing or invalid.",
            "",
        ])
        return "\n".join(lines)

    status = report.get("status", "UNKNOWN")

    lines.extend([
        f"**Benchmark status:** `{status}`",
        "",
    ])

    if status != "PASS":
        error_type = report.get("error_type", "UNKNOWN")
        error = report.get(
            "error",
            "No error details available.",
        )

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

    workload = safe_dict(report.get("workload"))
    configuration = safe_dict(report.get("configuration"))
    equivalence = safe_dict(report.get("equivalence_check"))
    results = safe_dict(report.get("results"))
    comparison = safe_dict(report.get("comparison"))
    environment = safe_dict(report.get("environment"))

    production = safe_dict(results.get("production"))
    independent = safe_dict(results.get("independent"))

    production_count = production.get("sample_count", "N/A")
    independent_count = independent.get("sample_count", "N/A")

    measurement_order = configuration.get(
        "measurement_order",
        "legacy_sequential_measurements",
    )

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
        f"| Measurement order | `{measurement_order}` |",
        f"| Numerical equivalence | `{equivalence.get('status', 'N/A')}` |",
        f"| Frobenius difference | `{equivalence.get('frobenius_difference', 'N/A')}` |",
        f"| Numerical tolerance | `{equivalence.get('tolerance', 'N/A')}` |",
        "",
        "### Measured execution times",
        "",
        "| Metric | Production | Independent reference | Comparative indicator |",
        "|---|---:|---:|---:|",
        f"| Minimum (ms) | {format_ms(production.get('minimum_ms'))} | {format_ms(independent.get('minimum_ms'))} | — |",
        f"| Median (ms) | **{format_ms(production.get('median_ms'))}** | {format_ms(independent.get('median_ms'))} | **{format_ratio(comparison.get('speedup_independent_over_production'))}** (reference / P1) |",
        f"| Mean (ms) | {format_ms(production.get('mean_ms'))} | {format_ms(independent.get('mean_ms'))} | — |",
        f"| Maximum (ms) | {format_ms(production.get('maximum_ms'))} | {format_ms(independent.get('maximum_ms'))} | — |",
        f"| Standard deviation (ms) | {format_ms(production.get('standard_deviation_ms'))} | {format_ms(independent.get('standard_deviation_ms'))} | — |",
        f"| Samples | {production_count} | {independent_count} | — |",
        "",
        "### Comparative indicators",
        "",
        f"- Independent / production median-time ratio: **{format_ratio(comparison.get('speedup_independent_over_production'))}**",
        f"- Median-time difference (independent − production): **{format_ms(comparison.get('median_difference_ms'))} ms**",
        f"- Production median-time reduction relative to the independent reference: **{format_pct(comparison.get('production_median_reduction_percent'))}**",
        "",
    ])

    paired_difference = comparison.get(
        "paired_median_difference_ms"
    )
    paired_win_rate = comparison.get(
        "production_pair_win_rate_percent"
    )
    paired_count = comparison.get("paired_sample_count")

    if (
        finite_number(paired_difference)
        and finite_number(paired_win_rate)
        and finite_number(paired_count)
    ):
        lines.extend([
            "### Paired comparison",
            "",
            f"- Median paired difference (independent − production): **{format_ms(paired_difference)} ms**",
            f"- Production wins among paired measurements: **{format_pct(paired_win_rate)}**",
            f"- Number of paired measurements: **{int(paired_count)}**",
            "",
            "A positive paired difference means production was faster "
            "in that pair. A production win rate above 50% means "
            "production was faster in more than half of the measured pairs.",
            "",
        ])
    else:
        lines.extend([
            "### Paired comparison",
            "",
            "Paired statistics are not available in this report. "
            "They will appear after a benchmark run using the "
            "alternating paired measurement method.",
            "",
        ])

    lines.extend([
        "A ratio greater than 1 means that the independent reference "
        "had a greater median execution time than P1 in this run.",
        "",
        "This is a relative runtime comparison, not a quantum speedup "
        "or an HPC scalability result.",
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
        "operator-construction workload (q=4, D=16).",
        "",
        "It does not establish large-scale quantum simulation, "
        "distributed execution, HPC scalability, or parallel speedup.",
        "",
        "Alternating paired measurements reduce systematic order bias, "
        "but do not eliminate virtual-machine contention, CPU-frequency "
        "variation, or other environmental noise.",
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
        with open(
            SUMMARY_PATH,
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(summary)

        print("P1 benchmark summary published.")
    else:
        print(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
