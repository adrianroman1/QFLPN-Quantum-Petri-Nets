import csv
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix


# ============================================================
# QFLPN SCALING BENCHMARK
#
# Qubits:
#       q = 4 ... 17
#
# State-space dimension:
#       N = 2^q
#
# The same QFLPN transition operator is scaled with q.
#
# The operator is:
#
#       U = I_(2^(q-1)) kron RY(theta)
#
# where
#
#       theta = 2 asin(sqrt(mu))
#
# and
#
#       mu = 0.70
#
# ============================================================


MIN_QUBITS = 4
MAX_QUBITS = 17

MU = 0.70

WARMUP = 20
REPETITIONS = 1000

TARGET_MS = 15.0
ERROR_TOLERANCE = 1.0e-12

BASE_DIR = Path(__file__).resolve().parent

RESULTS_DIR = (
    BASE_DIR /
    "results"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    RESULTS_DIR /
    "qflpn_scaling_python.csv"
)


def rotation_parameters(mu: float):
    theta = (
        2.0 *
        math.asin(
            math.sqrt(mu)
        )
    )

    c = math.cos(theta)
    s = math.sin(theta)

    return theta, c, s


def build_operator(
    qubits: int,
    mu: float
) -> csr_matrix:

    states = 2 ** qubits

    theta, c, s = rotation_parameters(mu)

    del theta

    rows = []
    cols = []
    values = []

    for k in range(
        0,
        states,
        2
    ):

        i = k
        j = k + 1

        rows.extend(
            [
                i,
                i,
                j,
                j
            ]
        )

        cols.extend(
            [
                i,
                j,
                i,
                j
            ]
        )

        values.extend(
            [
                c,
                -s,
                s,
                c
            ]
        )

    return csr_matrix(
        (
            values,
            (
                rows,
                cols
            )
        ),
        shape=(
            states,
            states
        ),
        dtype=np.float64
    )


def build_initial_state(
    states: int
) -> np.ndarray:

    index = np.arange(
        states,
        dtype=np.float64
    )

    x = (
        np.sin(index)
        +
        0.5 *
        np.cos(
            0.37 * index
        )
    )

    norm = np.linalg.norm(
        x,
        ord=2
    )

    if norm == 0.0:
        raise ValueError(
            "Initial state has zero norm."
        )

    return x / norm


def analytical_reference(
    x: np.ndarray,
    mu: float
) -> np.ndarray:

    theta, c, s = (
        rotation_parameters(mu)
    )

    del theta

    y = np.empty_like(x)

    y[0::2] = (
        c * x[0::2]
        -
        s * x[1::2]
    )

    y[1::2] = (
        s * x[0::2]
        +
        c * x[1::2]
    )

    return y


def measure_spmv(
    operator: csr_matrix,
    x: np.ndarray
) -> np.ndarray:

    for _ in range(WARMUP):
        operator @ x

    times_ms = np.empty(
        REPETITIONS,
        dtype=np.float64
    )

    for repetition in range(
        REPETITIONS
    ):

        start = (
            time.perf_counter_ns()
        )

        operator @ x

        end = (
            time.perf_counter_ns()
        )

        times_ms[repetition] = (
            end - start
        ) / 1_000_000.0

    return times_ms


def benchmark_qubit_level(
    qubits: int
) -> dict:

    states = 2 ** qubits

    construction_start = (
        time.perf_counter_ns()
    )

    operator = build_operator(
        qubits,
        MU
    )

    construction_end = (
        time.perf_counter_ns()
    )

    construction_ms = (
        construction_end
        -
        construction_start
    ) / 1_000_000.0

    x = build_initial_state(
        states
    )

    reference = (
        analytical_reference(
            x,
            MU
        )
    )

    computed = (
        operator @ x
    )

    max_absolute_error = float(
        np.max(
            np.abs(
                computed -
                reference
            )
        )
    )

    input_norm = float(
        np.linalg.norm(
            x,
            ord=2
        )
    )

    output_norm = float(
        np.linalg.norm(
            computed,
            ord=2
        )
    )

    norm_error = abs(
        output_norm -
        input_norm
    )

    measurements = (
        measure_spmv(
            operator,
            x
        )
    )

    mean_ms = float(
        np.mean(
            measurements
        )
    )

    median_ms = float(
        np.median(
            measurements
        )
    )

    min_ms = float(
        np.min(
            measurements
        )
    )

    max_ms = float(
        np.max(
            measurements
        )
    )

    numerical_status = (
        "PASS"
        if (
            max_absolute_error
            <= ERROR_TOLERANCE
            and
            norm_error
            <= ERROR_TOLERANCE
        )
        else
        "FAIL"
    )

    timing_status = (
        "PASS"
        if mean_ms <= TARGET_MS
        else
        "FAIL"
    )

    return {
        "language": "Python",
        "qubits": qubits,
        "states": states,
        "nnz": int(
            operator.nnz
        ),
        "mu": MU,
        "warmup": WARMUP,
        "repetitions": REPETITIONS,
        "construction_ms":
            construction_ms,
        "mean_ms":
            mean_ms,
        "median_ms":
            median_ms,
        "min_ms":
            min_ms,
        "max_ms":
            max_ms,
        "maximum_error":
            max_absolute_error,
        "input_norm":
            input_norm,
        "output_norm":
            output_norm,
        "norm_error":
            norm_error,
        "target_ms":
            TARGET_MS,
        "numerical_status":
            numerical_status,
        "timing_status":
            timing_status
    }


def environment_information():

    return {
        "python_version":
            sys.version.split()[0],

        "numpy_version":
            np.__version__,

        "platform":
            platform.platform(),

        "processor":
            platform.processor()
    }


def save_results(
    results: list[dict]
) -> None:

    fieldnames = [
        "language",
        "qubits",
        "states",
        "nnz",
        "mu",
        "warmup",
        "repetitions",
        "construction_ms",
        "mean_ms",
        "median_ms",
        "min_ms",
        "max_ms",
        "maximum_error",
        "input_norm",
        "output_norm",
        "norm_error",
        "target_ms",
        "numerical_status",
        "timing_status"
    ]

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


def main():

    print(
        "QFLPN scaling benchmark"
    )

    print(
        f"Qubits: "
        f"{MIN_QUBITS} ... "
        f"{MAX_QUBITS}"
    )

    print(
        "States: 2^q"
    )

    print(
        f"mu = {MU}"
    )

    print(
        f"Warmup: {WARMUP}"
    )

    print(
        f"Repetitions: "
        f"{REPETITIONS}"
    )

    print(
        f"Target: "
        f"{TARGET_MS:.3f} ms"
    )

    print()

    environment = (
        environment_information()
    )

    print(
        "Python:",
        environment[
            "python_version"
        ]
    )

    print(
        "NumPy:",
        environment[
            "numpy_version"
        ]
    )

    print(
        "Platform:",
        environment[
            "platform"
        ]
    )

    print()

    results = []

    for qubits in range(
        MIN_QUBITS,
        MAX_QUBITS + 1
    ):

        states = 2 ** qubits

        print(
            f"Running q={qubits}, "
            f"N={states:,}"
        )

        result = (
            benchmark_qubit_level(
                qubits
            )
        )

        results.append(
            result
        )

        print(
            f"  NNZ: "
            f"{result['nnz']:,}"
        )

        print(
            f"  Mean: "
            f"{result['mean_ms']:.6f} ms"
        )

        print(
            f"  Median: "
            f"{result['median_ms']:.6f} ms"
        )

        print(
            f"  Maximum error: "
            f"{result['maximum_error']:.3e}"
        )

        print(
            f"  Norm error: "
            f"{result['norm_error']:.3e}"
        )

        print(
            f"  Numerical: "
            f"{result['numerical_status']}"
        )

        print(
            f"  Timing: "
            f"{result['timing_status']}"
        )

        print()

    save_results(
        results
    )

    print(
        "Results saved to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()