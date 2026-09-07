import csv
from pathlib import Path

import matplotlib.pyplot as plt


BASE_DIR = Path(
    __file__
).resolve().parent

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


def read_csv(filename: Path):

    if not filename.exists():

        raise FileNotFoundError(
            f"Required results file "
            f"was not found:\n{filename}"
        )

    with filename.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        reader = csv.DictReader(
            file
        )

        rows = list(reader)

    if not rows:

        raise ValueError(
            f"Results file is empty:\n"
            f"{filename}"
        )

    return rows


def convert_results(rows):

    qubits = []
    states = []
    mean_ms = []
    median_ms = []

    for row in rows:

        qubits.append(
            int(row["qubits"])
        )

        states.append(
            int(row["states"])
        )

        mean_ms.append(
            float(row["mean_ms"])
        )

        median_ms.append(
            float(row["median_ms"])
        )

    return (
        qubits,
        states,
        mean_ms,
        median_ms
    )


def validate_dimensions(
    python_qubits,
    matlab_qubits
):

    if python_qubits != matlab_qubits:

        raise ValueError(
            "Python and MATLAB results "
            "contain different qubit levels."
        )

    expected = list(
        range(
            4,
            18
        )
    )

    if python_qubits != expected:

        raise ValueError(
            "Unexpected qubit range. "
            "Expected q=4...17."
        )


def main():

    print(
        "QFLPN scaling comparison"
    )

    print(
        f"Python results:\n"
        f"{PYTHON_RESULTS}"
    )

    print(
        f"MATLAB results:\n"
        f"{MATLAB_RESULTS}"
    )

    python_rows = read_csv(
        PYTHON_RESULTS
    )

    matlab_rows = read_csv(
        MATLAB_RESULTS
    )

    (
        python_qubits,
        python_states,
        python_mean,
        python_median
    ) = convert_results(
        python_rows
    )

    (
        matlab_qubits,
        matlab_states,
        matlab_mean,
        matlab_median
    ) = convert_results(
        matlab_rows
    )

    validate_dimensions(
        python_qubits,
        matlab_qubits
    )

    if python_states != matlab_states:

        raise ValueError(
            "Python and MATLAB results "
            "contain different state dimensions."
        )

    if len(python_qubits) != 14:

        raise ValueError(
            "Expected 14 qubit levels "
            "from q=4 through q=17."
        )

    target_ms = 15.0

    fig, ax = plt.subplots(
        figsize=(11, 7)
    )

    ax.plot(
        python_qubits,
        python_mean,
        marker="o",
        linewidth=2,
        label="Python"
    )

    ax.plot(
        matlab_qubits,
        matlab_mean,
        marker="s",
        linewidth=2,
        label="MATLAB-compatible"
    )

    ax.axhline(
        target_ms,
        linestyle="--",
        linewidth=1.5,
        label="Target = 15 ms"
    )

    ax.set_yscale(
        "log"
    )

    ax.set_xlabel(
        "Number of qubits"
    )

    ax.set_ylabel(
        "Mean SpMV execution time (ms)"
    )

    ax.set_title(
        "QFLPN Scaling with Number of Qubits"
    )

    ax.set_xticks(
        python_qubits
    )

    ax.grid(
        True,
        which="both",
        linestyle=":",
        linewidth=0.7
    )

    ax.legend()

    for q, n, value in zip(
        python_qubits,
        python_states,
        python_mean
    ):

        ax.annotate(
            f"{n:,}",
            (
                q,
                value
            ),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=7
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

    plt.close(fig)

    print(
        "Comparison figure created:"
    )

    print(
        OUTPUT_FIGURE
    )

    print()
    print(
        "Qubits:",
        python_qubits
    )

    print(
        "States:",
        python_states
    )


if __name__ == "__main__":
    main()