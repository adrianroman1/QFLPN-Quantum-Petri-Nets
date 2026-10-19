"""Transition-operator utilities for QFLPN P2."""

from __future__ import annotations

import numpy as np

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    HILBERT_DIM,
    c3x_operator,
    rotation_operator,
    transition_operator as canonical_transition_operator,
    validate_activations,
)


def controlled_x_operator() -> np.ndarray:
    """Return a four-qubit C3X operator.

    Controls: q1, q2, q3.
    Target: q4.
    Basis: big-endian, q1 is the most-significant bit.
    """
    return c3x_operator()


def build_rotation_operator(activations=DEFAULT_ACTIVATIONS) -> np.ndarray:
    """Return the tensor product of the four RY rotations."""
    return rotation_operator(validate_activations(activations))


def build_transition_operator(activations=DEFAULT_ACTIVATIONS) -> np.ndarray:
    """Return U = C3X @ U_rot."""
    return canonical_transition_operator(
        validate_activations(activations)
    )


def apply_transition(
    state: np.ndarray,
    activations=DEFAULT_ACTIVATIONS,
) -> np.ndarray:
    """Apply the canonical transition operator to a state vector."""
    vector = np.asarray(state, dtype=np.complex128)

    if vector.shape != (HILBERT_DIM,):
        raise ValueError("Input state must have shape (16,).")

    if not np.all(np.isfinite(vector)):
        raise ValueError("Input state contains non-finite values.")

    norm = np.linalg.norm(vector)
    if not np.isclose(norm, 1.0, atol=1e-10):
        raise ValueError("Input state must be normalized.")

    result = build_transition_operator(activations) @ vector

    if not np.isclose(np.linalg.norm(result), 1.0, atol=1e-10):
        raise ArithmeticError("Transition failed norm preservation.")

    return result


def verify_transition_structure() -> bool:
    """Check the exact permutation structure of the C3X gate."""
    gate = controlled_x_operator()

    if gate.shape != (16, 16):
        return False

    expected = np.eye(16, dtype=np.complex128)
    expected[14, 14] = 0.0
    expected[15, 15] = 0.0
    expected[14, 15] = 1.0
    expected[15, 14] = 1.0

    return bool(np.array_equal(gate, expected))


if __name__ == "__main__":
    operator = build_transition_operator()

    print("Transition operator shape:", operator.shape)
    print("C3X structure valid:", verify_transition_structure())
    print(
        "Unitary:",
        np.allclose(
            operator.conj().T @ operator,
            np.eye(16),
            atol=1e-10,
            rtol=0.0,
        ),
    )
