"""Reproducible P1 benchmark for the canonical four-qubit QFLPN instance."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from P1.code.qflpn_transition_operator import qflpn_transition_operator
from P1.tests.independent_reference import independent_global_operator

CANONICAL_MEMBERSHIPS = (0.85, 0.90, 0.45, 0.70)
QUANTUM_REGISTER_SIZE = 4
HILBERT_DIMENSION = 2 ** QUANTUM_REGISTER_SIZE
NUMERICAL_TOLERANCE = 1e-12

CSV_PATH = BENCHMARK_DIR / "benchmark_results.csv"
JSON_PATH = BENCHMARK_DIR / "benchmark_report.json"
ENV_PATH = BENCHMARK_DIR / "environment.txt"
MD_PATH = BENCHMARK_DIR / "BENCHMARK_RESULTS.md"

CSV_FIELDS = [
    "timestamp_utc",
    "operation",
    "implementation",
    "iteration",
    "elapsed_ns",
    "elapsed_ms",
    "qubit_count",
    "hilbert_dimension",
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def git_command(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return "UNAVAILABLE"
    except (OSError, subprocess.SubprocessError):
        return "UNAVAILABLE"


def cpu_model() -> str:
    for path in (
        Path("/proc/cpuinfo"),
        Path("/proc/device-tree/model"),
    ):
        try:
            content = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            for line in content.splitlines():
                lower = line.lower()
                if lower.startswith("model name") or lower.startswith("hardware"):
                    return line.split(":", 1)[-1].strip()

            if path.name == "model":
                return content.strip().replace("\x00", "")

        except OSError:
            continue

    return platform.processor() or "UNAVAILABLE"


def memory_bytes() -> int | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        value = int(pages) * int(page_size)
        return value if value > 0 else None
    except (AttributeError, OSError, ValueError):
        return None


def write_environment() -> dict:
    data = {
        "captured_at_utc": utc_now(),
        "repository_root": str(ROOT),
        "git_commit": git_command("rev-parse", "HEAD"),
        "git_branch": git_command("branch", "--show-current"),
        "git_worktree_status": git_command("status", "--short"),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "operating_system": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor() or "UNAVAILABLE",
        "cpu_model": cpu_model(),
        "logical_cpu_count": os.cpu_count(),
        "physical_memory_bytes": memory_bytes(),
        "benchmark_timer": "time.perf_counter_ns",
        "qubit_count": QUANTUM_REGISTER_SIZE,
        "hilbert_dimension": HILBERT_DIMENSION,
        "canonical_memberships": list(CANONICAL_MEMBERSHIPS),
        "numerical_equivalence_tolerance": NUMERICAL_TOLERANCE,
    }

    lines = [
        "P1 BENCHMARK ENVIRONMENT",
        "========================",
    ]

    for key, value in data.items():
        lines.append(
            f"{key}: {json.dumps(value, ensure_ascii=False)}"
        )

    ENV_PATH.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return data


def production_operator() -> np.ndarray:
    return np.asarray(
        qflpn_transition_operator(CANONICAL_MEMBERSHIPS),
        dtype=np.complex128,
    )


def independent_operator() -> np.ndarray:
    return np.asarray(
        independent_global_operator(CANONICAL_MEMBERSHIPS),
        dtype=np.complex128,
    )


def verify_equivalence() -> dict:
    production = production_operator()
    independent = independent_operator()

    expected_shape = (
        HILBERT_DIMENSION,
        HILBERT_DIMENSION,
    )

    if production.shape != expected_shape:
        raise AssertionError(
            f"Production shape mismatch: {production.shape}"
        )

    if independent.shape != production.shape:
        raise AssertionError(
            f"Independent shape mismatch: {independent.shape}"
        )

    if not np.isfinite(production).all():
        raise AssertionError(
            "Production operator contains non-finite values"
        )

    if not np.isfinite(independent).all():
        raise AssertionError(
            "Independent operator contains non-finite values"
        )

    difference = float(
        np.linalg.norm(production - independent, ord="fro")
    )

    if difference > NUMERICAL_TOLERANCE:
        raise AssertionError(
            "Implementations are not numerically equivalent: "
            f"Frobenius difference={difference:.17g}, "
            f"tolerance={NUMERICAL_TOLERANCE:.17g}"
        )

    return {
        "status": "PASS",
        "comparison": (
            "production qflpn_transition_operator versus "
            "independent_global_operator"
        ),
        "frobenius_difference": difference,
        "tolerance": NUMERICAL_TOLERANCE,
        "shape": list(production.shape),
    }


def validate_result(
    result: np.ndarray,
    implementation: str,
) -> None:
    if not isinstance(result, np.ndarray):
        raise TypeError(
            f"{implementation} returned "
            f"{type(result).__name__}, expected numpy.ndarray"
        )

    if not np.isfinite(result).all():
        raise ArithmeticError(
            f"{implementation} produced non-finite output"
        )

    expected_shape = (
        HILBERT_DIMENSION,
        HILBERT_DIMENSION,
    )

    if result.shape != expected_shape:
        raise AssertionError(
            f"{implementation} returned shape {result.shape}; "
            f"expected {expected_shape}"
        )


def measure_interleaved(
    production_function: Callable[[], np.ndarray],
    independent_function: Callable[[], np.ndarray],
    warmups: int,
    repetitions: int,
    timestamp: str,
) -> tuple[list[dict], list[int], list[int], list[float]]:
    """Measure both implementations in alternating paired order."""

    functions = {
        "production": production_function,
        "independent": independent_function,
    }

    samples = {
        "production": [],
        "independent": [],
    }

    rows = []
    paired_differences_ms = []

    # Alternate warm-up order to avoid always warming one implementation first.
    for iteration in range(warmups):
        if iteration % 2 == 0:
            order = ("production", "independent")
        else:
            order = ("independent", "production")

        for name in order:
            result = functions[name]()
            validate_result(result, name)

    # Each iteration is one paired comparison.
    for iteration in range(1, repetitions + 1):
        if iteration % 2 == 1:
            order = ("production", "independent")
        else:
            order = ("independent", "production")

        pair_ns = {}

        for name in order:
            start_ns = time.perf_counter_ns()
            result = functions[name]()
            elapsed_ns = time.perf_counter_ns() - start_ns

            # Validate after stopping the timer so validation is not timed.
            validate_result(result, name)

            elapsed_ns = int(elapsed_ns)
            samples[name].append(elapsed_ns)
            pair_ns[name] = elapsed_ns

            rows.append({
                "timestamp_utc": timestamp,
                "operation": "global_operator_construction",
                "implementation": name,
                "iteration": iteration,
                "elapsed_ns": elapsed_ns,
                "elapsed_ms": elapsed_ns / 1_000_000.0,
                "qubit_count": QUANTUM_REGISTER_SIZE,
                "hilbert_dimension": HILBERT_DIMENSION,
            })

        # Positive value means production was faster in this pair.
        paired_differences_ms.append(
            (
                pair_ns["independent"] - pair_ns["production"]
            ) / 1_000_000.0
        )

    return (
        rows,
        samples["production"],
        samples["independent"],
        paired_differences_ms,
    )


def summarize(samples: list[int]) -> dict:
    if not samples:
        raise ValueError("Cannot summarize an empty sample set")

    values_ms = [
        value / 1_000_000.0
        for value in samples
    ]

    return {
        "sample_count": len(values_ms),
        "minimum_ms": min(values_ms),
        "maximum_ms": max(values_ms),
        "mean_ms": statistics.mean(values_ms),
        "median_ms": statistics.median(values_ms),
        "standard_deviation_ms": (
            statistics.stdev(values_ms)
            if len(values_ms) > 1
            else 0.0
        ),
    }


def write_csv(rows: list[dict]) -> None:
    with CSV_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(report: dict) -> None:
    JSON_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )


def write_markdown(report: dict) -> None:
    if report["status"] != "PASS":
        content = (
            "# P1 Benchmark Results\n\n"
            "**Status:** FAIL\n\n"
            "Benchmark execution did not complete successfully. "
            "Inspect `benchmark_report.json`.\n"
        )
    else:
        production = report["results"]["production"]
        independent = report["results"]["independent"]
        comparison = report["comparison"]
        configuration = report["configuration"]

        ratio = comparison["speedup_independent_over_production"]
        paired_difference = comparison["paired_median_difference_ms"]
        win_rate = comparison["production_pair_win_rate_percent"]

        content = f"""# P1 Benchmark Results

## Scope

- Canonical register: **q = {report['workload']['qubit_count']} qubits**
- Hilbert-space dimension: **D = {report['workload']['hilbert_dimension']}**
- Operation: global QFLPN transition-operator construction
- Samples per implementation: **{configuration['repetitions']}**
- Warm-up iterations: **{configuration['warmups']}**
- Measurement order: **{configuration['measurement_order']}**
- Timer: `time.perf_counter_ns()`
- Numerical equivalence: **{report['equivalence_check']['status']}**
- Frobenius difference: `{report['equivalence_check']['frobenius_difference']:.6e}`
- Tolerance: `{report['equivalence_check']['tolerance']:.1e}`

## Measured execution times

| Metric | Production implementation | Independent implementation | Comparative indicator |
|---|---:|---:|---:|
| Minimum (ms) | {production['minimum_ms']:.6f} | {independent['minimum_ms']:.6f} | — |
| Median (ms) | **{production['median_ms']:.6f}** | {independent['median_ms']:.6f} | **{ratio:.6f}×** (reference / P1) |
| Mean (ms) | {production['mean_ms']:.6f} | {independent['mean_ms']:.6f} | — |
| Maximum (ms) | {production['maximum_ms']:.6f} | {independent['maximum_ms']:.6f} | — |
| Standard deviation (ms) | {production['standard_deviation_ms']:.6f} | {independent['standard_deviation_ms']:.6f} | — |
| Samples | {production['sample_count']} | {independent['sample_count']} | — |

## Paired comparison

- Median paired difference (independent − production): **{paired_difference:.6f} ms**
- Production wins among paired measurements: **{win_rate:.2f}%**
- Number of paired measurements: **{comparison['paired_sample_count']}**

A positive paired difference means production was faster in that pair.
A production win rate above 50% means production was faster in more than
half of the measured pairs. These statistics describe this execution only.

## Comparative indicators

- Independent / production median-time ratio: **{ratio:.6f}×**
- Median-time difference (independent − production): **{comparison['median_difference_ms']:.6f} ms**
- Production median-time reduction relative to the independent reference:
  **{comparison['production_median_reduction_percent']:.3f}%**

A ratio above 1 means the independent reference had a greater
median execution time than P1 in this measured run.

This is a relative runtime comparison, not a quantum speedup
or an HPC scalability result.

## Reproducibility

- Timestamp (UTC): `{report['timestamp_utc']}`
- Git commit: `{report['environment']['git_commit']}`
- Python: `{report['environment']['python_version']}`
- NumPy: `{report['environment']['numpy_version']}`
- SciPy: `{report['environment']['scipy_version']}`
- Platform: `{report['environment']['operating_system']}`
- CPU: `{report['environment']['cpu_model']}`

Raw paired samples are stored in `benchmark_results.csv`.
Structured results are stored in `benchmark_report.json`.
The captured environment is stored in `environment.txt`.

## Interpretation and limitations

This benchmark measures construction of the **canonical four-qubit P1
operator only**. It is not a benchmark of a scalable quantum simulator,
a million-qubit system, a distributed implementation, or an HPC workload.

The ratio compares two implementations of the same fixed-size operation;
it must not be interpreted as an asymptotic complexity result.

Alternating measurement order reduces systematic order bias but does not
eliminate virtual-machine contention, CPU-frequency variation, or other
environmental noise.

The measurements are machine- and environment-dependent.
They are evidence for this execution only, not a universal performance guarantee.
"""

    MD_PATH.write_text(
        content,
        encoding="utf-8",
    )


def run(warmups: int, repetitions: int) -> dict:
    if warmups < 0:
        raise ValueError("warmups must be non-negative")

    if repetitions < 2:
        raise ValueError("repetitions must be at least 2")

    BENCHMARK_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = utc_now()
    environment = write_environment()

    # Verify numerical equivalence before timing either implementation.
    equivalence = verify_equivalence()

    (
        rows,
        production_samples,
        independent_samples,
        paired_differences_ms,
    ) = measure_interleaved(
        production_operator,
        independent_operator,
        warmups,
        repetitions,
        timestamp,
    )

    production_summary = summarize(production_samples)
    independent_summary = summarize(independent_samples)

    production_median = production_summary["median_ms"]
    independent_median = independent_summary["median_ms"]

    if production_median <= 0.0:
        raise ArithmeticError(
            "Production median time is not positive"
        )

    if independent_median <= 0.0:
        raise ArithmeticError(
            "Independent median time is not positive"
        )

    median_difference_ms = (
        independent_median - production_median
    )

    speedup = independent_median / production_median

    production_median_reduction_percent = (
        median_difference_ms / independent_median * 100.0
    )

    paired_median_difference_ms = statistics.median(
        paired_differences_ms
    )

    production_pair_win_rate_percent = (
        sum(value > 0.0 for value in paired_differences_ms)
        / len(paired_differences_ms)
        * 100.0
    )

    comparison = {
        "metric": (
            "independent_median_ms / production_median_ms"
        ),
        "speedup_independent_over_production": speedup,
        "median_difference_ms": median_difference_ms,
        "production_median_reduction_percent": (
            production_median_reduction_percent
        ),
        "paired_median_difference_ms": (
            paired_median_difference_ms
        ),
        "production_pair_win_rate_percent": (
            production_pair_win_rate_percent
        ),
        "paired_sample_count": len(paired_differences_ms),
        "paired_difference_definition": (
            "independent_elapsed_ms - production_elapsed_ms; "
            "positive means production was faster"
        ),
        "interpretation": (
            "A value greater than 1 for the median ratio means "
            "the independent reference had a greater median "
            "execution time than production."
        ),
    }

    write_csv(rows)

    report = {
        "schema_version": 1,
        "benchmark_id": "P1-CANONICAL-4Q-OPERATOR-CONSTRUCTION",
        "status": "PASS",
        "timestamp_utc": timestamp,

        "workload": {
            "qubit_count": QUANTUM_REGISTER_SIZE,
            "hilbert_dimension": HILBERT_DIMENSION,
            "memberships": list(CANONICAL_MEMBERSHIPS),
            "operation": "global_operator_construction",
            "output_shape": [
                HILBERT_DIMENSION,
                HILBERT_DIMENSION,
            ],
            "numeric_dtype": "complex128",
        },

        "configuration": {
            "warmups": warmups,
            "repetitions": repetitions,
            "timer": "time.perf_counter_ns",
            "measurement_order": (
                "balanced_alternating_paired_measurements"
            ),
        },

        "equivalence_check": equivalence,

        "results": {
            "production": production_summary,
            "independent": independent_summary,
        },

        "comparison": comparison,

        "raw_samples": {
            "file": "benchmark_results.csv",
            "row_count": len(rows),
            "measurement_design": (
                "paired_alternating_order"
            ),
        },

        "environment": environment,

        "limitations": [
            "Only the canonical four-qubit P1 instance is measured.",
            "The result does not establish asymptotic scalability.",
            "The result does not establish million-qubit or HPC performance.",
            "Alternating order does not eliminate virtual-machine noise.",
            "Timings depend on the execution machine and environment.",
        ],
    }

    write_json(report)
    write_markdown(report)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the P1 canonical four-qubit benchmark."
    )

    parser.add_argument(
        "--warmups",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--repetitions",
        type=int,
        default=30,
    )

    args = parser.parse_args()

    try:
        report = run(
            args.warmups,
            args.repetitions,
        )

    except Exception as exc:
        failure = {
            "schema_version": 1,
            "benchmark_id": "P1-CANONICAL-4Q-OPERATOR-CONSTRUCTION",
            "status": "FAIL",
            "timestamp_utc": utc_now(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

        BENCHMARK_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        write_json(failure)
        write_markdown(failure)

        print(
            json.dumps(failure, indent=2),
            file=sys.stderr,
        )

        return 1

    print(json.dumps({
        "status": report["status"],
        "benchmark_id": report["benchmark_id"],
        "production_median_ms": (
            report["results"]["production"]["median_ms"]
        ),
        "independent_median_ms": (
            report["results"]["independent"]["median_ms"]
        ),
        "speedup_independent_over_production": (
            report["comparison"][
                "speedup_independent_over_production"
            ]
        ),
        "median_difference_ms": (
            report["comparison"]["median_difference_ms"]
        ),
        "production_median_reduction_percent": (
            report["comparison"][
                "production_median_reduction_percent"
            ]
        ),
        "paired_median_difference_ms": (
            report["comparison"][
                "paired_median_difference_ms"
            ]
        ),
        "production_pair_win_rate_percent": (
            report["comparison"][
                "production_pair_win_rate_percent"
            ]
        ),
        "files": [
            str(CSV_PATH.relative_to(ROOT)),
            str(JSON_PATH.relative_to(ROOT)),
            str(ENV_PATH.relative_to(ROOT)),
            str(MD_PATH.relative_to(ROOT)),
        ],
    }, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
