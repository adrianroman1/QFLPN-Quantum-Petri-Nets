import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


# ============================================================
# QFLPN SCALING COMPARISON FIGURE
# ============================================================
#
# This script compares the deterministic sparse QFLPN operator
# scaling results produced by:
#
#   1. Python / SciPy CSR SpMV
#   2. MATLAB-compatible / GNU Octave sparse SpMV
#
# State-space dimensions:
#
#   N = 1,024
#   N = 10,000
#   N = 100,000
#
# IMPORTANT:
#   These are state-space dimensions, NOT qubit counts.
#   Only N = 1,024 corresponds to 10 qubits.
#
# No random sampling is used.
# No Monte Carlo method is used.
#
# ============================================================


# ------------------------------------------------------------
# Repository directories
# ------------------------------------------------------------

PYTHON_DIR = Path(__file__).resolve().parent
REPOSITORY_DIR = PYTHON_DIR.parent

PYTHON_RESULTS_DIR = (
    PYTHON_DIR /
    "results"
)

MATLAB_RESULTS_DIR = (
    REPOSITORY_DIR /
    "matlab" /
    "results"
)


# ------------------------------------------------------------
# Input files
# ------------------------------------------------------------

PYTHON_FILE = (
    PYTHON_RESULTS_DIR /
    "qflpn_scaling_python.csv"
)

MATLAB_FILE = (
    MATLAB_RESULTS_DIR /
    "qflpn_scaling_matlab.csv"
)


# ------------------------------------------------------------
# Output file
# ------------------------------------------------------------

OUTPUT_FILE = (
    PYTHON_RESULTS_DIR /
    "qflpn_scaling_comparison.png"
)


# ------------------------------------------------------------
# Benchmark dimensions
# ------------------------------------------------------------

EXPECTED_DIMENSIONS = [
    1024,
    10_000,
    100_000
]


# ------------------------------------------------------------
# Target
# ------------------------------------------------------------

TARGET_MS = 15.0


# ------------------------------------------------------------
# CSV reader
# ------------------------------------------------------------

def read_csv(filename: Path) -> list[dict]:

    if not filename.exists():

        raise FileNotFoundError(
            "\nRequired result file was not found.\n"
            f"Expected path:\n{filename}\n\n"
            "Check that the corresponding benchmark job "
            "completed successfully and that the artifact "
            "was downloaded to the expected directory."
        )

    with filename.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        rows = list(
            csv.DictReader(file)
        )

    if not rows:

        raise ValueError(
            f"CSV file is empty:\n{filename}"
        )

    required_columns = {
        "dimension",
        "mean_ms"
    }

    available_columns = set(
        rows[0].keys()
    )

    missing_columns = (
        required_columns -
        available_columns
    )

    if missing_columns:

        raise ValueError(
            f"CSV file is missing required columns "
            f"{sorted(missing_columns)}:\n{filename}"
        )

    return rows


# ------------------------------------------------------------
# Convert CSV rows to numerical arrays
# ------------------------------------------------------------

def extract_results(
    rows: list[dict],
    source_name: str
) -> tuple[np.ndarray, np.ndarray]:

    dimensions = np.array(
        [
            int(row["dimension"])
            for row in rows
        ],
        dtype=np.int64
    )

    mean_times = np.array(
        [
            float(row["mean_ms"])
            for row in rows
        ],
        dtype=np.float64
    )

    if len(dimensions) != len(EXPECTED_DIMENSIONS):

        raise ValueError(
            f"{source_name} contains "
            f"{len(dimensions)} dimensions, but "
            f"{len(EXPECTED_DIMENSIONS)} were expected."
        )

    if not np.array_equal(
        dimensions,
        np.array(
            EXPECTED_DIMENSIONS,
            dtype=np.int64
        )
    ):

        raise ValueError(
            f"{source_name} dimensions are incorrect.\n"
            f"Expected: {EXPECTED_DIMENSIONS}\n"
            f"Received: {dimensions.tolist()}"
        )

    if not np.all(
        np.isfinite(mean_times)
    ):

        raise ValueError(
            f"{source_name} contains non-finite "
            "mean execution times."
        )

    return dimensions, mean_times


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main() -> None:

    print(
        "=============================================="
    )
    print(
        "QFLPN SCALING COMPARISON"
    )
    print(
        "=============================================="
    )

    print()
    print(
        "Repository directory:"
    )
    print(
        REPOSITORY_DIR
    )

    print()
    print(
        "Python result:"
    )
    print(
        PYTHON_FILE
    )

    print()
    print(
        "MATLAB-compatible result:"
    )
    print(
        MATLAB_FILE
    )

    print()

    # --------------------------------------------------------
    # Read benchmark results
    # --------------------------------------------------------

    python_rows = read_csv(
        PYTHON_FILE
    )

    matlab_rows = read_csv(
        MATLAB_FILE
    )

    # --------------------------------------------------------
    # Extract numerical data
    # --------------------------------------------------------

    python_dimensions, python_times = (
        extract_results(
            python_rows,
            "Python"
        )
    )

    matlab_dimensions, matlab_times = (
        extract_results(
            matlab_rows,
            "MATLAB-compatible"
        )
    )

    # --------------------------------------------------------
    # Verify identical dimensions
    # --------------------------------------------------------

    if not np.array_equal(
        python_dimensions,
        matlab_dimensions
    ):

        raise ValueError(
            "Python and MATLAB-compatible results "
            "use different state-space dimensions."
        )

    dimensions = python_dimensions

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    PYTHON_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Create comparison figure
    # --------------------------------------------------------

    figure = plt.figure(
        figsize=(10, 6)
    )

    plt.plot(
        dimensions,
        python_times,
        marker="o",
        linewidth=1.5,
        label="Python / SciPy CSR"
    )

    plt.plot(
        dimensions,
        matlab_times,
        marker="s",
        linewidth=1.5,
        label="MATLAB-compatible / Octave"
    )

    plt.axhline(
        TARGET_MS,
        linestyle="--",
        linewidth=1.2,
        label="Target = 15 ms"
    )

    # --------------------------------------------------------
    # Logarithmic state-space dimension axis
    # --------------------------------------------------------

    plt.xscale(
        "log"
    )

    plt.xticks(
        dimensions,
        [
            "1,024",
            "10,000",
            "100,000"
        ]
    )

    # --------------------------------------------------------
    # Axis labels
    # --------------------------------------------------------

    plt.xlabel(
        "State-space dimension N"
    )

    plt.ylabel(
        "Mean SpMV execution time (ms)"
    )

    plt.title(
        "QFLPN Deterministic Sparse Operator Scaling"
    )

    # --------------------------------------------------------
    # Grid and legend
    # --------------------------------------------------------

    plt.grid(
        True,
        which="both",
        alpha=0.25
    )

    plt.legend()

    # --------------------------------------------------------
    # Layout
    # --------------------------------------------------------

    plt.tight_layout()

    # --------------------------------------------------------
    # Save figure
    # --------------------------------------------------------

    figure.savefig(
        OUTPUT_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(
        figure
    )

    # --------------------------------------------------------
    # Console report
    # --------------------------------------------------------

    print(
        "Figure generated successfully."
    )

    print()
    print(
        "Output:"
    )
    print(
        OUTPUT_FILE
    )

    print()
    print(
        "------------------------------------------------"
    )

    print(
        "Dimension | Python mean (ms) | "
        "MATLAB-compatible mean (ms)"
    )

    print(
        "------------------------------------------------"
    )

    for index in range(
        len(dimensions)
    ):

        n = int(
            dimensions[index]
        )

        python_value = float(
            python_times[index]
        )

        matlab_value = float(
            matlab_times[index]
        )

        print(
            f"{n:9d} | "
            f"{python_value:16.6f} | "
            f"{matlab_value:26.6f}"
        )

    print(
        "------------------------------------------------"
    )

    print()
    print(
        "Target threshold:"
    )
    print(
        f"{TARGET_MS:.3f} ms"
    )

    print()
    print(
        "Comparison completed successfully."
    )


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------

if __name__ == "__main__":
    main()