from pathlib import Path
import csv
import math
import platform
import sys
import time

import numpy as np
import scipy
from scipy.sparse import csr_matrix


# ============================================================
# QFLPN SCALING BENCHMARK
# Deterministic sparse/unitary block-rotation operator
# ============================================================

QUBIT_RANGE = range(4, 18)       # q = 4 ... 17
WARMUP = 20
REPETITIONS = 1000

MU = 0.70
THRESHOLD_MS = 15.0

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_FILE = RESULTS_DIR / "qflpn_scaling_python.csv"


def rotation_parameters(mu: float):
    """
    QFLPN fuzzy-to-rotation convention:

        theta = 2 asin(sqrt(mu))

    with the corresponding 2x2 rotation block.
    """
    theta = 2.0 * math.asin(math.sqrt(mu))
    c = math.cos(theta)
    s = math.sin(theta)
    return theta, c, s


def deterministic_state(n: int) -> np.ndarray:
    """
    Deterministic normalized input state.
    """
    idx = np.arange(n, dtype=np.float64) + 1.0

    x = (
        np.sin(idx)
        + 0.5 * np.cos(0.37 * idx)
    )

    norm_x = np.linalg.norm(x, ord=2)

    if norm_x == 0.0:
        raise RuntimeError("Invalid zero input state.")

    return x / norm_x


def build_operator(n: int, c: float, s: float) -> csr_matrix:
    """
    Construct the deterministic sparse QFLPN operator.

    Each consecutive pair receives:

        [ c  -s ]
        [ s   c ]

    The global operator is block diagonal and orthogonal.
    """

    if n % 2 != 0:
        raise ValueError("State dimension must be even.")

    blocks = n // 2

    base = 2 * np.arange(blocks, dtype=np.int64)

    rows = np.repeat(np.arange(n, dtype=np.int64), 2)

    cols = np.empty(2 * n, dtype=np.int64)
    data = np.empty(2 * n, dtype=np.float64)

    # Row 0: columns 0,1
    # Row 1: columns 0,1
    # Row 2: columns 2,3
    # Row 3: columns 2,3
    # ...

    cols[0::4] = base
    cols[1::4] = base + 1
    cols[2::4] = base
    cols[3::4] = base + 1

    data[0::4] = c
    data[1::4] = -s
    data[2::4] = s
    data[3::4] = c

    return csr_matrix(
        (data, (rows, cols)),
        shape=(n, n),
        dtype=np.float64,
    )


def reference_apply(
    x: np.ndarray,
    c: float,
    s: float,
) -> np.ndarray:
    """
    Independent analytical application of the same
    2x2 rotation rule.

    This does not use sparse matrix multiplication.
    """

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


def measure_operator(
    A: csr_matrix,
    x: np.ndarray,
):
    """
    Warmup followed by the measured sparse matrix-vector
    operations.
    """

    for _ in range(WARMUP):
        A @ x

    times_ms = np.empty(REPETITIONS, dtype=np.float64)

    y = None

    for i in range(REPETITIONS):
        start_ns = time.perf_counter_ns()

        y = A @ x

        end_ns = time.perf_counter_ns()

        times_ms[i] = (end_ns - start_ns) / 1_000_000.0

    return y, times_ms


def write_results(rows):
    """
    Write CSV using the standard library.
    """

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "language",
        "qubits",
        "states",
        "nnz",
        "warmup",
        "repetitions",
        "fuzzy_membership",
        "rotation_angle_rad",
        "mean_state_ms",
        "median_state_ms",
        "min_state_ms",
        "max_state_ms",
        "maximum_error",
        "norm_preservation_error",
        "target_ms",
        "numerical_status",
        "timing_status",
    ]

    with RESULTS_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def main():
    theta, c, s = rotation_parameters(MU)

    print("=" * 64)
    print("QFLPN SCALING BENCHMARK - PYTHON")
    print("=" * 64)
    print(f"Qubit range          : 4 ... 17")
    print(f"State range          : 16 ... 131072")
    print(f"Warmup repetitions   : {WARMUP}")
    print(f"Measured repetitions : {REPETITIONS}")
    print(f"Fuzzy membership     : {MU:.12f}")
    print(f"Rotation angle       : {theta:.12f} rad")
    print(f"Target time          : {THRESHOLD_MS:.6f} ms")
    print()

    print(f"Python               : {sys.version.split()[0]}")
    print(f"NumPy                : {np.__version__}")
    print(f"SciPy                : {scipy.__version__}")
    print(f"Platform             : {platform.platform()}")
    print()

    rows = []

    for q in QUBIT_RANGE:

        n = 2 ** q

        print(
            f"q={q:2d} | "
            f"N={n:6d} | "
            f"NNZ={2*n:7d}",
            end=" | ",
            flush=True,
        )

        construction_start = time.perf_counter_ns()

        x = deterministic_state(n)
        A = build_operator(n, c, s)

        construction_end = time.perf_counter_ns()

        construction_ms = (
            construction_end - construction_start
        ) / 1_000_000.0

        y_ref = reference_apply(x, c, s)

        y, times_ms = measure_operator(A, x)

        maximum_error = float(
            np.max(np.abs(y - y_ref))
        )

        norm_preservation_error = float(
            abs(np.linalg.norm(y, ord=2) - 1.0)
        )

        mean_ms = float(np.mean(times_ms))
        median_ms = float(np.median(times_ms))
        min_ms = float(np.min(times_ms))
        max_ms = float(np.max(times_ms))

        numerical_ok = (
            np.isfinite(maximum_error)
            and np.isfinite(norm_preservation_error)
            and maximum_error <= 1e-12
            and norm_preservation_error <= 1e-12
        )

        timing_ok = (
            np.isfinite(mean_ms)
            and mean_ms <= THRESHOLD_MS
        )

        numerical_status = (
            "PASS"
            if numerical_ok
            else "FAIL"
        )

        timing_status = (
            "PASS"
            if timing_ok
            else "FAIL"
        )

        print(
            f"mean={mean_ms:.6f} ms | "
            f"median={median_ms:.6f} ms | "
            f"maxerr={maximum_error:.3e} | "
            f"normerr={norm_preservation_error:.3e} | "
            f"build={construction_ms:.3f} ms | "
            f"{numerical_status}/{timing_status}"
        )

        rows.append(
            {
                "language": "Python",
                "qubits": q,
                "states": n,
                "nnz": 2 * n,
                "warmup": WARMUP,
                "repetitions": REPETITIONS,
                "fuzzy_membership": f"{MU:.12f}",
                "rotation_angle_rad": f"{theta:.12f}",
                "mean_state_ms": f"{mean_ms:.9f}",
                "median_state_ms": f"{median_ms:.9f}",
                "min_state_ms": f"{min_ms:.9f}",
                "max_state_ms": f"{max_ms:.9f}",
                "maximum_error": f"{maximum_error:.16e}",
                "norm_preservation_error": (
                    f"{norm_preservation_error:.16e}"
                ),
                "target_ms": f"{THRESHOLD_MS:.6f}",
                "numerical_status": numerical_status,
                "timing_status": timing_status,
            }
        )

    write_results(rows)

    print()
    print("=" * 64)
    print(f"Results written to:")
    print(RESULTS_FILE)
    print("=" * 64)


if __name__ == "__main__":
    main()