"""Reproducible P1 benchmark for the canonical four-qubit QFLPN instance.

Compares:
  1. Production global-operator construction.
  2. Independent scalar-loop reference construction.

The benchmark does not claim scalability beyond the canonical q=4, D=16 case.
All timings are measured locally with time.perf_counter_ns().
"""
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
    """Return CPU model where exposed by the operating system."""
    candidates = [
        Path("/proc/cpuinfo"),
        Path("/proc/device-tree/model"),
    ]
    for path in candidates:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
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
    """Return physical memory when the platform exposes it."""
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        value = int(pages) * int(page_size)
        return value if value > 0 else None
    except (AttributeError, OSError, ValueError):
        return None


def write_environment() -> dict:
    memory = memory_bytes()
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
        "physical_memory_bytes": memory,
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
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
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
    """Verify both implementations before collecting timing samples."""
    production = production_operator()
    independent = independent_operator()

    if production.shape != (HILBERT_DIMENSION, HILBERT_DIMENSION):
        raise AssertionError(
            f"Production shape mismatch: {production.shape}"
        )

    if independent.shape != production.shape:
        raise AssertionError(
            f"Independent shape mismatch: {independent.shape}"
        )

    if not np.isfinite(production).all():
        raise AssertionError("Production operator contains non-finite values")

    if not np.isfinite(independent).all():
        raise AssertionError("Independent operator contains non-finite values")

    difference = float(np.linalg.norm(production - independent, ord="fro"))

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


def measure(
    function: Callable[[], np.ndarray],
    implementation: str,
    warmups: int,
    repetitions: int,
    timestamp: str,
) -> tuple[list[dict], list[int]]:
    """Run warmups and collect individual elapsed-time samples."""
    for _ in range(warmups):
        function()

    rows: list[dict] = []
    samples: list[int] = []

    for iteration in range(1, repetitions + 1):
        start = time.perf_counter_ns()
        result = function()
        elapsed_ns = time.perf_counter_ns() - start

        if not isinstance(result, np.ndarray):
            raise TypeError(
                f"{implementation} returned {type(result).__name__}, "
                "expected numpy.ndarray"
            )

        if not np.isfinite(result).all():
            raise ArithmeticError(
                f"{implementation} produced non-finite output"
            )

        samples.append(int(elapsed_ns))
        rows.append({
            "timestamp_utc": timestamp,
            "operation": "global_operator_construction",
            "implementation": implementation,
            "iteration": iteration,
            "elapsed_ns": int(elapsed_ns),
            "elapsed_ms": elapsed_ns / 1_000_000.0,
            "qubit_count": QUANTUM_REGISTER_SIZE,
            "hilbert_dimension": HILBERT_DIMENSION,
        })

    return rows, samples


def summarize(samples: list[int]) -> dict:
    if not samples:
        raise ValueError("Cannot summarize an empty sample set")

    values_ms = [value / 1_000_000.0 for value in samples]

    return {
        "sample_count": len(samples),
        "minimum_ms": min(values_ms),
        "maximum_ms": max(values_ms),
        "mean_ms": statistics.mean(values_ms),
        "median_ms": statistics.median(values_ms),
        "standard_deviation_ms": (
            statistics.stdev(values_ms) if len(values_ms) > 1 else 0.0
        ),
    }


def write_csv(rows: list[dict]) -> None:
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
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
        speedup = report["comparison"]["speedup_independent_over_production"]

        content = f"""# P1 Benchmark Results

## Scope

- Canonical register: **q = {report['workload']['qubit_count']} qubits**
- Hilbert-space dimension: **D = {report['workload']['hilbert_dimension']}**
- Operation: global QFLPN transition-operator construction
- Samples per implementation: **{report['configuration']['repetitions']}**
- Warm-up iterations: **{report['configuration']['warmups']}**
- Timer: `time.perf_counter_ns()`
- Numerical equivalence: **{report['equivalence_check']['status']}**
- Frobenius difference: `{report['equivalence_check']['frobenius_difference']:.6e}`
- Tolerance: `{report['equivalence_check']['tolerance']:.1e}`

## Measured execution times

| Metric | Production implementation | Independent implementation |
|---|---:|---:|
| Minimum (ms) | {production['minimum_ms']:.6f} | {independent['minimum_ms']:.6f} |
| Median (ms) | {production['median_ms']:.6f} | {independent['median_ms']:.6f} |
| Mean (ms) | {production['mean_ms']:.6f} | {independent['mean_ms']:.6f} |
| Maximum (ms) | {production['maximum_ms']:.6f} | {independent['maximum_ms']:.6f} |
| Standard deviation (ms) | {production['standard_deviation_ms']:.6f} | {independent['standard_deviation_ms']:.6f} |
| Samples | {production['sample_count']} | {independent['sample_count']} |

## Relative execution time

- Independent / production median-time ratio: **{speedup:.6f}×**
- Interpretation: values above 1 indicate that the production implementation
  had a lower median time in this measured run. Values below 1 indicate the
  opposite.

## Reproducibility

- Timestamp (UTC): `{report['timestamp_utc']}`
- Git commit: `{report['environment']['git_commit']}`
- Python: `{report['environment']['python_version']}`
- NumPy: `{report['environment']['numpy_version']}`
- SciPy: `{report['environment']['scipy_version']}`
- Platform: `{report['environment']['operating_system']}`
- CPU: `{report['environment']['cpu_model']}`

Raw samples are stored in `benchmark_results.csv`.
Structured results are stored in `benchmark_report.json`.
The captured environment is stored in `environment.txt`.

## Interpretation and limitations

This benchmark measures construction of the **canonical four-qubit P1
operator only**. It is not a benchmark of a scalable quantum simulator,
a million-qubit system, a distributed implementation, or an HPC workload.
The ratio compares two implementations of the same fixed-size operation;
it must not be interpreted as an asymptotic complexity result.

The measurements are machine- and environment-dependent. They are evidence
for this execution only, not a universal performance guarantee.
"""
    MD_PATH.write_text(content, encoding="utf-8")


def run(warmups: int, repetitions: int) -> dict:
    if warmups < 0:
        raise ValueError("warmups must be non-negative")
    if repetitions < 2:
        raise ValueError("repetitions must be at least 2")

    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = utc_now()
    environment = write_environment()
    equivalence = verify_equivalence()

    production_rows, production_samples = measure(
        production_operator,
        "production",
        warmups,
        repetitions,
        timestamp,
    )

    independent_rows, independent_samples = measure(
        independent_operator,
        "independent",
        warmups,
        repetitions,
        timestamp,
    )

    production_summary = summarize(production_samples)
    independent_summary = summarize(independent_samples)

    production_median = production_summary["median_ms"]
    independent_median = independent_summary["median_ms"]

    if production_median <= 0.0:
        raise ArithmeticError("Production median time is not positive")

    speedup = independent_median / production_median

    rows = production_rows + independent_rows
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
            "output_shape": [HILBERT_DIMENSION, HILBERT_DIMENSION],
            "numeric_dtype": "complex128",
        },
        "configuration": {
            "warmups": warmups,
            "repetitions": repetitions,
            "timer": "time.perf_counter_ns",
        },
        "equivalence_check": equivalence,
        "results": {
            "production": production_summary,
            "independent": independent_summary,
        },
        "comparison": {
            "metric": "independent_median_ms / production_median_ms",
            "speedup_independent_over_production": speedup,
            "interpretation": (
                "A value greater than 1 means the production implementation "
                "had a lower median execution time in this run."
            ),
        },
        "raw_samples": {
            "file": "benchmark_results.csv",
            "row_count": len(rows),
        },
        "environment": environment,
        "limitations": [
            "Only the canonical four-qubit P1 instance is measured.",
            "The result does not establish asymptotic scalability.",
            "The result does not establish million-qubit or HPC performance.",
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
        help="Warm-up calls per implementation (default: 5).",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=30,
        help="Measured calls per implementation (default: 30).",
    )
    args = parser.parse_args()

    try:
        report = run(args.warmups, args.repetitions)
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "benchmark_id": "P1-CANONICAL-4Q-OPERATOR-CONSTRUCTION",
            "status": "FAIL",
            "timestamp_utc": utc_now(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
        write_json(failure)
        write_markdown(failure)
        print(json.dumps(failure, indent=2), file=sys.stderr)
        return 1

    print(json.dumps({
        "status": report["status"],
        "benchmark_id": report["benchmark_id"],
        "production_median_ms": report["results"]["production"]["median_ms"],
        "independent_median_ms": report["results"]["independent"]["median_ms"],
        "speedup_independent_over_production": (
            report["comparison"]["speedup_independent_over_production"]
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
