import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

PYTHON_FILE = (
    RESULTS /
    "qflpn_operator_validation_python.csv"
)

MATLAB_FILE = (
    RESULTS /
    "qflpn_operator_validation_matlab.csv"
)

OUTPUT_PNG = (
    RESULTS /
    "qflpn_operator_scaling_comparison.png"
)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8"
    ) as f:
        return list(csv.DictReader(f))


def main():

    python_data = read_csv(PYTHON_FILE)
    matlab_data = read_csv(MATLAB_FILE)

    py_n = np.array(
        [int(r["dimension"]) for r in python_data]
    )

    py_time = np.array(
        [float(r["mean_ms"]) for r in python_data]
    )

    matlab_n = np.array(
        [int(r["dimension"]) for r in matlab_data]
    )

    matlab_time = np.array(
        [float(r["mean_ms"]) for r in matlab_data]
    )

    plt.figure(figsize=(9, 6))

    plt.plot(
        py_n,
        py_time,
        marker="o",
        label="Python"
    )

    plt.plot(
        matlab_n,
        matlab_time,
        marker="s",
        label="MATLAB"
    )

    plt.axhline(
        15.0,
        linestyle="--",
        label="Target = 15 ms"
    )

    plt.xscale("log")

    plt.xlabel("State-space dimension N")
    plt.ylabel("Mean SpMV execution time (ms)")

    plt.title(
        "QFLPN Sparse Operator Scaling"
    )

    plt.grid(True, which="both", alpha=0.25)
    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUTPUT_PNG,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print(f"Saved: {OUTPUT_PNG}")

    print()
    print("Dimension | Python ms | MATLAB ms")
    print("----------------------------------")

    for n in py_n:

        py = py_time[py_n == n][0]
        ml = matlab_time[matlab_n == n][0]

        print(
            f"{n:9d} | "
            f"{py:10.6f} | "
            f"{ml:10.6f}"
        )


if __name__ == "__main__":
    main()
