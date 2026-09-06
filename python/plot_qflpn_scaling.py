"""
QFLPN Python/MATLAB scaling plot
================================

Reads:

    results/scaling/qflpn_python_scaling_results.csv
    results/scaling/qflpn_matlab_scaling_results.csv

Creates:

    results/scaling/qflpn_python_matlab_scaling.png

The figure compares mean execution time for:

    1,024
    10,000
    100,000

state-vector dimensions.

The 15 ms target is displayed explicitly.

No Monte Carlo.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


PYTHON_FILE = Path(
    "results/scaling/qflpn_python_scaling_results.csv"
)

MATLAB_FILE = Path(
    "results/scaling/qflpn_matlab_scaling_results.csv"
)

OUTPUT_FILE = Path(
    "results/scaling/qflpn_python_matlab_scaling.png"
)

TARGET_MS = 15.0


def read_results(
    filename: Path,
) -> dict[str, list]:

    dimensions = []
    mean_ms = []

    with filename.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            dimensions.append(
                int(row["dimension"])
            )

            mean_ms.append(
                float(row["mean_ms"])
            )

    return {
        "dimensions": dimensions,
        "mean_ms": mean_ms,
    }


def main() -> None:

    python = read_results(
        PYTHON_FILE
    )

    matlab = read_results(
        MATLAB_FILE
    )


    # --------------------------------------------------------
    # Plot
    # --------------------------------------------------------

    plt.figure(
        figsize=(9, 6)
    )

    plt.plot(
        python["dimensions"],
        python["mean_ms"],
        marker="o",
        linewidth=2,
        label="Python",
    )

    plt.plot(
        matlab["dimensions"],
        matlab["mean_ms"],
        marker="s",
        linewidth=2,
        label="MATLAB",
    )

    plt.axhline(
        TARGET_MS,
        linestyle="--",
        linewidth=1.5,
        label="Target = 15 ms",
    )


    # --------------------------------------------------------
    # Axes
    # --------------------------------------------------------

    plt.xscale(
        "log"
    )

    plt.xlabel(
        "State-vector dimension"
    )

    plt.ylabel(
        "Mean execution time (ms)"
    )

    plt.title(
        "QFLPN Python/MATLAB Scaling: "
        "1,024–100,000 States"
    )


    plt.grid(
        True,
        which="both",
        alpha=0.25,
    )

    plt.legend()

    plt.tight_layout()


    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        OUTPUT_FILE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close()


    print(
        f"Figure exported: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":

    main()
