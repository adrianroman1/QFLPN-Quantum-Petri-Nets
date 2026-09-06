"""
QFLPN scalable deterministic benchmark - Python
================================================

Benchmark the action of a sparse, unitary QFLPN transition operator
on state dimensions:

    1,024
    10,000
    100,000

Interpretation:
    1,024 = 2^10 and corresponds to a 10-qubit state space.

    10,000 and 100,000 are numerical state-vector dimensions.
    They are NOT interpreted as exact 2^n qubit Hilbert-space dimensions.

The transition operator is a deterministic block-diagonal product
of 2x2 rotations.

Declared QFLPN fuzzy-to-quantum mapping:

    theta(mu) = 2 asin(sqrt(mu))

No Monte Carlo.
No random sampling.

Outputs:

    results/scaling/qflpn_python_scaling_results.csv
"""

from __future__ import annotations

import csv
import math
import time
from pathlib import Path

import numpy as np


# ============================================================
# Configuration
# ============================================================

DIMENSIONS = (
    1024,
    10_000,
    100_000,
)

MU = 0.70

REPETITIONS = 1000
WARMUP = 20

TARGET_MS = 15.0
TOLERANCE = 1e-12

OUTPUT_FILE = Path(
    "results/scaling/qflpn_python_scaling_results.csv"
)


# ============================================================
# QFLPN fuzzy -> quantum mapping
# ============================================================

def fuzzy_to_angle(mu: float) -> float:
    """
    Declared QFLPN mapping:

        theta(mu) = 2 asin(sqrt(mu))
    """

    if not 0.0 <= mu <= 1.0:
        raise ValueError(
            "Fuzzy membership must belong to [0, 1]."
        )

    return 2.0 * math.asin(
        math.sqrt(mu)
    )


# ============================================================
# Deterministic sparse unitary transition
# ============================================================

def build_transition_operator(
    dimension: int,
):
    """
    Build a sparse block-diagonal unitary operator.

    Each 2x2 block is:

        [ cos(theta/2)  -sin(theta/2) ]
        [ sin(theta/2)   cos(theta/2) ]

    Therefore every block is unitary.

    If dimension is odd, the final basis component
    is left unchanged.
    """

    try:
        from scipy.sparse import csr_matrix
    except ImportError as exc:
        raise RuntimeError(
            "This benchmark requires scipy."
        ) from exc

    if dimension < 1:
        raise ValueError(
            "Dimension must be positive."
        )

    theta = fuzzy_to_angle(MU)

    c = math.cos(theta / 2.0)
    s = math.sin(theta / 2.0)

    rows = []
    cols = []
    data = []

    for i in range(0, dimension - 1, 2):

        rows.extend(
            [
                i,
                i,
                i + 1,
                i + 1,
            ]
        )

        cols.extend(
            [
                i,
                i + 1,
                i,
                i + 1,
            ]
        )

        data.extend(
            [
                c,
                -s,
                s,
                c,
            ]
        )

    if dimension % 2 == 1:

        last = dimension - 1

        rows.append(last)
        cols.append(last)
        data.append(1.0)

    return csr_matrix(
        (
            data,
            (rows, cols),
        ),
        shape=(
            dimension,
            dimension,
        ),
    )


# ============================================================
# Deterministic normalized state
# ============================================================

def build_reference_state(
    dimension: int,
) -> np.ndarray:
    """
    Construct a deterministic normalized state vector.

    No random numbers are used.
    """

    indices = np.arange(
        1,
        dimension + 1,
        dtype=np.float64,
    )

    state = 1.0 / np.sqrt(indices)

    state = state.astype(
        np.complex128
    )

    state /= np.linalg.norm(state)

    return state


# ============================================================
# Benchmark one dimension
# ============================================================

def benchmark_dimension(
    dimension: int,
) -> dict:

    operator = build_transition_operator(
        dimension
    )

    state = build_reference_state(
        dimension
    )

    # --------------------------------------------------------
    # Warm-up
    # --------------------------------------------------------

    for _ in range(WARMUP):

        operator @ state

    # --------------------------------------------------------
    # Timed execution
    # --------------------------------------------------------

    timings_ns = []

    output = None

    for _ in range(REPETITIONS):

        start = time.perf_counter_ns()

        output = operator @ state

        end = time.perf_counter_ns()

        timings_ns.append(
            end - start
        )

    timings_ms = (
        np.asarray(
            timings_ns,
            dtype=np.float64,
        )
        / 1_000_000.0
    )

    if output is None:
        raise RuntimeError(
            "Benchmark produced no output."
        )

    # --------------------------------------------------------
    # Numerical validation
    # --------------------------------------------------------

    input_norm = np.linalg.norm(
        state
    )

    output_norm = np.linalg.norm(
        output
    )

    norm_error = abs(
        output_norm - input_norm
    )

    reference = operator.dot(
        state
    )

    maximum_error = float(
        np.max(
            np.abs(
                output - reference
            )
        )
    )

    numerical_error = max(
        norm_error,
        maximum_error,
    )

    numerical_status = (
        "PASS"
        if numerical_error <= TOLERANCE
        else "REVIEW REQUIRED"
    )

    mean_ms = float(
        np.mean(timings_ms)
    )

    timing_status = (
        "PASS"
        if mean_ms <= TARGET_MS
        else "TARGET NOT MET"
    )

    # --------------------------------------------------------
    # Quibit interpretation
    # --------------------------------------------------------

    if dimension > 0 and (
        dimension
        & (dimension - 1)
    ) == 0:

        qubits = int(
            math.log2(dimension)
        )

    else:

        qubits = "NA"

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    return {

        "language": "Python",

        "dimension": dimension,

        "qubits_if_power_of_two": qubits,

        "nnz": int(
            operator.nnz
        ),

        "repetitions": REPETITIONS,

        "warmup": WARMUP,

        "mean_ms": mean_ms,

        "median_ms": float(
            np.median(
                timings_ms
            )
        ),

        "min_ms": float(
            np.min(
                timings_ms
            )
        ),

        "max_ms": float(
            np.max(
                timings_ms
            )
        ),

        "target_ms": TARGET_MS,

        "norm_error": float(
            norm_error
        ),

        "maximum_error": maximum_error,

        "numerical_status": numerical_status,

        "timing_status": timing_status,
    }


# ============================================================
# Main
# ============================================================

def main() -> None:

    print("=" * 72)
    print(
        "QFLPN SCALING BENCHMARK - PYTHON"
    )
    print("=" * 72)

    print(
        "Deterministic sparse unitary transition."
    )

    print(
        "Monte Carlo: NOT USED."
    )

    print(
        f"Target: {TARGET_MS:.1f} ms"
    )

    results = []

    for dimension in DIMENSIONS:

        result = benchmark_dimension(
            dimension
        )

        results.append(
            result
        )

        print()
        print(
            f"Dimension: {dimension}"
        )

        print(
            f"  NNZ               : "
            f"{result['nnz']}"
        )

        print(
            f"  mean              : "
            f"{result['mean_ms']:.6f} ms"
        )

        print(
            f"  median            : "
            f"{result['median_ms']:.6f} ms"
        )

        print(
            f"  min               : "
            f"{result['min_ms']:.6f} ms"
        )

        print(
            f"  max               : "
            f"{result['max_ms']:.6f} ms"
        )

        print(
            f"  norm error        : "
            f"{result['norm_error']:.3e}"
        )

        print(
            f"  maximum error     : "
            f"{result['maximum_error']:.3e}"
        )

        print(
            f"  numerical status  : "
            f"{result['numerical_status']}"
        )

        print(
            f"  15 ms status      : "
            f"{result['timing_status']}"
        )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        fieldnames = list(
            results[0].keys()
        )

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            results
        )

    print()
    print(
        f"CSV exported: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":

    main()
