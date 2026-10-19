"""Independent PennyLane-versus-NumPy statevector parity tests."""

from __future__ import annotations

import numpy as np
import pennylane as qml

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    fuzzy_to_angle,
    reference_state,
)

ATOL = 1e-10
WIRES = [0, 1, 2, 3]


def pennylane_statevector(
    activations: tuple[float, ...] = DEFAULT_ACTIVATIONS,
) -> np.ndarray:
    """Execute the four RY gates followed by the canonical C3X."""

    device = qml.device(
        "default.qubit",
        wires=4,
        shots=None,
    )

    angles = tuple(
        fuzzy_to_angle(value)
        for value in activations
    )

    @qml.qnode(device)
    def circuit():
        for wire, angle in zip(WIRES, angles):
            qml.RY(angle, wires=wire)

        # First three wires are controls; last wire is target.
        qml.MultiControlledX(wires=[0, 1, 2, 3])

        return qml.state()

    return np.asarray(circuit(), dtype=np.complex128)


def test_pennylane_and_numpy_statevectors_agree():
    expected = reference_state(DEFAULT_ACTIVATIONS)
    actual = pennylane_statevector(DEFAULT_ACTIVATIONS)

    assert actual.shape == (16,)
    assert np.all(np.isfinite(actual))

    assert np.allclose(
        actual,
        expected,
        atol=ATOL,
        rtol=0.0,
    )


def test_pennylane_and_numpy_probabilities_agree():
    numpy_state = reference_state(DEFAULT_ACTIVATIONS)
    pennylane_state = pennylane_statevector(DEFAULT_ACTIVATIONS)

    numpy_probabilities = np.abs(numpy_state) ** 2
    pennylane_probabilities = np.abs(pennylane_state) ** 2

    assert np.allclose(
        pennylane_probabilities,
        numpy_probabilities,
        atol=ATOL,
        rtol=0.0,
    )


def test_pennylane_statevector_is_normalized():
    state = pennylane_statevector(DEFAULT_ACTIVATIONS)

    assert np.isclose(
        np.linalg.norm(state),
        1.0,
        atol=ATOL,
        rtol=0.0,
    )


def test_pennylane_and_numpy_have_unit_self_fidelity():
    numpy_state = reference_state(DEFAULT_ACTIVATIONS)
    pennylane_state = pennylane_statevector(DEFAULT_ACTIVATIONS)

    fidelity = float(
        abs(np.vdot(numpy_state, pennylane_state)) ** 2
    )

    assert np.isclose(
        fidelity,
        1.0,
        atol=ATOL,
        rtol=0.0,
    )
