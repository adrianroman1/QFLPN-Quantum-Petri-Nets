"""Canonical NumPy reference implementation for the QFLPN P2 model.

Conventions
-----------
- Four qubits; Hilbert-space dimension is 16.
- Computational basis is big-endian:
  |0000>, |0001>, ..., |1111>.
- q1 is the leftmost / most-significant qubit.
- q4 is the rightmost / least-significant qubit.
- Each activation lambda_i is encoded by:
      theta_i = 2 * asin(sqrt(lambda_i))
- The single-qubit operation is RY(theta_i).
- The four-qubit rotation is:
      U_rot = RY(theta_1) kron ... kron RY(theta_4)
- The transition is a C3X gate with controls q1, q2, q3
  and target q4. It swaps basis indices 14 and 15.
- The complete operator is:
      U = C3X @ U_rot
"""

from __future__ import annotations

from typing import Iterable

import numpy as np


N_QUBITS = 4
HILBERT_DIM = 2**N_QUBITS

DEFAULT_ACTIVATIONS = (0.85, 0.90, 0.45, 0.70)


def _validate_activation(value: float) -> float:
    """Validate one activation, rejecting bool and non-finite values."""

    if isinstance(value, (bool, np.bool_)):
        raise TypeError("Boolean values are not valid activations.")

    if not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError("Activation must be a real numeric scalar.")

    result = float(value)

    if not np.isfinite(result):
        raise ValueError("Activation must be finite.")

    if not 0.0 <= result <= 1.0:
        raise ValueError("Activation must lie in [0, 1].")

    return result


def validate_activations(
    activations: Iterable[float] = DEFAULT_ACTIVATIONS,
) -> tuple[float, ...]:
    """Return exactly four validated activation values."""

    try:
        values = tuple(activations)
    except TypeError as exc:
        raise TypeError(
            "Activations must be an iterable of four values."
        ) from exc

    if len(values) != N_QUBITS:
        raise ValueError("Exactly four activations are required.")

    return tuple(_validate_activation(value) for value in values)


def fuzzy_to_angle(activation: float) -> float:
    """Map an activation lambda in [0, 1] to an RY angle."""

    lam = _validate_activation(activation)
    return float(2.0 * np.arcsin(np.sqrt(lam)))


def ry_matrix(theta: float) -> np.ndarray:
    """Return the standard real-valued RY(theta) matrix.

    Only real numeric scalar inputs are accepted.
    Boolean values and numeric strings are rejected explicitly.
    """

    if isinstance(theta, (bool, np.bool_)):
        raise TypeError("theta must not be Boolean.")

    if not isinstance(theta, (int, float, np.integer, np.floating)):
        raise TypeError("theta must be a real numeric scalar.")

    value = float(theta)

    if not np.isfinite(value):
        raise ValueError("theta must be finite.")

    c = np.cos(value / 2.0)
    s = np.sin(value / 2.0)

    return np.array(
        [
            [c, -s],
            [s, c],
        ],
        dtype=np.complex128,
    )


def rotation_operator(
    activations: Iterable[float] = DEFAULT_ACTIVATIONS,
) -> np.ndarray:
    """Construct U_rot in big-endian qubit order."""

    values = validate_activations(activations)

    operator = np.array(
        [[1.0 + 0.0j]],
        dtype=np.complex128,
    )

    for activation in values:
        theta = fuzzy_to_angle(activation)
        operator = np.kron(operator, ry_matrix(theta))

    if operator.shape != (HILBERT_DIM, HILBERT_DIM):
        raise RuntimeError(
            "Unexpected rotation-operator dimensions."
        )

    return operator


def c3x_operator() -> np.ndarray:
    """Construct C3X with controls q1,q2,q3 and target q4.

    In the specified big-endian basis, the only swapped basis
    states are |1110> (index 14) and |1111> (index 15).
    """

    operator = np.eye(
        HILBERT_DIM,
        dtype=np.complex128,
    )

    operator[14, 14] = 0.0
    operator[15, 15] = 0.0
    operator[14, 15] = 1.0
    operator[15, 14] = 1.0

    return operator


def transition_operator(
    activations: Iterable[float] = DEFAULT_ACTIVATIONS,
) -> np.ndarray:
    """Construct the complete operator U = C3X @ U_rot."""

    u_rot = rotation_operator(activations)
    c3x = c3x_operator()

    return c3x @ u_rot


def initial_state() -> np.ndarray:
    """Return the computational basis state |0000>."""

    state = np.zeros(
        HILBERT_DIM,
        dtype=np.complex128,
    )
    state[0] = 1.0

    return state


def reference_state(
    activations: Iterable[float] = DEFAULT_ACTIVATIONS,
) -> np.ndarray:
    """Compute the final state U|0000>."""

    operator = transition_operator(activations)
    state = operator @ initial_state()

    if not np.isclose(
        np.linalg.norm(state),
        1.0,
        atol=1e-12,
        rtol=0.0,
    ):
        raise ArithmeticError(
            "Reference state is not normalized."
        )

    return state


def density_matrix(state: np.ndarray) -> np.ndarray:
    """Construct rho = |psi><psi| from a normalized state vector."""

    vector = np.asarray(
        state,
        dtype=np.complex128,
    )

    if vector.shape != (HILBERT_DIM,):
        raise ValueError(
            "State vector must have shape (16,)."
        )

    if not np.all(np.isfinite(vector)):
        raise ValueError(
            "State vector contains non-finite values."
        )

    norm = np.linalg.norm(vector)

    if not np.isclose(
        norm,
        1.0,
        atol=1e-10,
        rtol=0.0,
    ):
        raise ValueError(
            "State vector must be normalized."
        )

    return np.outer(
        vector,
        vector.conj(),
    )


def is_unitary(
    operator: np.ndarray,
    atol: float = 1e-10,
) -> bool:
    """Return whether a matrix is unitary within the given tolerance."""

    matrix = np.asarray(
        operator,
        dtype=np.complex128,
    )

    if matrix.shape != (
        HILBERT_DIM,
        HILBERT_DIM,
    ):
        return False

    if not np.all(np.isfinite(matrix)):
        return False

    identity = np.eye(
        HILBERT_DIM,
        dtype=np.complex128,
    )

    return bool(
        np.allclose(
            matrix.conj().T @ matrix,
            identity,
            atol=atol,
            rtol=0.0,
        )
    )


def basis_label(index: int) -> str:
    """Return the four-qubit big-endian basis label for an index."""

    if isinstance(index, (bool, np.bool_)):
        raise TypeError(
            "Basis index must not be Boolean."
        )

    if not isinstance(index, (int, np.integer)):
        raise TypeError(
            "Basis index must be an integer."
        )

    if not 0 <= int(index) < HILBERT_DIM:
        raise ValueError(
            "Basis index must lie between 0 and 15."
        )

    return format(int(index), "04b")


if __name__ == "__main__":
    state = reference_state()
    probabilities = np.abs(state) ** 2

    print("QFLPN P2 — NumPy reference")
    print("Basis order: big-endian |0000> ... |1111>")
    print("Activations:", DEFAULT_ACTIVATIONS)
    print("State norm:", np.linalg.norm(state))
    print(
        "Transition operator unitary:",
        is_unitary(transition_operator()),
    )

    print("\nNon-zero output probabilities:")

    for index, probability in enumerate(probabilities):
        if probability > 1e-14:
            print(
                f"|{basis_label(index)}> : "
                f"{probability:.12f}"
            )
