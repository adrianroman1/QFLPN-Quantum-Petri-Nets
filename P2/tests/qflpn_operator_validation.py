"""Sparse-operator benchmark using the standard RY convention."""

from __future__ import annotations

import csv
import math
import time
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix

DIMENSIONS = (1024, 10_000, 100_000)
MU = 0.70
WARMUP = 20
REPETITIONS = 1000
TARGET_MS = 15.0

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def _validated_mu(mu: float) -> float:
    if isinstance(mu, (bool, np.bool_)):
        raise TypeError("mu must not be Boolean.")
    value = float(mu)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("mu must be finite and lie in [0, 1].")
    return value


def _ry_coefficients(mu: float) -> tuple[float, float]:
    theta = 2.0 * math.asin(math.sqrt(_validated_mu(mu)))
    return math.cos(theta / 2.0), math.sin(theta / 2.0)


def build_qflpn_operator(n: int, mu: float) -> csr_matrix:
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer.")
    if n < 2 or n % 2:
        raise ValueError("n must be a positive even integer >= 2.")

    c, s = _ry_coefficients(mu)
    indices = np.arange(0, n, 2)

    rows = np.column_stack(
        (indices, indices, indices + 1, indices + 1)
    ).ravel()
    cols = np.column_stack(
        (indices, indices + 1, indices, indices + 1)
    ).ravel()
    data = np.tile(np.array([c, -s, s, c]), n // 2)

    return csr_matrix((data, (rows, cols)), shape=(n, n))


def build_deterministic_state(n: int) -> np.ndarray:
    idx = np.arange(n, dtype=np.float64)
    vector = np.sin(idx) + 0.5 * np.cos(0.37 * idx)
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0.0:
        raise RuntimeError("Invalid initial-state norm.")
    return vector / norm


def analytical_reference(x: np.ndarray, mu: float) -> np.ndarray:
    vector = np.asarray(x, dtype=np.float64)
    if vector.ndim != 1 or vector.size % 2:
        raise ValueError("x must be a one-dimensional even-length vector.")
    c, s = _ry_coefficients(mu)
    result = np.empty_like(vector)
    result[0::2] = c * vector[0::2] - s * vector[1::2]
    result[1::2] = s * vector[0::2] + c * vector[1::2]
    return result


def benchmark(operator: csr_matrix, vector: np.ndarray) -> np.ndarray:
    for _ in range(WARMUP):
        operator @ vector

    samples = []
    for _ in range(REPETITIONS):
        start = time.perf_counter_ns()
        operator @ vector
        samples.append((time.perf_counter_ns() - start) / 1_000_000.0)
    return np.asarray(samples, dtype=np.float64)


def run_dimension(n: int) -> dict[str, object]:
    start = time.perf_counter()
    operator = build_qflpn_operator(n, MU)
    construction_ms = (time.perf_counter() - start) * 1000.0

    vector = build_deterministic_state(n)
    expected = analytical_reference(vector, MU)
    actual = operator @ vector

    max_error = float(np.max(np.abs(actual - expected)))
    norm_error = abs(float(np.linalg.norm(actual)) - 1.0)
    timings = benchmark(operator, vector)

    numerical_pass = max_error <= 1e-12 and norm_error <= 1e-12
    timing_pass = float(np.mean(timings)) <= TARGET_MS

    return {
        "dimension": n,
        "nnz": int(operator.nnz),
        "density_percent": 100.0 * operator.nnz / (n * n),
        "construction_ms": construction_ms,
        "mean_ms": float(np.mean(timings)),
        "median_ms": float(np.median(timings)),
        "min_ms": float(np.min(timings)),
        "max_ms": float(np.max(timings)),
        "max_absolute_error": max_error,
        "norm_error": norm_error,
        "target_ms": TARGET_MS,
        "numerical_status": "PASS" if numerical_pass else "FAIL",
        "timing_status": "PASS" if timing_pass else "FAIL",
    }


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / "qflpn_operator_validation_python.csv"
    results = [run_dimension(n) for n in DIMENSIONS]

    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    for result in results:
        print(result)

    failed = any(
        row["numerical_status"] != "PASS"
        or row["timing_status"] != "PASS"
        for row in results
    )
    print("STATUS:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
