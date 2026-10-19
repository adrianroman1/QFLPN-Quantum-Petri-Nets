import numpy as np
import pennylane as qml

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    fuzzy_to_angle,
    reference_state,
)


ATOL = 1e-10


def execute_pennylane(activations):
    device = qml.device("default.qubit", wires=4, shots=None)

    @qml.qnode(device)
    def circuit():
        for wire, activation in enumerate(activations):
            qml.RY(fuzzy_to_angle(activation), wires=wire)

        qml.MultiControlledX(wires=[0, 1, 2, 3])
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


def test_pennylane_probabilities_match_numpy():
    actual = execute_pennylane(DEFAULT_ACTIVATIONS)
    expected = reference_state(DEFAULT_ACTIVATIONS)

    assert np.allclose(
        np.abs(actual) ** 2,
        np.abs(expected) ** 2,
        atol=ATOL,
        rtol=0.0,
    )


def test_pennylane_numpy_squared_fidelity_is_one():
    actual = execute_pennylane(DEFAULT_ACTIVATIONS)
    expected = reference_state(DEFAULT_ACTIVATIONS)
    fidelity = abs(np.vdot(expected, actual)) ** 2

    assert np.isclose(fidelity, 1.0, atol=ATOL, rtol=0.0)
