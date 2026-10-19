"""Independent PennyLane-versus-NumPy circuit equivalence tests."""

from __future__ import annotations

import numpy as np
import pennylane as qml

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    fuzzy_to_angle,
    reference_state,
)

ATOL = 1e-12


def execute_pennylane(activations):
    device = qml.device("default.qubit", wires=4)

    @qml.qnode(device)
    def circuit():
        for wire, activation in enumerate(activations):
            qml.RY(fuzzy_to_angle(float(activation)), wires=wire)

        controlled_x = qml.ctrl(qml.PauliX, control=[0, 1, 2])
        controlled_x(wires=3)
        return qml.state()

    return np.asarray(circuit(), dtype=np.complex128)


def test_pennylane_state_matches_numpy_reference():
    actual = execute_pennylane(DEFAULT_ACTIVATIONS)
    expected = reference_state(DEFAULT_ACTIVATIONS)

    assert actual.shape == (16,)
    assert np.all(np.isfinite(actual))
    assert np.allclose(actual, expected, atol=ATOL, rtol=0.0)


def test_pennylane_state_is_normalized():
    actual = execute_pennylane(DEFAULT_ACTIVATIONS)
    assert np.isclose(np.linalg.norm(actual), 1.0, atol=ATOL, rtol=0.0)


def test_pennylane_probabilities_match_numpy_reference():
    actual = execute_pennylane(DEFAULT_ACTIVATIONS)
    expected = reference_state(DEFAULT_ACTIVATIONS)

    assert np.allclose(
        np.abs(actual) ** 2,
        np.abs(expected) ** 2,
        atol=ATOL,
        rtol=0.0,
    )


def test_pennylane_c3x_changes_only_the_controlled_transition():
    # The explicit C3X action on |1110> must produce |1111>.
    device = qml.device("default.qubit", wires=4)

    @qml.qnode(device)
    def circuit():
        qml.BasisState(np.array([1, 1, 1, 0]), wires=range(4))
        qml.ctrl(qml.PauliX, control=[0, 1, 2])(wires=3)
        return qml.state()

    state = np.asarray(circuit())
    expected = np.zeros(16, dtype=np.complex128)
    expected[15] = 1.0
    assert np.allclose(state, expected, atol=ATOL, rtol=0.0)
