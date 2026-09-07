#!/usr/bin/env python3

import csv
import math
import os
import time

import numpy as np
from scipy.linalg import expm
from scipy.sparse import csr_matrix


Q_MIN = 4
Q_MAX = 17

WARMUP = 20
REPETITIONS = 1000

FUZZY_MEMBERSHIP = 0.70
TIME_STEP = 1.0
KRYLOV_DIMENSION = 20

TARGET_MS = 15.0

OUTPUT_DIR = os.path.join("python", "results")
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "qflpn_krylov_arnoldi_python.csv",
)


def build_qflpn_operator(n: int, mu: float) -> csr_matrix:
    """
    Build the deterministic sparse QFLPN rotation operator.

    The operator is block diagonal with identical 2x2 orthogonal
    rotation blocks derived from the fuzzy membership value.
    """

    if n < 2 or n % 2 != 0:
        raise ValueError("The state dimension must be an even positive integer.")

    theta = 2.0 * math.asin(math.sqrt(mu))
    c = math.cos(theta)
    s = math.sin(theta)

    indices = np.arange(0, n, 2, dtype=np.int64)

    rows = np.empty(2 * n, dtype=np.int64)
    cols = np.empty(2 * n, dtype=np.int64)
    values = np.empty(2 * n, dtype=np.float64)

    rows[0::4] = indices
    cols[0::4] = indices
    values[0::4] = c

    rows[1::4] = indices
    cols[1::4] = indices + 1
    values[1::4] = -s

    rows[2::4] = indices + 1
    cols[2::4] = indices
    values[2::4] = s

    rows[3::4] = indices + 1
    cols[3::4] = indices + 1
    values[3::4] = c

    return csr_matrix((values, (rows, cols)), shape=(n, n))


def build_initial_state(n: int) -> np.ndarray:
    """
    Deterministic normalized initial state.
    """

    x = np.arange(1, n + 1, dtype=np.float64)

    norm = np.linalg.norm(x)

    if norm == 0.0:
        raise ValueError("Initial state has zero norm.")

    return x / norm


def analytical_exponential_action(
    x: np.ndarray,
    mu: float,
    time_step: float,
) -> np.ndarray:
    """
    Independent analytical reference for exp(t*A)x.

    For every 2x2 block

        A_k = [[c, -s],
               [s,  c]]

    the exponential is

        exp(t*A_k)
          = exp(t*c) [[cos(t*s), -sin(t*s)],
                      [sin(t*s),  cos(t*s)]]
    """

    theta = 2.0 * math.asin(math.sqrt(mu))
    c = math.cos(theta)
    s = math.sin(theta)

    alpha = math.exp(time_step * c)
    phi = time_step * s

    cp = math.cos(phi)
    sp = math.sin(phi)

    y = np.empty_like(x)

    even = x[0::2]
    odd = x[1::2]

    y[0::2] = alpha * (cp * even - sp * odd)
    y[1::2] = alpha * (sp * even + cp * odd)

    return y


def arnoldi_exponential_action(
    a: csr_matrix,
    x: np.ndarray,
    time_step: float,
    krylov_dimension: int,
) -> tuple[np.ndarray, int]:
    """
    Compute an Arnoldi/Krylov approximation of exp(t*A)x.

    Modified Gram-Schmidt with a second reorthogonalization pass
    is used for numerical stability.
    """

    n = x.size

    beta = np.linalg.norm(x)

    if beta == 0.0:
        return np.zeros_like(x), 0

    m = min(krylov_dimension, n)

    v = np.zeros((n, m), dtype=np.float64)
    h = np.zeros((m, m), dtype=np.float64)

    v[:, 0] = x / beta

    effective_dimension = 1

    for j in range(m):
        w = a @ v[:, j]

        for i in range(j + 1):
            hij = np.dot(v[:, i], w)
            h[i, j] += hij
            w -= hij * v[:, i]

        # Second orthogonalization pass.
        for i in range(j + 1):
            hij = np.dot(v[:, i], w)
            h[i, j] += hij
            w -= hij * v[:, i]

        if j + 1 >= m:
            effective_dimension = m
            break

        hnext = np.linalg.norm(w)

        if hnext <= np.finfo(np.float64).eps * max(1.0, np.linalg.norm(h)):
            effective_dimension = j + 1
            break

        h[j + 1, j] = hnext
        v[:, j + 1] = w / hnext
        effective_dimension = j + 2

    h_eff = h[:effective_dimension, :effective_dimension]
    v_eff = v[:, :effective_dimension]

    exp_h = expm(time_step * h_eff)

    e1 = np.zeros(effective_dimension, dtype=np.float64)
    e1[0] = beta

    y = v_eff @ (exp_h @ e1)

    return y, effective_dimension


def measure_once(
    a: csr_matrix,
    x: np.ndarray,
    time_step: float,
) -> tuple[float, float, int, float]:
    """
    One timed Arnoldi execution.

    Returns:
        elapsed_ms,
        maximum_absolute_error,
        effective_krylov_dimension,
        norm_error.
    """

    start = time.perf_counter()

    y, effective_dimension = arnoldi_exponential_action(
        a,
        x,
        time_step,
        KRYLOV_DIMENSION,
    )

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    reference = analytical_exponential_action(
        x,
        FUZZY_MEMBERSHIP,
        time_step,
    )

    maximum_absolute_error = float(
        np.max(np.abs(y - reference))
    )

    norm_error = float(
        abs(np.linalg.norm(y) - np.linalg.norm(reference))
    )

    return (
        elapsed_ms,
        maximum_absolute_error,
        effective_dimension,
        norm_error,
    )


def run_benchmark(
    q: int,
) -> dict:
    n = 2 ** q

    a = build_qflpn_operator(
        n,
        FUZZY_MEMBERSHIP,
    )

    x = build_initial_state(n)

    # Warm-up.
    for _ in range(WARMUP):
        arnoldi_exponential_action(
            a,
            x,
            TIME_STEP,
            KRYLOV_DIMENSION,
        )

    elapsed_values = []
    error_values = []
    dimension_values = []
    norm_error_values = []

    for _ in range(REPETITIONS):
        (
            elapsed_ms,
            maximum_absolute_error,
            effective_dimension,
            norm_error,
        ) = measure_once(
            a,
            x,
            TIME_STEP,
        )

        elapsed_values.append(elapsed_ms)
        error_values.append(maximum_absolute_error)
        dimension_values.append(effective_dimension)
        norm_error_values.append(norm_error)

    elapsed = np.asarray(elapsed_values, dtype=np.float64)
    errors = np.asarray(error_values, dtype=np.float64)
    dimensions = np.asarray(dimension_values, dtype=np.float64)
    norm_errors = np.asarray(norm_error_values, dtype=np.float64)

    mean_ms = float(np.mean(elapsed))
    median_ms = float(np.median(elapsed))
    min_ms = float(np.min(elapsed))
    max_ms = float(np.max(elapsed))

    maximum_error = float(np.max(errors))
    maximum_norm_error = float(np.max(norm_errors))

    effective_dimension = int(round(float(np.median(dimensions))))

    status = (
        "PASS"
        if (
            maximum_error <= 1.0e-12
            and maximum_norm_error <= 1.0e-12
            and mean_ms <= TARGET_MS
        )
        else "FAIL"
    )

    return {
        "language": "Python",
        "qubits": q,
        "states": n,
        "repetitions": REPETITIONS,
        "warmup": WARMUP,
        "krylov_dimension": KRYLOV_DIMENSION,
        "effective_krylov_dimension": effective_dimension,
        "mean_arnoldi_ms": mean_ms,
        "median_arnoldi_ms": median_ms,
        "min_arnoldi_ms": min_ms,
        "max_arnoldi_ms": max_ms,
        "target_ms": TARGET_MS,
        "maximum_error": maximum_error,
        "maximum_norm_error": maximum_norm_error,
        "status": status,
    }


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fieldnames = [
        "language",
        "qubits",
        "states",
        "repetitions",
        "warmup",
        "krylov_dimension",
        "effective_krylov_dimension",
        "mean_arnoldi_ms",
        "median_arnoldi_ms",
        "min_arnoldi_ms",
        "max_arnoldi_ms",
        "target_ms",
        "maximum_error",
        "maximum_norm_error",
        "status",
    ]

    print("QFLPN KRYLOV-ARNOLDI BENCHMARK - PYTHON")
    print(f"Qubit range          : {Q_MIN} ... {Q_MAX}")
    print(f"Warmup repetitions   : {WARMUP}")
    print(f"Measured repetitions : {REPETITIONS}")
    print(f"Fuzzy membership     : {FUZZY_MEMBERSHIP:.12f}")
    print(f"Krylov dimension    : {KRYLOV_DIMENSION}")
    print(f"Target time         : {TARGET_MS:.6f} ms")
    print()

    rows = []

    for q in range(Q_MIN, Q_MAX + 1):
        row = run_benchmark(q)
        rows.append(row)

        print(
            f"q={q:2d}  "
            f"N={row['states']:6d}  "
            f"mean={row['mean_arnoldi_ms']:.6f} ms  "
            f"median={row['median_arnoldi_ms']:.6f} ms  "
            f"max={row['max_arnoldi_ms']:.6f} ms  "
            f"K={row['effective_krylov_dimension']:2d}  "
            f"error={row['maximum_error']:.3e}  "
            f"status={row['status']}"
        )

    with open(
        OUTPUT_FILE,
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

    print()
    print(f"CSV output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()