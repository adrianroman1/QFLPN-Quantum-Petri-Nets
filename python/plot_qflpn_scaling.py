from pathlib import Path
import csv

import matplotlib.pyplot as plt


# ============================================================
# QFLPN SCALING COMPARISON FIGURE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
REPOSITORY_DIR = BASE_DIR.parent

PYTHON_RESULTS = (
    BASE_DIR
    / "results"
    / "qflpn_scaling_python.csv"
)

MATLAB_RESULTS = (
    REPOSITORY_DIR
    / "matlab"
    / "results"
    / "qflpn_scaling_matlab.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "results"
    / "qflpn_scaling_comparison.png"
)

EXPECTED_QUBITS = list(range(4, 18))
EXPECTED_STATES = [2 ** q for q in EXPECTED_QUBITS]
TARGET_MS = 15.0


def read_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing result file: {path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as handle:

        reader = csv.DictReader(handle)
        rows = list(reader)

    if not rows:
        raise RuntimeError(
            f"Empty result file: {path}"
        )

    return rows


def parse_results(rows, source_name):
    qubits = []
    states = []
    mean_times = []

    for row in rows:

        q = int(row["qubits"])
        n = int(row["states"])
        mean_ms = float(row["mean_state_ms"])

        qubits.append(q)
        states.append(n)
        mean_times.append(mean_ms)

    if qubits != EXPECTED_QUBITS:
        raise ValueError(
            f"{source_name}: unexpected qubit sequence: "
            f"{qubits}"
        )

    if states != EXPECTED_STATES:
        raise ValueError(
            f"{source_name}: unexpected state sequence: "
            f"{states}"
        )

    return qubits, states, mean_times


def main():

    python_rows = read_csv(PYTHON_RESULTS)
    matlab_rows = read_csv(MATLAB_RESULTS)

    q_python, states_python, time_python = (
        parse_results(
            python_rows,
            "Python",
        )
    )

    q_matlab, states_matlab, time_matlab = (
        parse_results(
            matlab_rows,
            "MATLAB",
        )
    )

    if q_python != q_matlab:
        raise ValueError(
            "Python and MATLAB qubit sequences differ."
        )

    if states_python != states_matlab:
        raise ValueError(
            "Python and MATLAB state sequences differ."
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig, ax = plt.subplots(
        figsize=(11, 7)
    )

    ax.plot(
        q_python,
        time_python,
        marker="o",
        linewidth=1.8,
        label="Python / SciPy CSR",
    )

    ax.plot(
        q_matlab,
        time_matlab,
        marker="s",
        linewidth=1.8,
        label="MATLAB / Octave sparse",
    )

    ax.axhline(
        TARGET_MS,
        linestyle="--",
        linewidth=1.5,
        label="Operational target: 15 ms",
    )

    ax.set_xlabel(
        "Number of qubits q"
    )

    ax.set_ylabel(
        "Mean sparse matrix-vector time (ms)"
    )

    ax.set_title(
        "QFLPN Scaling: Sparse Operator Execution Time"
    )

    ax.set_xticks(
        EXPECTED_QUBITS
    )

    ax.grid(
        True,
        which="both",
        axis="both",
        alpha=0.25,
    )

    ax.legend()

    # State counts are exact powers of two.
    # They are displayed as annotations without
    # treating state dimension as a qubit count.
    for q, n, t in zip(
        q_python,
        states_python,
        time_python,
    ):
        ax.annotate(
            f"N={n:,}",
            (q, t),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=7,
        )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_FILE,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)

    print("=" * 64)
    print("QFLPN SCALING COMPARISON")
    print("=" * 64)
    print(f"Python input : {PYTHON_RESULTS}")
    print(f"MATLAB input : {MATLAB_RESULTS}")
    print(f"Figure       : {OUTPUT_FILE}")
    print("=" * 64)


if __name__ == "__main__":
    main()