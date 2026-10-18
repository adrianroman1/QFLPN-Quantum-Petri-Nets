"""CSR rotation-block consistency check, aligned with the P1 RY convention.

Scope note: P1's preprint explicitly assigns large-scale CSR/sparse evolution
experiments to P3. This retained script is therefore only a numerical helper;
its timings are not evidence for P1's scientific claims.
"""

from __future__ import annotations

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
TOLERANCE = 1e-12
ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def _validate_inputs(n: int, mu: float) -> None:
    if not isinstance(n, int) or n <= 0 or n % 2 != 0:
        raise ValueError("n must be a positive even integer for 2x2 rotation blocks.")
    if not 0.0 <= mu <= 1.0:
        raise ValueError("mu must belong to [0, 1].")


def _rotation_coefficients(mu: float) -> tuple[float, float]:
    theta = 2.0 * math.asin(math.sqrt(mu))
    half_theta = theta / 2.0
    return math.cos(half_theta), math.sin(half_theta)


def build_qflpn_operator(n: int, mu: float) -> csr_matrix:
    """Build block-diagonal RY(theta(mu)) rotations in CSR format."""
    _validate_inputs(n, mu)
    c, s = _rotation_coefficients(mu)
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    for k in range(0, n, 2):
        i, j = k, k + 1
        rows.extend([i, i, j, j])
        cols.extend([i, j, i, j])
        data.extend([c, -s, s, c])
    return csr_matrix((data, (rows, cols)), shape=(n, n), dtype=np.float64)


def build_deterministic_state(n: int) -> np.ndarray:
    _validate_inputs(n, MU)
    idx = np.arange(n, dtype=np.float64)
    x = np.sin(idx) + 0.5 * np.cos(0.37 * idx)
    norm = np.linalg.norm(x)
    if norm == 0.0:
        raise RuntimeError("Initial state has zero norm.")
    return x / norm


def analytical_reference(x: np.ndarray, mu: float) -> np.ndarray:
    _validate_inputs(int(x.size), mu)
    c, s = _rotation_coefficients(mu)
    y = np.empty_like(x)
    y[0::2] = c * x[0::2] - s * x[1::2]
    y[1::2] = s * x[0::2] + c * x[1::2]
    return y


def benchmark(operator: csr_matrix, x: np.ndarray) -> np.ndarray:
    for _ in range(WARMUP):
        operator @ x
    measurements = []
    for _ in range(REPETITIONS):
        t0 = time.perf_counter_ns()
        operator @ x
        t1 = time.perf_counter_ns()
        measurements.append((t1 - t0) / 1_000_000.0)
    return np.asarray(measurements, dtype=np.float64)


def run_dimension(n: int) -> dict[str, float | int | str]:
    construction_start = time.perf_counter()
    operator = build_qflpn_operator(n, MU)
    construction_ms = (time.perf_counter() - construction_start) * 1000.0
    x = build_deterministic_state(n)
    y_reference = analytical_reference(x, MU)
    y_sparse = operator @ x
    max_error = float(np.max(np.abs(y_sparse - y_reference)))
    norm_error = abs(float(np.linalg.norm(y_sparse)) - float(np.linalg.norm(x)))
    measurements = benchmark(operator, x)
    return {
        "dimension": n,
        "nnz": int(operator.nnz),
        "density_percent": float(100.0 * operator.nnz / (n * n)),
        "construction_ms": construction_ms,
        "mean_ms": float(np.mean(measurements)),
        "median_ms": float(np.median(measurements)),
        "min_ms": float(np.min(measurements)),
        "max_ms": float(np.max(measurements)),
        "max_absolute_error": max_error,
        "norm_error": norm_error,
        "target_ms": TARGET_MS,
        "status": "PASS" if max_error <= TOLERANCE and norm_error <= TOLERANCE else "FAIL",
        "timing_status": "PASS" if np.mean(measurements) <= TARGET_MS else "FAIL",
    }


def validate_input_guards() -> None:
    for invalid_n in (0, -2, 3):
        try:
            build_qflpn_operator(invalid_n, MU)
        except ValueError:
            continue
        raise AssertionError(f"Invalid dimension {invalid_n} was not rejected.")
    try:
        build_qflpn_operator(2, 1.1)
    except ValueError:
        pass
    else:
        raise AssertionError("Out-of-range membership was not rejected.")


def main() -> None:
    validate_input_guards()
    RESULTS.mkdir(parents=True, exist_ok=True)
    output_file = RESULTS / "qflpn_operator_validation_python.csv"
    results = []
    for n in DIMENSIONS:
        print(f"Running N={n:,}")
        result = run_dimension(n)
        results.append(result)
        print(f"  mean = {result['mean_ms']:.6f} ms")
        print(f"  max error = {result['max_absolute_error']:.3e}")
        print(f"  norm error = {result['norm_error']:.3e}")
        if result["status"] != "PASS":
            raise AssertionError(f"CSR numerical consistency failed for N={n}.")
    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()
