import csv
import math
import time
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix


DIMENSIONS = [1024, 10_000, 100_000]
MU = 0.70
WARMUP = 20
REPETITIONS = 1000
TARGET_MS = 15.0

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def build_qflpn_operator(n, mu):
    theta = 2.0 * math.asin(math.sqrt(mu))
    c = math.cos(theta)
    s = math.sin(theta)

    rows = []
    cols = []
    data = []

    for k in range(0, n, 2):
        i = k
        j = k + 1

        rows.extend([i, i, j, j])
        cols.extend([i, j, i, j])
        data.extend([c, -s, s, c])

    return csr_matrix(
        (data, (rows, cols)),
        shape=(n, n),
        dtype=np.float64
    )


def build_deterministic_state(n):
    idx = np.arange(n, dtype=np.float64)

    x = (
        np.sin(idx)
        + 0.5 * np.cos(0.37 * idx)
    )

    norm = np.linalg.norm(x)

    if norm == 0.0:
        raise RuntimeError("Starea inițială are norma zero.")

    return x / norm


def analytical_reference(x, mu):
    theta = 2.0 * math.asin(math.sqrt(mu))
    c = math.cos(theta)
    s = math.sin(theta)

    y = np.empty_like(x)

    y[0::2] = (
        c * x[0::2]
        - s * x[1::2]
    )

    y[1::2] = (
        s * x[0::2]
        + c * x[1::2]
    )

    return y


def benchmark(A, x):
    for _ in range(WARMUP):
        A @ x

    measurements = []

    for _ in range(REPETITIONS):
        t0 = time.perf_counter_ns()
        A @ x
        t1 = time.perf_counter_ns()

        measurements.append(
            (t1 - t0) / 1_000_000.0
        )

    return np.asarray(measurements)


def run_dimension(n):
    construction_start = time.perf_counter()

    A = build_qflpn_operator(n, MU)

    construction_ms = (
        time.perf_counter() - construction_start
    ) * 1000.0

    x = build_deterministic_state(n)

    y_reference = analytical_reference(x, MU)

    y_sparse = A @ x

    max_error = float(
        np.max(np.abs(y_sparse - y_reference))
    )

    norm_input = float(np.linalg.norm(x))
    norm_output = float(np.linalg.norm(y_sparse))

    norm_error = abs(
        norm_output - norm_input
    )

    measurements = benchmark(A, x)

    result = {
        "dimension": n,
        "nnz": int(A.nnz),
        "density_percent": float(
            100.0 * A.nnz / (n * n)
        ),
        "construction_ms": construction_ms,
        "mean_ms": float(np.mean(measurements)),
        "median_ms": float(np.median(measurements)),
        "min_ms": float(np.min(measurements)),
        "max_ms": float(np.max(measurements)),
        "max_absolute_error": max_error,
        "norm_error": norm_error,
        "target_ms": TARGET_MS,
        "status": "PASS"
        if max_error <= 1e-12 and norm_error <= 1e-12
        else "FAIL",
        "timing_status": "PASS"
        if np.mean(measurements) <= TARGET_MS
        else "FAIL"
    }

    return result


def main():
    output_file = RESULTS / "qflpn_operator_validation_python.csv"

    results = []

    for n in DIMENSIONS:
        print(f"Running N={n:,}")
        result = run_dimension(n)
        results.append(result)

        print(
            f"  mean = {result['mean_ms']:.6f} ms"
        )
        print(
            f"  max error = "
            f"{result['max_absolute_error']:.3e}"
        )
        print(
            f"  norm error = "
            f"{result['norm_error']:.3e}"
        )

    fieldnames = list(results[0].keys())

    with output_file.open(
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
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()
