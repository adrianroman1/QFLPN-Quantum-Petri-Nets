import csv
from pathlib import Path

import matplotlib.pyplot as plt


# ============================================================
# QFLPN SCALING COMPARISON FIGURE
#
# Compares deterministic sparse-operator execution times
# for:
#
#       N = 1,024
#       N = 10,000
#       N = 100,000
#
# These are state-space dimensions, not qubit counts.
#
# No Monte Carlo.
# ============================================================


BASE_DIR = (
    Path(__file__).resolve().parent
)


PYTHON_RESULTS = (
    BASE_DIR /
    "results" /
    "qflpn_scaling_python.csv"
)


MATLAB_RESULTS = (
    BASE_DIR.parent /
    "matlab" /
    "results" /
    "qflpn_scaling_matlab.csv"
)


OUTPUT_FIGURE = (
    BASE_DIR /
    "results" /
    "qflpn_scaling_comparison.png"
)


EXPECTED_STATES = [
    1024,
    10000,
    100000,
]


TARGET_MS = 15.0


# ------------------------------------------------------------
# CSV reader
# ------------------------------------------------------------

def read_csv(filename):

    if not filename.exists():

        raise FileNotFoundError(
            "Required results file was not found:\n"
            f"{filename}"
        )

    with filename.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        reader = csv.DictReader(
            file
        )

        rows = list(
            reader
        )

    if not rows:

        raise ValueError(
            "Results file is empty:\n"
            f"{filename}"
        )

    return rows


# ------------------------------------------------------------
# Convert and validate results
# ------------------------------------------------------------

def convert_results(rows, source_name):

    states = []
    mean_ms = []
    median_ms = []
    min_ms = []
    max_ms = []
    numerical_status = []
    timing_status = []

    for row in rows:

        states.append(
            int(
                row["states"]
            )
        )

        mean_ms.append(
            float(
                row["mean_ms"]
            )
        )

        median_ms.append(
            float(
                row["median_ms"]
            )
        )

        min_ms.append(
            float(
                row["min_ms"]
            )
        )

        max_ms.append(
            float(
                row["max_ms"]
            )
        )

        numerical_status.append(
            row["numerical_status"]
        )

        timing_status.append(
            row["timing_status"]
        )

    if states != EXPECTED_STATES:

        raise ValueError(
            f"{source_name} contains unexpected "
            f"state-space dimensions.\n"
            f"Expected: {EXPECTED_STATES}\n"
            f"Obtained: {states}"
        )

    for index in range(
        len(states)
    ):

        if numerical_status[index] != "PASS":

            raise ValueError(
                f"{source_name}: numerical validation "
                f"failed for N={states[index]}."
            )

    return {
        "states": states,
        "mean_ms": mean_ms,
        "median_ms": median_ms,
        "min_ms": min_ms,
        "max_ms": max_ms,
        "numerical_status": numerical_status,
        "timing_status": timing_status,
    }


# ------------------------------------------------------------
# Validate Python/MATLAB consistency
# ------------------------------------------------------------

def validate_consistency(
    python_results,
    matlab_results
):

    if (
        python_results["states"]
        !=
        matlab_results["states"]
    ):

        raise ValueError(
            "Python and MATLAB-compatible results "
            "contain different state-space dimensions."
        )


# ------------------------------------------------------------
# Create figure
# ------------------------------------------------------------

def create_figure(
    python_results,
    matlab_results
):

    states = (
        python_results["states"]
    )

    python_mean = (
        python_results["mean_ms"]
    )

    matlab_mean = (
        matlab_results["mean_ms"]
    )

    fig, ax = plt.subplots(
        figsize=(
            11,
            7
        )
    )


    # --------------------------------------------------------
    # Python
    # --------------------------------------------------------

    ax.plot(
        states,
        python_mean,
        marker="o",
        linewidth=2,
        markersize=7,
        label="Python / SciPy CSR"
    )


    # --------------------------------------------------------
    # MATLAB-compatible
    # --------------------------------------------------------

    ax.plot(
        states,
        matlab_mean,
        marker="s",
        linewidth=2,
        markersize=7,
        label="MATLAB-compatible / sparse"
    )


    # --------------------------------------------------------
    # Target
    # --------------------------------------------------------

    ax.axhline(
        TARGET_MS,
        linestyle="--",
        linewidth=1.5,
        label="Target = 15 ms"
    )


    # --------------------------------------------------------
    # Axis configuration
    # --------------------------------------------------------

    ax.set_xscale(
        "log"
    )


    ax.set_yscale(
        "log"
    )


    ax.set_xlabel(
        "State-space dimension N"
    )


    ax.set_ylabel(
        "Mean sparse matrix-vector time (ms)"
    )


    ax.set_title(
        "QFLPN Deterministic Sparse-Operator Scaling"
    )


    ax.set_xticks(
        states
    )


    ax.set_xticklabels(
        [
            "1,024",
            "10,000",
            "100,000"
        ]
    )


    ax.grid(
        True,
        which="both",
        linestyle=":",
        linewidth=0.7
    )


    ax.legend(
        loc="best"
    )


    # --------------------------------------------------------
    # Annotate measured means
    # --------------------------------------------------------

    for state, value in zip(
        states,
        python_mean
    ):

        ax.annotate(
            f"{value:.4f} ms",
            (
                state,
                value
            ),
            textcoords="offset points",
            xytext=(
                0,
                9
            ),
            ha="center",
            fontsize=8
        )


    for state, value in zip(
        states,
        matlab_mean
    ):

        ax.annotate(
            f"{value:.4f} ms",
            (
                state,
                value
            ),
            textcoords="offset points",
            xytext=(
                0,
                -16
            ),
            ha="center",
            fontsize=8
        )


    # --------------------------------------------------------
    # Figure note
    # --------------------------------------------------------

    ax.text(
        0.02,
        0.02,
        "Deterministic benchmark; no Monte Carlo. "
        "N denotes state-space dimension.",
        transform=ax.transAxes,
        fontsize=8,
        verticalalignment="bottom"
    )


    fig.tight_layout()


    OUTPUT_FIGURE.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    fig.savefig(
        OUTPUT_FIGURE,
        dpi=200,
        bbox_inches="tight"
    )


    plt.close(
        fig
    )


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    print(
        "============================================================"
    )

    print(
        "QFLPN SCALING COMPARISON"
    )

    print(
        "============================================================"
    )

    print(
        f"Python results:\n{PYTHON_RESULTS}"
    )

    print(
        f"MATLAB-compatible results:\n{MATLAB_RESULTS}"
    )

    print()


    python_rows = read_csv(
        PYTHON_RESULTS
    )


    matlab_rows = read_csv(
        MATLAB_RESULTS
    )


    python_results = convert_results(
        python_rows,
        "Python"
    )


    matlab_results = convert_results(
        matlab_rows,
        "MATLAB-compatible"
    )


    validate_consistency(
        python_results,
        matlab_results
    )


    create_figure(
        python_results,
        matlab_results
    )


    print(
        "Figure created:"
    )

    print(
        OUTPUT_FIGURE
    )

    print()


    print(
        "Measured state-space dimensions:"
    )

    for index, states in enumerate(
        EXPECTED_STATES
    ):

        print(
            f"N={states:,} | "
            f"Python mean="
            f"{python_results['mean_ms'][index]:.6f} ms | "
            f"MATLAB-compatible mean="
            f"{matlab_results['mean_ms'][index]:.6f} ms"
        )


    print()

    print(
        "All numerical validation checks:"
    )

    print(
        "Python: PASS"
    )

    print(
        "MATLAB-compatible: PASS"
    )


    print(
        "============================================================"
    )


if __name__ == "__main__":
    main()