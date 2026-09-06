import csv
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix


DIMENSIONS = [1024, 10_000, 100_000]

MU = 0.70

WARMUP = 20
REPETITIONS = 1000

TARGET_MS = 15.0
ERROR_TOLERANCE = 1e-12


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    RESULTS_DIR /
    "qflpn_scaling_python.csv"
)


def build_qflpn_operator(n, mu):

    theta = 2.0 * math.asin(
        math.sqrt(mu)
    )

    c = math.cos(theta)
    s = math.sin(theta)

    rows = []
    cols = []
    values = []

    for k in range(0, n, 2):

        i = k
        j = k + 1

        rows.extend(
            [i, i, j, j]
        )

        cols.extend(
            [i, j, i, j]
        )

        values.extend(
            [c, -s, s, c]
        )

    return csr_matrix(
        (
            values,
            (rows, cols)
        ),
        shape=(n, n),
        dtype=np.float64
    )


def build_initial_state(n):

    index = np.arange(
        n,
        dtype=np.float64
    )

    x = (
        np.sin(index)
        +
        0.5 * np.cos(
            0.37 * index
        )
    )

    norm = np.linalg.norm(x)

    if norm == 0.0:
        raise RuntimeError(
            "Initial state has zero norm."
        )

    return x / norm


def analytical_reference(x, mu):

    theta = 2.0 * math.asin(
        math.sqrt(mu)
    )

    c = math.cos(theta)
    s = math.sin(theta)

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


def benchmark(operator, x):

    for _ in range(WARMUP):
        operator @ x

    measurements = []

    for _ in range(REPETITIONS):

        start = time.perf_counter_ns()

        operator @ x

        end = time.perf_counter_ns()

        elapsed_ms = (
            end - start
        ) / 1_000_000.0

        measurements.append(
            elapsed_ms
        )

    return np.asarray(
        measurements,
        dtype=np.float64
    )


def run_dimension(n):

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
        construction_end
        -
        construction_start
    ) / 1_000_000.0

    x = build_initial_state(n)

    reference = analytical_reference(
        x,
        MU
    )

    computed = operator @ x

    max_absolute_error = float(
        np.max(
            np.abs(
                computed - reference
            )
        )
    )

    input_norm = float(
        np.linalg.norm(x)
    )

    output_norm = float(
        np.linalg.norm(computed)
    )

    norm_error = abs(
        output_norm -
        input_norm
    )

    measurements = benchmark(
        operator,
        x
    )

    mean_ms = float(
        np.mean(measurements)
    )

    median_ms = float(
        np.median(measurements)
    )

    min_ms = float(
        np.min(measurements)
    )

    max_ms = float(
        np.max(measurements)
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
        "dimension": n,
        "nnz": int(operator.nnz),
        "density_percent": (
            100.0 *
            operator.nnz /
            (n * n)
        ),
        "mu": MU,
        "warmup": WARMUP,
        "repetitions": REPETITIONS,
        "construction_ms": construction_ms,
        "mean_ms": mean_ms,
        "median_ms": median_ms,
        "min_ms": min_ms,
        "max_ms": max_ms,
        "max_absolute_error":
            max_absolute_error,
        "input_norm": input_norm,
        "output_norm": output_norm,
        "norm_error": norm_error,
        "target_ms": TARGET_MS,
        "error_tolerance":
            ERROR_TOLERANCE,
        "numerical_status":
            numerical_status,
        "timing_status":
            timing_status
    }


def get_environment():

    return {
        "python_version":
            sys.version.split()[0],

        "numpy_version":
            np.__version__,

        "scipy_version":
            __import__(
                "scipy"
            ).__version__,

        "platform":
            platform.platform(),

        "processor":
            platform.processor()
    }


def save_results(results):

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


def main():

    print(
        "QFLPN Scaling Benchmark"
    )

    print(
        "Dimensions:",
        DIMENSIONS
    )

    print(
        f"Warmup: {WARMUP}"
    )

    print(
        f"Repetitions: {REPETITIONS}"
    )

    print()

    environment = get_environment()

    print(
        f"Python: "
        f"{environment['python_version']}"
    )

    print(
        f"NumPy: "
        f"{environment['numpy_version']}"
    )

    print(
        f"SciPy: "
        f"{environment['scipy_version']}"
    )

    print(
        f"Platform: "
        f"{environment['platform']}"
    )

    print()

    results = []

    for n in DIMENSIONS:

        print(
            f"Running N={n:,}"
        )

        result = run_dimension(n)

        results.append(result)

        print(
            f"  NNZ: "
            f"{result['nnz']:,}"
        )

        print(
            f"  Construction: "
            f"{result['construction_ms']:.6f} ms"
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
            f"  Min: "
            f"{result['min_ms']:.6f} ms"
        )

        print(
            f"  Max: "
            f"{result['max_ms']:.6f} ms"
        )

        print(
            f"  Maximum error: "
            f"{result['max_absolute_error']:.3e}"
        )

        print(
            f"  Norm error: "
            f"{result['norm_error']:.3e}"
        )

        print(
            f"  Numerical status: "
            f"{result['numerical_status']}"
        )

        print(
            f"  Timing status: "
            f"{result['timing_status']}"
        )

        print()

    save_results(results)

    print(
        "Results saved to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()