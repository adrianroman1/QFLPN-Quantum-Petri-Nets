import csv
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np
from scipy import __version__ as SCIPY_VERSION
from scipy.sparse import csr_matrix


# ============================================================
# QFLPN SCALING BENCHMARK
#
# Deterministic sparse QFLPN operator benchmark.
#
# State-space dimensions:
#       N = 1,024
#       N = 10,000
#       N = 100,000
#
# IMPORTANT:
# These are STATE-SPACE DIMENSIONS, not qubit counts.
#
# N = 1,024 = 2^10 -> equivalent to 10 qubits.
# N = 10,000 and N = 100,000 are general numerical
# state-space dimensions and are not full 2^q quantum
# state-vector simulations.
#
# No random numbers.
# No Monte Carlo.
# No dense N x N matrix.
#
# Operator:
#
#     U = blockdiag(R(theta), R(theta), ..., R(theta))
#
# with
#
#     R(theta) =
#
#       [ cos(theta)  -sin(theta) ]
#       [ sin(theta)   cos(theta) ]
#
# and
#
#     theta = 2 asin(sqrt(mu))
#
#     mu = 0.70
#
# Each block is unitary/orthogonal in exact arithmetic.
#
# The benchmark measures deterministic CSR sparse
# matrix-vector multiplication:
#
#     y = U x
#
# Numerical validation is performed against an independent
# analytical reference, NOT against another CSR multiplication.
# ============================================================


# ------------------------------------------------------------
# Experimental parameters
# ------------------------------------------------------------

DIMENSIONS = [
    1024,
    10000,
    100000,
]

MU = 0.70

WARMUP_REPETITIONS = 20
BENCHMARK_REPETITIONS = 1000

TARGET_MS = 15.0

NUMERICAL_TOLERANCE = 1.0e-12

OUTPUT_DIRECTORY = (
    Path(__file__).resolve().parent / "results"
)

OUTPUT_FILE = (
    OUTPUT_DIRECTORY /
    "qflpn_scaling_python.csv"
)


# ------------------------------------------------------------
# Equivalent qubit count
# ------------------------------------------------------------

def equivalent_qubits_if_power_of_two(n):
    """
    Return q only when N = 2^q.

    For example:
        N = 1024 -> q = 10

    For non-powers of two:
        N = 10000 -> ""
        N = 100000 -> ""
    """

    if n <= 0:
        return ""

    q = int(round(math.log2(n)))

    if 2 ** q == n:
        return q

    return ""


# ------------------------------------------------------------
# Deterministic initial state
# ------------------------------------------------------------

def build_deterministic_state(n):
    """
    Construct a deterministic normalized state vector.

    No random numbers are used.

        x_i = sin(i) + 0.5 cos(0.37 i)

    The vector is normalized in the Euclidean 2-norm.
    """

    index = np.arange(
        n,
        dtype=np.float64
    )

    x = (
        np.sin(index)
        +
        0.5 * np.cos(0.37 * index)
    )

    norm = np.linalg.norm(
        x,
        ord=2
    )

    if norm == 0.0:
        raise RuntimeError(
            "Deterministic initial state has zero norm."
        )

    return x / norm


# ------------------------------------------------------------
# QFLPN sparse operator
# ------------------------------------------------------------

def build_qflpn_operator(n, mu):
    """
    Construct the deterministic QFLPN transition operator
    in CSR format.

    The matrix consists of n/2 independent 2x2 rotation
    blocks:

        [ c  -s ]
        [ s   c ]

    where:

        theta = 2 asin(sqrt(mu))
        c = cos(theta)
        s = sin(theta)

    The matrix has exactly 2 non-zero entries per row,
    hence:

        NNZ = 2N
    """

    if n % 2 != 0:
        raise ValueError(
            "This benchmark requires even state-space dimensions."
        )

    theta = (
        2.0 *
        math.asin(
            math.sqrt(mu)
        )
    )

    c = math.cos(theta)
    s = math.sin(theta)

    number_of_blocks = n // 2

    # --------------------------------------------------------
    # Row indices
    # --------------------------------------------------------

    rows = np.repeat(
        np.arange(n, dtype=np.int64),
        2
    )

    # --------------------------------------------------------
    # Column indices
    #
    # For every block:
    #
    # row 2k     -> columns 2k, 2k+1
    # row 2k + 1 -> columns 2k, 2k+1
    # --------------------------------------------------------

    block_index = np.arange(
        number_of_blocks,
        dtype=np.int64
    )

    first = (
        2 *
        block_index
    )

    second = first + 1

    cols = np.empty(
        2 * n,
        dtype=np.int64
    )

    cols[0::4] = first
    cols[1::4] = second
    cols[2::4] = first
    cols[3::4] = second

    # --------------------------------------------------------
    # Matrix values
    # --------------------------------------------------------

    values = np.empty(
        2 * n,
        dtype=np.float64
    )

    values[0::4] = c
    values[1::4] = -s
    values[2::4] = s
    values[3::4] = c

    operator = csr_matrix(
        (
            values,
            (
                rows,
                cols
            )
        ),
        shape=(
            n,
            n
        ),
        dtype=np.float64
    )

    operator.sum_duplicates()

    return operator


# ------------------------------------------------------------
# Independent analytical reference
# ------------------------------------------------------------

def analytical_reference(x, mu):
    """
    Compute the reference result independently from CSR.

    This implements the mathematical 2x2 transformation
    directly on vector pairs.

    It is intentionally NOT calculated as:

        operator @ x

    because that would make the numerical validation
    tautological.
    """

    theta = (
        2.0 *
        math.asin(
            math.sqrt(mu)
        )
    )

    c = math.cos(theta)
    s = math.sin(theta)

    y = np.empty_like(x)

    even = slice(
        0,
        None,
        2
    )

    odd = slice(
        1,
        None,
        2
    )

    y[even] = (
        c * x[even]
        -
        s * x[odd]
    )

    y[odd] = (
        s * x[even]
        +
        c * x[odd]
    )

    return y


# ------------------------------------------------------------
# Benchmark one dimension
# ------------------------------------------------------------

def benchmark_dimension(n):
    print(
        f"Running N = {n:,}"
    )

    # --------------------------------------------------------
    # Deterministic input
    # --------------------------------------------------------

    x = build_deterministic_state(
        n
    )

    input_norm = np.linalg.norm(
        x,
        ord=2
    )

    # --------------------------------------------------------
    # Operator construction
    # --------------------------------------------------------

    construction_start = (
        time.perf_counter_ns()
    )

    operator = build_qflpn_operator(
        n,
        MU
    )

    construction_end = (
        time.perf_counter_ns()
    )

    construction_ms = (
        construction_end -
        construction_start
    ) / 1_000_000.0

    # --------------------------------------------------------
    # Structural validation
    # --------------------------------------------------------

    expected_nnz = 2 * n

    if operator.nnz != expected_nnz:
        raise RuntimeError(
            "CSR structural validation failed: "
            f"expected NNZ={expected_nnz}, "
            f"obtained NNZ={operator.nnz}."
        )

    # --------------------------------------------------------
    # Independent analytical reference
    # --------------------------------------------------------

    reference = analytical_reference(
        x,
        MU
    )

    # --------------------------------------------------------
    # Warm-up
    # --------------------------------------------------------

    y = None

    for _ in range(
        WARMUP_REPETITIONS
    ):
        y = operator @ x

    # --------------------------------------------------------
    # Timed deterministic CSR SpMV
    # --------------------------------------------------------

    timings_ms = np.empty(
        BENCHMARK_REPETITIONS,
        dtype=np.float64
    )

    for repetition in range(
        BENCHMARK_REPETITIONS
    ):

        start = (
            time.perf_counter_ns()
        )

        y = operator @ x

        end = (
            time.perf_counter_ns()
        )

        timings_ms[repetition] = (
            end - start
        ) / 1_000_000.0

    # --------------------------------------------------------
    # Numerical validation
    # --------------------------------------------------------

    maximum_error = float(
        np.max(
            np.abs(
                y -
                reference
            )
        )
    )

    output_norm = float(
        np.linalg.norm(
            y,
            ord=2
        )
    )

    norm_error = abs(
        output_norm -
        input_norm
    )

    numerical_status = (
        "PASS"
        if (
            maximum_error <=
            NUMERICAL_TOLERANCE
            and
            norm_error <=
            NUMERICAL_TOLERANCE
        )
        else
        "FAIL"
    )

    # --------------------------------------------------------
    # Timing statistics
    # --------------------------------------------------------

    mean_ms = float(
        np.mean(
            timings_ms
        )
    )

    median_ms = float(
        np.median(
            timings_ms
        )
    )

    min_ms = float(
        np.min(
            timings_ms
        )
    )

    max_ms = float(
        np.max(
            timings_ms
        )
    )

    timing_status = (
        "PASS"
        if mean_ms <= TARGET_MS
        else
        "FAIL"
    )

    # --------------------------------------------------------
    # Console output
    # --------------------------------------------------------

    print(
        f"  NNZ             = {operator.nnz:,}"
    )

    print(
        f"  Construction    = "
        f"{construction_ms:.6f} ms"
    )

    print(
        f"  Mean SpMV       = "
        f"{mean_ms:.6f} ms"
    )

    print(
        f"  Median SpMV     = "
        f"{median_ms:.6f} ms"
    )

    print(
        f"  Minimum SpMV    = "
        f"{min_ms:.6f} ms"
    )

    print(
        f"  Maximum SpMV    = "
        f"{max_ms:.6f} ms"
    )

    print(
        f"  Maximum error   = "
        f"{maximum_error:.3e}"
    )

    print(
        f"  Norm error      = "
        f"{norm_error:.3e}"
    )

    print(
        f"  Numerical       = "
        f"{numerical_status}"
    )

    print(
        f"  Timing          = "
        f"{timing_status}"
    )

    print()

    return {
        "language": "Python",
        "dimension_type": "state_space",
        "states": n,
        "equivalent_qubits": (
            equivalent_qubits_if_power_of_two(n)
        ),
        "nnz": operator.nnz,
        "mu": MU,
        "warmup": WARMUP_REPETITIONS,
        "repetitions": BENCHMARK_REPETITIONS,
        "construction_ms": construction_ms,
        "mean_ms": mean_ms,
        "median_ms": median_ms,
        "min_ms": min_ms,
        "max_ms": max_ms,
        "maximum_error": maximum_error,
        "input_norm": float(input_norm),
        "output_norm": output_norm,
        "norm_error": norm_error,
        "target_ms": TARGET_MS,
        "numerical_tolerance": NUMERICAL_TOLERANCE,
        "numerical_status": numerical_status,
        "timing_status": timing_status,
        "python_version": (
            platform.python_version()
        ),
        "numpy_version": np.__version__,
        "scipy_version": SCIPY_VERSION,
        "platform": platform.platform(),
        "processor": platform.processor(),
    }


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    results = []

    print(
        "============================================================"
    )
    print(
        "QFLPN DETERMINISTIC CSR SCALING BENCHMARK"
    )
    print(
        "============================================================"
    )

    print(
        f"Dimensions: {DIMENSIONS}"
    )

    print(
        f"mu = {MU}"
    )

    print(
        f"Warm-up repetitions = "
        f"{WARMUP_REPETITIONS}"
    )

    print(
        f"Benchmark repetitions = "
        f"{BENCHMARK_REPETITIONS}"
    )

    print(
        f"Target = {TARGET_MS:.3f} ms"
    )

    print(
        "Monte Carlo = NOT USED"
    )

    print()

    for n in DIMENSIONS:

        results.append(
            benchmark_dimension(n)
        )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    fieldnames = list(
        results[0].keys()
    )

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            results
        )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print(
        "============================================================"
    )

    print(
        "QFLPN scaling benchmark completed."
    )

    print(
        f"Results: {OUTPUT_FILE}"
    )

    print(
        "============================================================"
    )

    for result in results:

        print(
            f"N={result['states']:,} | "
            f"NNZ={result['nnz']:,} | "
            f"mean={result['mean_ms']:.6f} ms | "
            f"max_error="
            f"{result['maximum_error']:.3e} | "
            f"numerical="
            f"{result['numerical_status']} | "
            f"timing="
            f"{result['timing_status']}"
        )


if __name__ == "__main__":
    main()