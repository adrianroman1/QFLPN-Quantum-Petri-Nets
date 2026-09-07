#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.sparse import csr_matrix


# ============================================================
# QFLPN SCALING BENCHMARK
# ============================================================
#
# Deterministic sparse QFLPN operator benchmark.
#
# Qubit range:
#     q = 4, ..., 17
#
# State dimensions:
#     N = 2^q
#
# Operator:
#     identical 2x2 unitary rotation blocks
#
# Benchmark:
#     CSR sparse matrix-vector multiplication
#
# Numerical validation:
#     independent analytical application of the same operator
#
# Precision:
#     float64
#
# Timing:
#     20 warmup repetitions
#     1000 measured repetitions
#
# Output:
#     python/results/qflpn_scaling_python.csv
#
# ============================================================


# -----------------------------
# Configuration
# -----------------------------

MIN_QUBITS = 4
MAX_QUBITS = 17

WARMUP = 20
REPETITIONS = 1000

TARGET_MS = 15.0

# Fuzzy membership used by the declared
# fuzzy-to-quantum angle convention.
MU = 0.70

OUTPUT_DIR = Path(__file__).resolve().parent / "results"
OUTPUT_FILE = OUTPUT_DIR / "qflpn_scaling_python.csv"


# -----------------------------
# QFLPN operator definition
# -----------------------------

def qflpn_rotation_parameters(mu: float) -> tuple[float, float, float]:
    """
    Convert fuzzy membership mu to the rotation angle and
    corresponding cosine/sine values.

    theta(mu) = 2 * asin(sqrt(mu))
    """
    if not (0.0 <= mu <= 1.0):
        raise ValueError("mu must satisfy 0 <= mu <= 1.")

    theta = 2.0 * math.asin(math.sqrt(mu))
    c = math.cos(theta)
    s = math.sin(theta)

    return theta, c, s


def build_qflpn_csr(n: int, c: float, s: float) -> csr_matrix:
    """
    Construct the deterministic sparse QFLPN transition operator.

    Each pair of basis states receives the unitary block

        [ c  -s ]
        [ s   c ]

    Therefore every row has exactly two non-zero elements.
    """
    if n <= 0:
        raise ValueError("State dimension must be positive.")

    if n % 2 != 0:
        raise ValueError("State dimension must be even.")

    rows = np.repeat(np.arange(n, dtype=np.int32), 2)

    cols = np.empty(2 * n, dtype=np.int32)
    data = np.empty(2 * n, dtype=np.float64)

    for k in range(0, n, 2):
        p = 2 * k

        cols[p] = k
        data[p] = c

        cols[p + 1] = k + 1
        data[p + 1] = -s

        cols[p + 2] = k
        data[p + 2] = s

        cols[p + 3] = k + 1
        data[p + 3] = c

    # The construction above uses four values per pair.
    # Rebuild explicitly to guarantee the correct CSR layout.
    row_index = np.arange(n, dtype=np.int32)

    row_list = np.empty(2 * n, dtype=np.int32)
    col_list = np.empty(2 * n, dtype=np.int32)
    value_list = np.empty(2 * n, dtype=np.float64)

    pos = 0

    for k in range(0, n, 2):
        row_list[pos] = k
        col_list[pos] = k
        value_list[pos] = c
        pos += 1

        row_list[pos] = k
        col_list[pos] = k + 1
        value_list[pos] = -s
        pos += 1

        row_list[pos] = k + 1
        col_list[pos] = k
        value_list[pos] = s
        pos += 1

        row_list[pos] = k + 1
        col_list[pos] = k + 1
        value_list[pos] = c
        pos += 1

    matrix = csr_matrix(
        (value_list, (row_list, col_list)),
        shape=(n, n),
        dtype=np.float64,
    )

    matrix.sum_duplicates()
    matrix.eliminate_zeros()

    return matrix


# -----------------------------
# Deterministic input state
# -----------------------------

def deterministic_state(n: int) -> np.ndarray:
    """
    Generate a deterministic normalized state vector.

    No random generator is used.
    """
    i = np.arange(n, dtype=np.float64)

    x = np.sin(i) + 0.5 * np.cos(0.37 * i)

    norm = np.linalg.norm(x)

    if norm == 0.0:
        raise ValueError("Input state has zero norm.")

    return x / norm


# -----------------------------
# Independent analytical action
# -----------------------------

def analytical_qflpn_action(
    x: np.ndarray,
    c: float,
    s: float,
) -> np.ndarray:
    """
    Apply the same QFLPN operator directly from its analytical
    2x2 block definition.

    This is independent of scipy.sparse CSR multiplication.
    """
    n = x.size

    y = np.empty_like(x)

    even = np.arange(0, n, 2)
    odd = even + 1

    x_even = x[even]
    x_odd = x[odd]

    y[even] = c * x_even - s * x_odd
    y[odd] = s * x_even + c * x_odd

    return y


# -----------------------------
# Validation
# -----------------------------

def validate_operator(
    matrix: csr_matrix,
    x: np.ndarray,
    reference: np.ndarray,
) -> tuple[float, float]:
    """
    Validate sparse operator action against the analytical result.

    Returns:
        maximum absolute error
        norm preservation error
    """
    result = matrix @ x

    maximum_error = float(
        np.max(np.abs(result - reference))
    )

    input_norm = float(np.linalg.norm(x))
    output_norm = float(np.linalg.norm(result))

    norm_error = abs(output_norm - input_norm)

    return maximum_error, norm_error


# -----------------------------
# Timing
# -----------------------------

def benchmark_spmv(
    matrix: csr_matrix,
    x: np.ndarray,
) -> np.ndarray:
    """
    Measure only the repeated CSR SpMV operation.
    """
    for _ in range(WARMUP):
        matrix @ x

    timings_ms = np.empty(REPETITIONS, dtype=np.float64)

    for repetition in range(REPETITIONS):
        start = time.perf_counter_ns()
        matrix @ x
        end = time.perf_counter_ns()

        timings_ms[repetition] = (end - start) / 1_000_000.0

    return timings_ms


# -----------------------------
# Main benchmark
# -----------------------------

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    theta, c, s = qflpn_rotation_parameters(MU)

    print("=" * 72)
    print("QFLPN SCALING BENCHMARK — PYTHON")
    print("=" * 72)
    print(f"Qubit range       : {MIN_QUBITS} ... {MAX_QUBITS}")
    print(f"Warmup repetitions: {WARMUP}")
    print(f"Measured repetitions: {REPETITIONS}")
    print(f"Fuzzy membership  : {MU:.12f}")
    print(f"Rotation angle    : {theta:.12f} rad")
    print(f"Target time       : {TARGET_MS:.6f} ms")
    print(f"Python            : {sys.version.split()[0]}")
    print(f"NumPy             : {np.__version__}")
    print(f"SciPy             : {scipy.__version__}")
    print(f"Platform          : {platform.platform()}")
    print("=" * 72)

    fieldnames = [
        "language",
        "qubits",
        "states",
        "nnz",
        "repetitions",
        "warmup",
        "mean_spmv_ms",
        "median_spmv_ms",
        "min_spmv_ms",
        "max_spmv_ms",
        "maximum_error",
        "norm_error",
        "target_ms",
        "numerical_status",
        "timing_status",
    ]

    rows = []

    for qubits in range(MIN_QUBITS, MAX_QUBITS + 1):
        states = 2 ** qubits

        print(
            f"\nq={qubits:2d} | "
            f"N={states:7d} | "
            f"constructing CSR operator..."
        )

        matrix = build_qflpn_csr(states, c, s)
        x = deterministic_state(states)

        reference = analytical_qflpn_action(
            x,
            c,
            s,
        )

        maximum_error, norm_error = validate_operator(
            matrix,
            x,
            reference,
        )

        timings = benchmark_spmv(matrix, x)

        mean_ms = float(np.mean(timings))
        median_ms = float(np.median(timings))
        min_ms = float(np.min(timings))
        max_ms = float(np.max(timings))

        numerical_status = (
            "PASS"
            if maximum_error <= 1e-12
            and norm_error <= 1e-12
            else "FAIL"
        )

        timing_status = (
            "PASS"
            if mean_ms <= TARGET_MS
            else "FAIL"
        )

        row = {
            "language": "Python",
            "qubits": qubits,
            "states": states,
            "nnz": int(matrix.nnz),
            "repetitions": REPETITIONS,
            "warmup": WARMUP,
            "mean_spmv_ms": f"{mean_ms:.12f}",
            "median_spmv_ms": f"{median_ms:.12f}",
            "min_spmv_ms": f"{min_ms:.12f}",
            "max_spmv_ms": f"{max_ms:.12f}",
            "maximum_error": f"{maximum_error:.16e}",
            "norm_error": f"{norm_error:.16e}",
            "target_ms": f"{TARGET_MS:.6f}",
            "numerical_status": numerical_status,
            "timing_status": timing_status,
        }

        rows.append(row)

        print(
            f"       nnz={matrix.nnz:7d} | "
            f"mean={mean_ms:.6f} ms | "
            f"median={median_ms:.6f} ms | "
            f"max_error={maximum_error:.3e} | "
            f"norm_error={norm_error:.3e} | "
            f"{numerical_status}/{timing_status}"
        )

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 72)
    print("RESULTS WRITTEN")
    print("=" * 72)
    print(OUTPUT_FILE)
    print("=" * 72)


if __name__ == "__main__":
    main()