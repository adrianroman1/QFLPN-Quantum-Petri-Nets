import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parent

RESULTS_DIR = (
    BASE_DIR / "results"
)

PYTHON_FILE = (
    RESULTS_DIR /
    "qflpn_scaling_python.csv"
)

MATLAB_FILE = (
    RESULTS_DIR /
    "qflpn_scaling_matlab.csv"
)

OUTPUT_FILE = (
    RESULTS_DIR /
    "qflpn_scaling_comparison.png"
)


def read_csv(filename):

    with filename.open(
        "r",
        encoding="utf-8"
    ) as file:

        return list(
            csv.DictReader(file)
        )


def main():

    python_results = read_csv(
        PYTHON_FILE
    )

    matlab_results = read_csv(
        MATLAB_FILE
    )

    python_dimensions = np.array(
        [
            int(row["dimension"])
            for row in python_results
        ]
    )

    python_times = np.array(
        [
            float(row["mean_ms"])
            for row in python_results
        ]
    )

    matlab_dimensions = np.array(
        [
            int(row["dimension"])
            for row in matlab_results
        ]
    )

    matlab_times = np.array(
        [
            float(row["mean_ms"])
            for row in matlab_results
        ]
    )

    figure = plt.figure(
        figsize=(9, 6)
    )

    plt.plot(
        python_dimensions,
        python_times,
        marker="o",
        label="Python"
    )

    plt.plot(
        matlab_dimensions,
        matlab_times,
        marker="s",
        label="MATLAB"
    )

    plt.axhline(
        15.0,
        linestyle="--",
        label="Target = 15 ms"
    )

    plt.xscale("log")

    plt.xlabel(
        "State-space dimension N"
    )

    plt.ylabel(
        "Mean SpMV execution time (ms)"
    )

    plt.title(
        "QFLPN Sparse Operator Scaling"
    )

    plt.xticks(
        [1024, 10000, 100000],
        ["1,024", "10,000", "100,000"]
    )

    plt.grid(
        True,
        which="both",
        alpha=0.25
    )

    plt.legend()

    plt.tight_layout()

    figure.savefig(
        OUTPUT_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(figure)

    print(
        f"Figure saved to:\n{OUTPUT_FILE}"
    )

    print()
    print(
        "Dimension | Python mean (ms) | "
        "MATLAB mean (ms)"
    )

    print(
        "------------------------------------------------"
    )

    for n in python_dimensions:

        python_value = python_times[
            python_dimensions == n
        ][0]

        matlab_value = matlab_times[
            matlab_dimensions == n
        ][0]

        print(
            f"{n:9d} | "
            f"{python_value:16.6f} | "
            f"{matlab_value:16.6f}"
        )


if __name__ == "__main__":
    main()