"""
QFLPN PennyLane Experiment
==========================

4-qubit QFLPN reference experiment.

The script:
- prepares the reference state;
- prints amplitudes;
- prints computational-basis probabilities;
- calculates normalization;
- exports numerical results to CSV.

No Monte Carlo.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pennylane as qml

from qflpn_reference import (
    fuzzy_to_angle,
    reference_state,
)


MEMBERSHIPS = (
    0.85,
    0.90,
    0.45,
    0.70,
)

N_QUBITS = 4
OUTPUT_FILE = Path("qflpn_pennylane_results.csv")


dev = qml.device(
    "default.qubit",
    wires=N_QUBITS,
)


@qml.qnode(dev)
def qflpn_circuit(memberships):
    """
    Prepare the four-qubit QFLPN reference state.
    """

    for wire, mu in enumerate(memberships):
        theta = fuzzy_to_angle(float(mu))
        qml.RY(theta, wires=wire)

    return qml.state()


def main() -> None:
    print("=" * 60)
    print("QFLPN PENNYLANE — 4-QUBIT EXPERIMENT")
    print("=" * 60)

    print("\nFuzzy memberships:")
    print(MEMBERSHIPS)

    state = np.asarray(
        qflpn_circuit(MEMBERSHIPS),
        dtype=np.complex128,
    )

    reference = reference_state(MEMBERSHIPS)

    state_difference = np.max(
        np.abs(state - reference)
    )

    probabilities = np.abs(state) ** 2

    print("\nState dimension:")
    print(state.size)

    print("\nNormalization:")
    print(f"||psi|| = {np.linalg.norm(state):.15f}")

    print("\nProbability conservation:")
    print(f"sum(P) = {probabilities.sum():.15f}")

    print("\nPennyLane vs reference implementation:")
    print(
        f"maximum absolute difference = "
        f"{state_difference:.3e}"
    )

    print("\nComputational-basis probabilities:")

    rows = []

    for index, probability in enumerate(probabilities):
        basis = format(index, f"0{N_QUBITS}b")

        if probability > 1e-14:
            print(
                f"|{basis}> : "
                f"{probability:.12f}"
            )

        rows.append(
            {
                "basis": basis,
                "probability": float(probability),
            }
        )

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "basis",
                "probability",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)

    print("\nExport:")
    print(OUTPUT_FILE.resolve())

    print("\nSTATUS:")
    if state_difference <= 1e-12:
        print("PASS — PennyLane agrees with reference model.")
    else:
        print("REVIEW REQUIRED.")


if __name__ == "__main__":
    main()
