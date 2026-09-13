#!/usr/bin/env python3

import csv
import os

import matplotlib.pyplot as plt
import numpy as np


PYTHON_FILE = os.path.join(
    "python",
    "results",
    "qflpn_krylov_arnoldi_python.csv",
)

MATLAB_FILE = os.path.join(
    "matlab",
    "results",
    "qflpn_krylov_arnoldi_matlab.csv",
)

OUTPUT_DIR = os.path.join(
    "python",
    "figures",
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "qflpn_krylov_arnoldi_comparison.png",
)


def read_csv(filename: str) -> dict:
    with open(
        filename,
        "r",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        rows = list(csv.DictReader(csv_file))

    if not rows:
        raise ValueError(f"Empty CSV file: {filename}")

    q = np.asarray(
        [int(row["qubits"]) for row in rows],
        dtype=np.int64,
    )

    states = np.asarray(
        [int(row["states"]) for row in rows],
        dtype=np.int64,
    )

    mean_ms = np.asarray(
        [float(row["mean_arnoldi_ms"]) for row in rows],
        dtype=np.float64,
    )

    median_ms = np.asarray(
        [float(row["median_arnoldi_ms"]) for row in rows],
        dtype=np.float64,
    )

    effective_dimension = np.asarray(
        [
            int(row["effective_krylov_dimension"])
            for row in rows
        ],
        dtype=np.int64,
    )

    target_ms = float(rows[0]["target_ms"])

    return {
        "q": q,
        "states": states,
        "mean_ms": mean_ms,
        "median_ms": median_ms,
        "effective_dimension": effective_dimension,
        "target_ms": target_ms,
    }


def validate_structure(
    python_data: dict,
    matlab_data: dict,
) -> None:

    expected_q = np.arange(4, 18, dtype=np.int64)
    expected_states = 2 ** expected_q

    if not np.array_equal(
        python_data["q"],
        expected_q,
    ):
        raise ValueError(
            "Python CSV does not contain q=4...17."
        )

    if not np.array_equal(
        matlab_data["q"],
        expected_q,
    ):
        raise ValueError(
            "MATLAB CSV does not contain q=4...17."
        )

    if not np.array_equal(
        python_data["states"],
        expected_states,
    ):
        raise ValueError(
            "Python state counts are not 2^q."
        )

    if not np.array_equal(
        matlab_data["states"],
        expected_states,
    ):
        raise ValueError(
            "MATLAB state counts are not 2^q."
        )


def main() -> None:

    python_data = read_csv(PYTHON_FILE)
    matlab_data = read_csv(MATLAB_FILE)

    validate_structure(
        python_data,
        matlab_data,
    )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True,
    )

    q = python_data["q"]

    target_ms = python_data["target_ms"]

    if not np.isclose(
        target_ms,
        matlab_data["target_ms"],
    ):
        raise ValueError(
            "Python and MATLAB target thresholds differ."
        )

    plt.figure(figsize=(11, 7))

    plt.plot(
        q,
        python_data["mean_ms"],
        marker="o",
        linewidth=2.0,
        label="Python",
    )

    plt.plot(
        q,
        matlab_data["mean_ms"],
        marker="s",
        linewidth=2.0,
        label="MATLAB / Octave",
    )

    plt.axhline(
        target_ms,
        linestyle="--",
        linewidth=1.5,
        label=f"Operational threshold = {target_ms:g} ms",
    )

    for index in range(len(q)):
        plt.annotate(
            f"N={python_data['states'][index]:,}",
            (
                q[index],
                python_data["mean_ms"][index],
            ),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            fontsize=7,
        )

    plt.xlabel("Qubits (q)")
    plt.ylabel("Mean Arnoldi execution time (ms)")
    plt.title(
        "QFLPN Krylov–Arnoldi: Python vs MATLAB / Octave"
    )

    plt.xticks(q)
    plt.grid(True, alpha=0.25)
    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUTPUT_FILE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close()

    print(f"Figure output: {OUTPUT_FILE}")

    print()
    print("QFLPN KRYLOV-ARNOLDI COMPARISON")
    print("-" * 72)
    print(
        f"{'q':>3} "
        f"{'states':>8} "
        f"{'Python ms':>14} "
        f"{'MATLAB ms':>14} "
        f"{'K(Py)':>7} "
        f"{'K(Mat)':>7}"
    )
    print("-" * 72)

    for index in range(len(q)):
        print(
            f"{q[index]:3d} "
            f"{python_data['states'][index]:8d} "
            f"{python_data['mean_ms'][index]:14.6f} "
            f"{matlab_data['mean_ms'][index]:14.6f} "
            f"{python_data['effective_dimension'][index]:7d} "
            f"{matlab_data['effective_dimension'][index]:7d}"
        )


if __name__ == "__main__":
    main()
