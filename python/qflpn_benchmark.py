"""
QFLPN Benchmark
===============

Deterministic benchmark for the 4-qubit QFLPN model.

Outputs:
    qflpn_python_results.csv

Measures:
    - state construction time
    - total execution time
    - normalization error
    - probability error
    - fidelity error

No Monte Carlo.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

import numpy as np

from qflpn_reference import (
    density_matrix,
    pure_state_fidelity,
    reference_state,
)


MEMBERSHIPS = (
    0.85,
    0.90,
    0.45,
    0.70,
)

QUBITS = 4
STATES = 2 ** QUBITS
REPETITIONS = 1000
TARGET_MS = 15.0

OUTPUT_FILE = Path("qflpn_python_results.csv")


def benchmark() -> dict[str, float]:

    # Warm-up
    for _ in range(20):
        state = reference_state(MEMBERSHIPS)
        density_matrix(state)

    state_times = []
    total_times = []

    last_state = None
    last_rho = None

    for _ in range(REPETITIONS):

        start_total = time.perf_counter_ns()

        start_state = time.perf_counter_ns()
        state = reference_state(MEMBERSHIPS)
        end_state = time.perf_counter_ns()

        rho = density_matrix(state)

        end_total = time.perf_counter_ns()

        state_times.append(
            (end_state - start_state) / 1_000_000.0
        )

        total_times.append(
            (end_total - start_total) / 1_000_000.0
        )

        last_state = state
        last_rho = rho

    state_times = np.asarray(state_times)
    total_times = np.asarray(total_times)

    normalization_error = abs(
        np.linalg.norm(last_state) - 1.0
    )

    probability_error = abs(
        np.sum(np.abs(last_state) ** 2) - 1.0
    )

    fidelity_error = abs(
        pure_state_fidelity(last_state, last_state) - 1.0
    )

    hermiticity_error = np.linalg.norm(
        last_rho - last_rho.conj().T,
        ord="fro",
    )

    maximum_error = max(
        normalization_error,
        probability_error,
        fidelity_error,
        hermiticity_error,
    )

    return {
        "qubits": QUBITS,
        "states": STATES,
        "repetitions": REPETITIONS,
        "mean_state_ms": float(np.mean(state_times)),
        "median_state_ms": float(np.median(state_times)),
        "min_state_ms": float(np.min(state_times)),
        "max_state_ms": float(np.max(state_times)),
        "mean_total_ms": float(np.mean(total_times)),
        "median_total_ms": float(np.median(total_times)),
        "min_total_ms": float(np.min(total_times)),
        "max_total_ms": float(np.max(total_times)),
        "target_ms": TARGET_MS,
        "maximum_error": float(maximum_error),
    }


def main() -> None:

    print("=" * 64)
    print("QFLPN PYTHON BENCHMARK")
    print("=" * 64)

    results = benchmark()

    print(f"\nQubits              : {results['qubits']}")
    print(f"States              : {results['states']}")
    print(f"Repetitions         : {results['repetitions']}")

    print("\nState construction:")
    print(f"  mean              : {results['mean_state_ms']:.6f} ms")
    print(f"  median            : {results['median_state_ms']:.6f} ms")
    print(f"  min               : {results['min_state_ms']:.6f} ms")
    print(f"  max               : {results['max_state_ms']:.6f} ms")

    print("\nTotal execution:")
    print(f"  mean              : {results['mean_total_ms']:.6f} ms")
    print(f"  median            : {results['median_total_ms']:.6f} ms")
    print(f"  min               : {results['min_total_ms']:.6f} ms")
    print(f"  max               : {results['max_total_ms']:.6f} ms")

    print("\nNumerical validation:")
    print(
        f"  maximum error     : "
        f"{results['maximum_error']:.3e}"
    )

    print("\n15 ms target:")

    if results["mean_total_ms"] <= TARGET_MS:
        status = "PASS"
        print("  STATUS            : PASS")
    else:
        status = "TARGET NOT MET"
        print("  STATUS            : TARGET NOT MET")

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "language",
            "qubits",
            "states",
            "repetitions",
            "mean_state_ms",
            "median_state_ms",
            "min_state_ms",
            "max_state_ms",
            "mean_total_ms",
            "median_total_ms",
            "min_total_ms",
            "max_total_ms",
            "target_ms",
            "maximum_error",
            "status",
        ])

        writer.writerow([
            "Python",
            results["qubits"],
            results["states"],
            results["repetitions"],
            results["mean_state_ms"],
            results["median_state_ms"],
            results["min_state_ms"],
            results["max_state_ms"],
            results["mean_total_ms"],
            results["median_total_ms"],
            results["min_total_ms"],
            results["max_total_ms"],
            results["target_ms"],
            results["maximum_error"],
            status,
        ])

    print(f"\nCSV exported: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
