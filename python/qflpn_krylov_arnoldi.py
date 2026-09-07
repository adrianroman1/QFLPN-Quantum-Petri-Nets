#!/usr/bin/env python3
"""
QFLPN Polynomial Krylov / Arnoldi Benchmark

Deterministic sparse QFLPN operator.
The Arnoldi method approximates exp(A) @ x using
    V_m exp(H_m) e_1 ||x||_2

Scaling:
    q = 4,...,17
    N = 2^q states

Precision:
    float64

Timing protocol:
    warmup = 20
    repetitions = 1000

The analytical reference is evaluated independently from
the sparse matrix-vector implementation.
"""

from pathlib import Path
import csv
import platform
import sys
import time

import numpy as np
import scipy
from scipy.linalg import expm
from scipy.sparse import csr_matrix


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

QUBIT_RANGE = range(4, 18)

WARMUP = 20
REPETITIONS = 1000

MU = 0.70
TIME_STEP = 1.0

# Maximum Krylov dimension.
# For the present deterministic block operator the Arnoldi process may
# terminate earlier through numerical breakdown.
KRYLOV_DIMENSION = 20

THRESHOLD_MS = 15.0

ABS_ERROR_TOL = 1.0e-10

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_FILE = RESULTS_DIR / "qflpn_krylov_arnoldi_python.csv"


# ---------------------------------------------------------------------------
# Deterministic QFLPN state
# ---------------------------------------------------------------------------

def deterministic_state(n: int) -> np.ndarray:
    """
    Construct a deterministic normalized state vector.
    """
    idx = np.arange(n, dtype=np.float64) + 1.0

    x = (
        np.sin(idx)
        + 0.5 * np.cos(0.37 * idx)
    )

    norm_x = np.linalg.norm(x, ord=2)

    if not np.isfinite(norm_x) or norm_x == 0.0:
        raise RuntimeError("Invalid deterministic state normalization.")

    return x / norm_x


# ---------------------------------------------------------------------------
# QFLPN sparse operator
# ---------------------------------------------------------------------------

def qflpn_parameters(mu: float):
    """
    Return the deterministic QFLPN rotation parameters.

    theta(mu) = 2 asin(sqrt(mu))
    R(theta) =
        [ cos(theta)  -sin(theta) ]
        [ sin(theta)   cos(theta) ]
    """
    theta = 2.0 * np.arcsin(np.sqrt(mu))
    c = np.cos(theta)
    s = np.sin(theta)

    return theta, c, s


def build_qflpn_operator(n: int, mu: float) -> csr_matrix:
    """
    Construct the deterministic sparse QFLPN block-rotation operator.

    The matrix contains independent 2x2 rotation blocks:
        [ c  -s ]
        [ s   c ]

    Number of nonzero entries:
        NNZ = 2N
    """
    if n < 2 or n % 2 != 0:
        raise ValueError("State dimension must be a positive even integer.")

    _, c, s = qflpn_parameters(mu)

    blocks = n // 2
    base = 2 * np.arange(blocks, dtype=np.int64)

    rows = np.repeat(np.arange(n, dtype=np.int64), 2)

    cols = np.empty(2 * n, dtype=np.int64)
    data = np.empty(2 * n, dtype=np.float64)

    # Row 2k:
    #     c*x[2k] - s*x[2k+1]
    #
    # Row 2k+1:
    #     s*x[2k] + c*x[2k+1]

    cols[0::4] = base
    cols[1::4] = base + 1
    cols[2::4] = base
    cols[3::4] = base + 1

    data[0::4] = c
    data[1::4] = -s
    data[2::4] = s
    data[3::4] = c

    operator = csr_matrix(
        (data, (rows, cols)),
        shape=(n, n),
        dtype=np.float64,
    )

    operator.sum_duplicates()
    operator.sort_indices()

    return operator


# ---------------------------------------------------------------------------
# Independent analytical reference
# ---------------------------------------------------------------------------

def analytical_exp_reference(
    x: np.ndarray,
    mu: float,
    time_step: float,
) -> np.ndarray:
    """
    Independent analytical reference for exp(time_step * A) @ x.

    For each 2x2 QFLPN block

        A = [ c  -s ]
            [ s   c ]

    write

        A = c I + s J,

    where J^2 = -I.

    Therefore

        exp(t A)
          = exp(t c) [ cos(t s) I + sin(t s) J ].

    This reference does not call sparse matrix multiplication,
    Arnoldi, or scipy.linalg.expm.
    """
    _, c, s = qflpn_parameters(mu)

    tc = time_step * c
    ts = time_step * s

    scale = np.exp(tc)
    cos_term = np.cos(ts)
    sin_term = np.sin(ts)

    y = np.empty_like(x)

    even = x[0::2]
    odd = x[1::2]

    y[0::2] = scale * (
        cos_term * even
        - sin_term * odd
    )

    y[1::2] = scale * (
        sin_term * even
        + cos_term * odd
    )

    return y


# ---------------------------------------------------------------------------
# Arnoldi decomposition
# ---------------------------------------------------------------------------

def arnoldi_decomposition(
    operator: csr_matrix,
    x: np.ndarray,
    krylov_dimension: int,
):
    """
    Construct an Arnoldi basis for K_m(A,x).

    Returns
    -------
    V : ndarray
        Orthonormal Krylov basis.
    H : ndarray
        Upper-Hessenberg projected operator.
    beta : float
        Initial vector norm.
    k_actual : int
        Effective Krylov dimension.

    Modified Gram-Schmidt with one reorthogonalization pass is used.
    """
    n = x.size

    beta = np.linalg.norm(x, ord=2)

    if not np.isfinite(beta) or beta == 0.0:
        raise ValueError("Input vector has invalid norm.")

    m = min(krylov_dimension, n)

    V = np.zeros((n, m), dtype=np.float64)
    H = np.zeros((m, m), dtype=np.float64)

    V[:, 0] = x / beta

    k_actual = 1

    breakdown_tolerance = 1.0e-13

    for j in range(m):
        w = operator @ V[:, j]

        # First modified Gram-Schmidt pass.
        for i in range(j + 1):
            hij = np.dot(V[:, i], w)
            H[i, j] += hij
            w -= hij * V[:, i]

        # Reorthogonalization pass.
        for i in range(j + 1):
            hij = np.dot(V[:, i], w)
            H[i, j] += hij
            w -= hij * V[:, i]

        if j + 1 >= m:
            k_actual = m
            break

        h_next = np.linalg.norm(w, ord=2)

        H[j + 1, j] = h_next

        if (
            not np.isfinite(h_next)
            or h_next <= breakdown_tolerance
        ):
            k_actual = j + 1
            break

        V[:, j + 1] = w / h_next
        k_actual = j + 2

    return (
        V[:, :k_actual],
        H[:k_actual, :k_actual],
        beta,
        k_actual,
    )


# ---------------------------------------------------------------------------
# Polynomial Krylov / Arnoldi matrix-function action
# ---------------------------------------------------------------------------

def arnoldi_exponential_action(
    operator: csr_matrix,
    x: np.ndarray,
    time_step: float,
    krylov_dimension: int,
) -> tuple[np.ndarray, int]:
    """
    Approximate

        exp(time_step * A) @ x

    through polynomial Krylov / Arnoldi:

        V_m exp(time_step * H_m) e_1 ||x||_2
    """
    V, H, beta, k_actual = arnoldi_decomposition(
        operator,
        x,
        krylov_dimension,
    )

    projected = expm(time_step * H)

    e1 = np.zeros(k_actual, dtype=np.float64)
    e1[0] = 1.0

    y = beta * (V @ (projected @ e1))

    return y, k_actual


# ---------------------------------------------------------------------------
# Numerical diagnostics
# ---------------------------------------------------------------------------

def maximum_absolute_error(
    computed: np.ndarray,
    reference: np.ndarray,
) -> float:
    """
    Maximum componentwise absolute error.
    """
    return float(np.max(np.abs(computed - reference)))


def norm_error(
    computed: np.ndarray,
    reference: np.ndarray,
) -> float:
    """
    Relative 2-norm error with respect to the independent reference.
    """
    reference_norm = np.linalg.norm(reference, ord=2)

    if reference_norm == 0.0:
        return float(np.linalg.norm(computed, ord=2))

    return float(
        np.linalg.norm(computed - reference, ord=2)
        / reference_norm
    )


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

def measure_arnoldi(
    operator: csr_matrix,
    x: np.ndarray,
    time_step: float,
    krylov_dimension: int,
):
    """
    Measure the complete Arnoldi matrix-function action.

    Matrix construction and result serialization are outside the timing
    interval.
    """
    # Warm-up phase.
    for _ in range(WARMUP):
        y, k_actual = arnoldi_exponential_action(
            operator,
            x,
            time_step,
            krylov_dimension,
        )

    times_ms = np.empty(REPETITIONS, dtype=np.float64)

    k_actual = 0
    y = None

    for i in range(REPETITIONS):
        start_ns = time.perf_counter_ns()

        y, k_actual = arnoldi_exponential_action(
            operator,
            x,
            time_step,
            krylov_dimension,
        )

        elapsed_ns = time.perf_counter_ns() - start_ns
        times_ms[i] = elapsed_ns / 1.0e6

    return y, k_actual, times_ms


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

CSV_HEADER = [
    "language",
    "qubits",
    "states",
    "nnz",
    "warmup",
    "repetitions",
    "fuzzy_membership",
    "rotation_angle_rad",
    "time_step",
    "krylov_dimension",
    "effective_krylov_dimension",
    "mean_arnoldi_ms",
    "median_arnoldi_ms",
    "min_arnoldi_ms",
    "max_arnoldi_ms",
    "maximum_error",
    "relative_norm_error",
    "target_ms",
    "numerical_status",
    "timing_status",
]


def write_result(
    writer,
    q: int,
    n: int,
    nnz: int,
    theta: float,
    effective_k: int,
    times_ms: np.ndarray,
    max_error: float,
    rel_norm_error: float,
):
    mean_ms = float(np.mean(times_ms))
    median_ms = float(np.median(times_ms))
    min_ms = float(np.min(times_ms))
    max_ms = float(np.max(times_ms))

    numerical_ok = (
        np.isfinite(max_error)
        and np.isfinite(rel_norm_error)
        and max_error <= ABS_ERROR_TOL
        and rel_norm_error <= ABS_ERROR_TOL
    )

    timing_ok = (
        np.isfinite(mean_ms)
        and mean_ms <= THRESHOLD_MS
    )

    numerical_status = "PASS" if numerical_ok else "FAIL"
    timing_status = "PASS" if timing_ok else "FAIL"

    writer.writerow([
        "Python",
        q,
        n,
        nnz,
        WARMUP,
        REPETITIONS,
        f"{MU:.12f}",
        f"{theta:.12f}",
        f"{TIME_STEP:.12f}",
        KRYLOV_DIMENSION,
        effective_k,
        f"{mean_ms:.12f}",
        f"{median_ms:.12f}",
        f"{min_ms:.12f}",
        f"{max_ms:.12f}",
        f"{max_error:.16e}",
        f"{rel_norm_error:.16e}",
        f"{THRESHOLD_MS:.6f}",
        numerical_status,
        timing_status,
    ])

    return (
        mean_ms,
        median_ms,
        min_ms,
        max_ms,
        numerical_status,
        timing_status,
    )


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------

def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    theta, _, _ = qflpn_parameters(MU)

    print("=" * 72)
    print("QFLPN POLYNOMIAL KRYLOV / ARNOLDI BENCHMARK - PYTHON")
    print("=" * 72)
    print(f"Qubit range             : 4 ... 17")
    print(f"Warmup repetitions      : {WARMUP}")
    print(f"Measured repetitions    : {REPETITIONS}")
    print(f"Fuzzy membership        : {MU:.12f}")
    print(f"Rotation angle          : {theta:.12f} rad")
    print(f"Time step               : {TIME_STEP:.12f}")
    print(f"Krylov dimension        : {KRYLOV_DIMENSION}")
    print(f"Target time             : {THRESHOLD_MS:.6f} ms")
    print(f"Output                  : {RESULTS_FILE}")
    print("=" * 72)

    overall_numerical_ok = True
    overall_timing_ok = True

    with RESULTS_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.writer(csv_file)
        writer.writerow(CSV_HEADER)

        for q in QUBIT_RANGE:
            n = 2 ** q

            print()
            print(f"q={q:2d}  states={n:6d}")

            operator = build_qflpn_operator(n, MU)

            x = deterministic_state(n)

            reference = analytical_exp_reference(
                x,
                MU,
                TIME_STEP,
            )

            y, effective_k, times_ms = measure_arnoldi(
                operator,
                x,
                TIME_STEP,
                KRYLOV_DIMENSION,
            )

            max_error = maximum_absolute_error(
                y,
                reference,
            )

            relative_error = norm_error(
                y,
                reference,
            )

            (
                mean_ms,
                median_ms,
                min_ms,
                max_ms,
                numerical_status,
                timing_status,
            ) = write_result(
                writer,
                q,
                n,
                int(operator.nnz),
                theta,
                effective_k,
                times_ms,
                max_error,
                relative_error,
            )

            overall_numerical_ok &= numerical_status == "PASS"
            overall_timing_ok &= timing_status == "PASS"

            print(
                f"  NNZ                     : {operator.nnz}"
            )
            print(
                f"  Effective Krylov dim.   : {effective_k}"
            )
            print(
                f"  Mean                    : {mean_ms:.9f} ms"
            )
            print(
                f"  Median                  : {median_ms:.9f} ms"
            )
            print(
                f"  Min                     : {min_ms:.9f} ms"
            )
            print(
                f"  Max                     : {max_ms:.9f} ms"
            )
            print(
                f"  Maximum absolute error  : {max_error:.16e}"
            )
            print(
                f"  Relative norm error     : {relative_error:.16e}"
            )
            print(
                f"  Numerical status        : {numerical_status}"
            )
            print(
                f"  Timing status           : {timing_status}"
            )

    print()
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print(
        f"Numerical status : "
        f"{'PASS' if overall_numerical_ok else 'FAIL'}"
    )
    print(
        f"Timing status    : "
        f"{'PASS' if overall_timing_ok else 'FAIL'}"
    )
    print(f"CSV file         : {RESULTS_FILE}")
    print("=" * 72)

    if not overall_numerical_ok or not overall_timing_ok:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
