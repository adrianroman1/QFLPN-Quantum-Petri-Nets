import csv
import math
import time
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix


# ============================================================
# QFLPN SCALING BENCHMARK
# State-space dimensions:
#     1,024
#    10,000
#   100,000
#
# The benchmark measures deterministic sparse operator action.
# ============================================================

DIMENSIONS = [1024, 10000, 100000]

MU = 0.70

WARMUP = 20
REPETITIONS = 1000

TARGET_MS = 15.0

OUTPUT_FILE = Path("qflpn_scaling_python.csv")


def build_qflpn_operator(n, mu):
    """
    Construct a deterministic sparse QFLPN transition operator.

    The state space is divided into 2x2 rotation blocks:

        [ cos(theta)  -sin(theta) ]
        [ sin(theta)   cos(theta) ]

    where

        theta = 2 asin(sqrt(mu)).

    Each block is unitary/orthogonal in real arithmetic.
    """

    theta = 2.0 * math.asin(math.sqrt(mu))

    c = math.cos(theta)
    s = math.sin(theta)

    rows = np.repeat(np.arange(n), 2)
    cols = np.empty(2 * n, dtype=np.int64)
    data = np.empty(2 * n, dtype=np.float64)

    for k in range(0, n, 2):
        cols[2 * k] = k
        cols[2 * k + 1] = k + 1

        data[2 * k] = c
        data[2 * k + 1] = -s

        cols[2 * k + 2] = k
        cols[2 * k + 3] = k + 1

        data[2 * k + 2] = s
        data[2 * k + 3] = c

    return csr_matrix((data, (rows, cols)), shape=(n, n))


def build_deterministic_state(n):
    """
    Construct the same deterministic initial state for every run.
    No random numbers are used.
    """

    i = np.arange(n, dtype=np.float64)

    x = np.sin(i) + 0.5 * np.cos(0.37 * i)

    norm = np.linalg.norm(x)

    return x / norm


def analytical_reference(x, mu):
    """
    Independent analytical application of the same 2x2
    QFLPN transition blocks.

    This is used as the numerical reference and is deliberately
    computed independently from CSR SpMV.
    """

    theta = 2.0 * math.asin(math.sqrt(mu))

    c = math.cos(theta)
    s = math.sin(theta)

    y = np.empty_like(x)

    y[0::2] = c * x[0::2] - s * x[1::2]
    y[1::2] = s * x[0::2] + c * x[1::2]

    return y


def qubits_if_power_of_two(n):
    """
    Return the exact qubit count only when N is a power of two.
    Otherwise return an empty value.
    """

    q = int(round(math.log2(n)))

    if 2 ** q == n:
        return q

    return ""


def benchmark_dimension(n):
    print(f"Running N = {n:,}")

    construction_start = time.perf_counter_ns()

    operator = build_qflpn_operator(n, MU)
    x = build_deterministic_state(n)

    construction_end = time.perf_counter_ns()

    construction_ms = (
        construction_end - construction_start
    ) / 1_000_000.0

    reference = analytical_reference(x, MU)

    input_norm = np.linalg.norm(x)

    # Warm-up
    y = None

    for _ in range(WARMUP):
        y = operator @ x

    # Timed deterministic SpMV
    timings_ms = []

    for _ in range(REPETITIONS):
        start = time.perf_counter_ns()

        y = operator @ x

        end = time.perf_counter_ns()

        timings_ms.append(
            (end - start) / 1_000_000.0
        )

    timings_ms = np.asarray(timings_ms)

    output_norm = np.linalg.norm(y)

    maximum_error = np.max(
        np.abs(y - reference)
    )

    norm_error = abs(
        output_norm - input_norm
    )

    timing_status = (
        "PASS"
        if float(np.mean(timings_ms)) <= TARGET_MS
        else "FAIL"
    )

    numerical_status = (
        "PASS"
        if maximum_error <= 1e-12
        and norm_error <= 1e-12
        else "FAIL"
    )

    return {
        "language": "Python",
        "states": n,
        "qubits_if_power_of_two": qubits_if_power_of_two(n),
        "nnz": operator.nnz,
        "mu": MU,
        "warmup": WARMUP,
        "repetitions": REPETITIONS,
        "construction_ms": construction_ms,
        "mean_ms": float(np.mean(timings_ms)),
        "median_ms": float(np.median(timings_ms)),
        "min_ms": float(np.min(timings_ms)),
        "max_ms": float(np.max(timings_ms)),
        "maximum_error": float(maximum_error),
        "input_norm": float(input_norm),
        "output_norm": float(output_norm),
        "norm_error": float(norm_error),
        "target_ms": TARGET_MS,
        "numerical_status": numerical_status,
        "timing_status": timing_status,
    }


def main():

    results = []

    for n in DIMENSIONS:
        results.append(
            benchmark_dimension(n)
        )

    fieldnames = list(results[0].keys())

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    print()
    print("QFLPN scaling benchmark completed.")
    print(f"Results written to: {OUTPUT_FILE}")

    for result in results:
        print(
            f"N={result['states']:,} | "
            f"NNZ={result['nnz']:,} | "
            f"mean={result['mean_ms']:.6f} ms | "
            f"error={result['maximum_error']:.3e} | "
            f"{result['numerical_status']} / "
            f"{result['timing_status']}"
        )


if __name__ == "__main__":
    main()