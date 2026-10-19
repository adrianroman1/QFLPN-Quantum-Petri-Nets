"""Execute the canonical four-qubit QFLPN circuit in PennyLane."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pennylane as qml

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    fuzzy_to_angle,
    reference_state,
)

N_QUBITS = 4
ATOL = 1e-12
OUTPUT_FILE = Path("qflpn_pennylane_results.csv")


def build_device():
    return qml.device("default.qubit", wires=N_QUBITS)


@qml.qnode(build_device())
def qflpn_circuit(memberships):
    """Prepare U = C3X @ (RY(theta_1) kron ... kron RY(theta_4))."""
    for wire, membership in enumerate(memberships):
        qml.RY(fuzzy_to_angle(float(membership)), wires=wire)

    controlled_x = qml.ctrl(
        qml.PauliX,
        control=[0, 1, 2],
    )
    controlled_x(wires=3)

    return qml.state()


def main() -> int:
    memberships = tuple(DEFAULT_ACTIVATIONS)
    state = np.asarray(qflpn_circuit(memberships), dtype=np.complex128)
    reference = reference_state(memberships)

    if state.shape != (16,) or not np.all(np.isfinite(state)):
        print("FAIL: PennyLane returned an invalid state vector.")
        return 1

    difference = float(np.max(np.abs(state - reference)))
    norm_error = abs(float(np.linalg.norm(state)) - 1.0)
    probabilities = np.abs(state) ** 2
    probability_error = abs(float(probabilities.sum()) - 1.0)

    print("PennyLane / NumPy maximum difference:", f"{difference:.3e}")
    print("State norm error:", f"{norm_error:.3e}")
    print("Probability sum error:", f"{probability_error:.3e}")

    if max(difference, norm_error, probability_error) > ATOL:
        print("FAIL: PennyLane does not reproduce the NumPy reference.")
        return 1

    output_path = OUTPUT_FILE.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("basis", "probability"))
        for index, probability in enumerate(probabilities):
            writer.writerow((format(index, "04b"), float(probability)))

    print("PASS: PennyLane agrees with NumPy.")
    print("CSV:", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
