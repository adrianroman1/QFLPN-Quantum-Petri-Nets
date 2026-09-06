"""
QFLPN Results Plot
==================

Creates thesis-ready benchmark figures from measured CSV files.

Input:
    qflpn_python_results.csv
    qflpn_matlab_results.csv   (when available)

Output:
    qflpn_execution_time.png
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


PYTHON_FILE = Path("qflpn_python_results.csv")
MATLAB_FILE = Path("qflpn_matlab_results.csv")
OUTPUT_FILE = Path("qflpn_execution_time.png")


def read_result(path: Path):
    if not path.exists():
        return None

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        rows = list(csv.DictReader(file))

    if not rows:
        return None

    row = rows[0]

    return {
        "language": row["language"],
        "mean_total_ms": float(row["mean_total_ms"]),
        "target_ms": float(row["target_ms"]),
    }


def main() -> None:

    results = []

    python_result = read_result(PYTHON_FILE)
    matlab_result = read_result(MATLAB_FILE)

    if python_result is not None:
        results.append(python_result)

    if matlab_result is not None:
        results.append(matlab_result)

    if not results:
        raise FileNotFoundError(
            "No benchmark CSV files were found."
        )

    labels = [
        result["language"]
        for result in results
    ]

    values = [
        result["mean_total_ms"]
        for result in results
    ]

    target = results[0]["target_ms"]

    plt.figure(figsize=(8, 5))

    bars = plt.bar(labels, values)

    plt.axhline(
        target,
        linestyle="--",
        linewidth=1.5,
        label=f"Target = {target:.1f} ms",
    )

    plt.ylabel("Mean execution time (ms)")
    plt.xlabel("Implementation")
    plt.title(
        "QFLPN 4-Qubit Mean Execution Time"
    )

    for bar, value in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.4f} ms",
            ha="center",
            va="bottom",
        )

    plt.legend()
    plt.tight_layout()

    plt.savefig(
        OUTPUT_FILE,
        dpi=300,
        bbox_inches="tight",
    )

    print("=" * 64)
    print("QFLPN BENCHMARK FIGURE")
    print("=" * 64)

    for result in results:
        print(
            f"{result['language']}: "
            f"{result['mean_total_ms']:.6f} ms"
        )

    print(f"\nTarget: {target:.3f} ms")
    print(f"PNG exported: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
