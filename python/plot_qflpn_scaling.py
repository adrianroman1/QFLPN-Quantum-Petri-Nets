#!/usr/bin/env python3

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


# ============================================================
# QFLPN SCALING COMPARISON FIGURE
# ============================================================
#
# Reads:
#     python/results/qflpn_scaling_python.csv
#     matlab/results/qflpn_scaling_matlab.csv
#
# Expected qubit range:
#     q = 4 ... 17
#
# Expected state dimensions:
#     N = 2^q
#
# Output:
#     python/results/qflpn_scaling_comparison.png
#
# ============================================================


ROOT = Path(__file__).resolve().parents[1]

PYTHON_RESULTS = (
    ROOT
    / "python"
    / "results"
    / "qflpn_scaling_python.csv"
)

MATLAB_RESULTS = (
    ROOT
    / "matlab"
    / "results"
    / "qflpn_scaling_matlab.csv"
)

OUTPUT_FILE = (
    ROOT
    / "python"
    / "results"
    / "qflpn_scaling_comparison.png"
)

EXPECTED_QUBITS = list(range(4, 18))

TARGET_MS = 15.0


# ------------------------------------------------------------
# CSV reader
# ------------------------------------------------------------

def read_results(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Results file does not exist:\n{path}"
        )

    if path.stat().st_size == 0:
        raise ValueError(
            f"Results file is empty:\n{path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        reader = csv.DictReader(csv_file)
        rows = list(reader)

    if not rows:
        raise ValueError(
            f"Results file contains no data rows:\n{path}"
        )

    required_columns = {
        "qubits",
        "states",
        "mean_spmv_ms",
        "median_spmv_ms",
        "maximum_error",
        "norm_error",
    }

    missing = required_columns.difference(
        reader.fieldnames or []
    )

    if missing:
        raise ValueError(
            f"Missing columns in {path}:\n"
            f"{sorted(missing)}"
        )

    return rows


# ------------------------------------------------------------
# Validation of dimensions
# ------------------------------------------------------------

def validate_scaling_rows(
    rows: list[dict[str, str]],
    label: str,
) -> None:

    qubits = [
        int(row["qubits"])
        for row in rows
    ]

    states = [
        int(row["states"])
        for row in rows
    ]

    expected_states = [
        2 ** q
        for q in EXPECTED_QUBITS
    ]

    if qubits != EXPECTED_QUBITS:
        raise ValueError(
            f"{label}: unexpected qubit sequence.\n"
            f"Expected: {EXPECTED_QUBITS}\n"
            f"Received: {qubits}"
        )

    if states != expected_states:
        raise ValueError(
            f"{label}: state dimensions do not equal 2^q.\n"
            f"Expected: {expected_states}\n"
            f"Received: {states}"
        )


# ------------------------------------------------------------
# Numeric conversion
# ------------------------------------------------------------

def extract_values(
    rows: list[dict[str, str]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:

    qubits = np.array(
        [int(row["qubits"]) for row in rows],
        dtype=np.int32,
    )

    states = np.array(
        [int(row["states"]) for row in rows],
        dtype=np.int64,
    )

    mean_ms = np.array(
        [
            float(row["mean_spmv_ms"])
            for row in rows
        ],
        dtype=np.float64,
    )

    median_ms = np.array(
        [
            float(row["median_spmv_ms"])
            for row in rows
        ],
        dtype=np.float64,
    )

    return qubits, states, mean_ms, median_ms


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main() -> None:

    print("=" * 72)
    print("QFLPN SCALING COMPARISON")
    print("=" * 72)

    python_rows = read_results(PYTHON_RESULTS)
    matlab_rows = read_results(MATLAB_RESULTS)

    validate_scaling_rows(
        python_rows,
        "Python",
    )

    validate_scaling_rows(
        matlab_rows,
        "MATLAB",
    )

    (
        python_q,
        python_states,
        python_mean,
        python_median,
    ) = extract_values(python_rows)

    (
        matlab_q,
        matlab_states,
        matlab_mean,
        matlab_median,
    ) = extract_values(matlab_rows)

    if not np.array_equal(
        python_q,
        matlab_q,
    ):
        raise ValueError(
            "Python and MATLAB qubit dimensions differ."
        )

    if not np.array_equal(
        python_states,
        matlab_states,
    ):
        raise ValueError(
            "Python and MATLAB state dimensions differ."
        )

    # --------------------------------------------------------
    # Figure
    # --------------------------------------------------------

    figure, axis = plt.subplots(
        figsize=(11, 7)
    )

    axis.plot(
        python_q,
        python_mean,
        marker="o",
        linewidth=2,
        label="Python — mean SpMV",
    )

    axis.plot(
        matlab_q,
        matlab_mean,
        marker="s",
        linewidth=2,
        label="MATLAB — mean SpMV",
    )

    axis.axhline(
        TARGET_MS,
        linestyle="--",
        linewidth=1.5,
        label=f"Target = {TARGET_MS:.1f} ms",
    )

    axis.set_xlabel(
        "Number of qubits"
    )

    axis.set_ylabel(
        "Mean sparse operator execution time (ms)"
    )

    axis.set_title(
        "QFLPN Sparse Operator Scaling: 4–17 Qubits"
    )

    axis.set_xticks(
        EXPECTED_QUBITS
    )

    axis.grid(
        True,
        which="both",
        linestyle=":",
        linewidth=0.8,
    )

    axis.legend()

    # State dimensions are shown on a secondary x-axis.
    secondary = axis.secondary_xaxis(
        "top"
    )

    secondary.set_xticks(
        EXPECTED_QUBITS
    )

    secondary.set_xticklabels(
        [
            f"{2 ** q:,}"
            for q in EXPECTED_QUBITS
        ],
        rotation=45,
        ha="left",
    )

    secondary.set_xlabel(
        "State-space dimension N = 2^q"
    )

    figure.tight_layout()

    figure.savefig(
        OUTPUT_FILE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print("\nScaling dimensions:")
    print("-" * 72)

    for index, q in enumerate(EXPECTED_QUBITS):

        print(
            f"q={q:2d} | "
            f"N={2 ** q:7d} | "
            f"Python={python_mean[index]:.6f} ms | "
            f"MATLAB={matlab_mean[index]:.6f} ms"
        )

    print("-" * 72)

    print(
        f"\nFigure written to:\n{OUTPUT_FILE}"
    )

    print("=" * 72)


if __name__ == "__main__":
    main()