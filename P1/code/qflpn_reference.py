"""
QFLPN Reference Model
=====================

4-qubit reference implementation for the QFLPN doctoral model.

Mathematical convention:
    theta(mu) = 2 * arcsin(sqrt(mu)),  mu in [0, 1]

Then:
    RY(theta(mu)) |0>
has measurement probability mu for state |1>.

This mapping is a declared QFLPN modeling convention:
fuzzy membership != quantum probability by definition.

The module provides:
- fuzzy-to-angle mapping
- single-qubit state preparation
- 4-qubit reference state
- normalization validation
- density matrix construction and PSD diagnostic
- fidelity between pure states
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np


N_QUBITS = 4
STATE_DIMENSION = 2 ** N_QUBITS


def fuzzy_to_angle(mu: float) -> float:
    """Map fuzzy membership mu in [0,1] to theta(mu)=2 asin(sqrt(mu))."""
    if not 0.0 <= mu <= 1.0:
        raise ValueError("Fuzzy membership must belong to [0, 1].")
    return 2.0 * math.asin(math.sqrt(mu))


def ry_state(mu: float) -> np.ndarray:
    """Return RY(theta(mu))|0>; P(|1>) equals mu up to roundoff."""
    theta = fuzzy_to_angle(mu)
    return np.array(
        [math.cos(theta / 2.0), math.sin(theta / 2.0)],
        dtype=np.complex128,
    )


def kron_product(states: Iterable[np.ndarray]) -> np.ndarray:
    """Compute the Kronecker product of a sequence of state vectors."""
    result = np.array([1.0 + 0.0j], dtype=np.complex128)
    for state in states:
        result = np.kron(result, state)
    return result


def reference_state(memberships: Iterable[float]) -> np.ndarray:
    """Construct the four-qubit product reference state."""
    memberships = tuple(float(mu) for mu in memberships)
    if len(memberships) != N_QUBITS:
        raise ValueError(
            f"Expected {N_QUBITS} fuzzy memberships, received {len(memberships)}."
        )
    state = kron_product(ry_state(mu) for mu in memberships)
    validate_normalization(state)
    return state


def density_matrix(state: np.ndarray) -> np.ndarray:
    """Construct rho = |psi><psi| for a normalized pure state."""
    state = np.asarray(state, dtype=np.complex128)
    validate_normalization(state)
    return np.outer(state, np.conjugate(state))


def validate_normalization(state: np.ndarray, tolerance: float = 1e-12) -> None:
    """Verify ||psi||_2 = 1."""
    state = np.asarray(state, dtype=np.complex128)
    if state.ndim != 1:
        raise ValueError("State vector must be one-dimensional.")
    norm = np.linalg.norm(state)
    if not np.isclose(norm, 1.0, atol=tolerance, rtol=0.0):
        raise ValueError(f"State is not normalized: ||psi|| = {norm}")


def positive_semidefinite_residual(
    rho: np.ndarray,
    hermiticity_tolerance: float = 1e-12,
) -> float:
    r"""Return eps_PSD=max(0,-lambda_min(rho)) for a Hermitian matrix.

    The Hermiticity precondition is checked explicitly because the PSD
    diagnostic in P1 is defined for density operators.
    """
    rho = np.asarray(rho, dtype=np.complex128)
    if rho.ndim != 2 or rho.shape[0] != rho.shape[1]:
        raise ValueError("Density matrix must be square.")
    hermiticity_error = np.linalg.norm(rho - rho.conj().T, ord="fro")
    if hermiticity_error > hermiticity_tolerance:
        raise ValueError(
            "PSD diagnostic requires a Hermitian matrix; "
            f"Hermiticity error={hermiticity_error:.3e}."
        )
    lambda_min = float(np.min(np.linalg.eigvalsh(rho)))
    return max(0.0, -lambda_min)


def pure_state_fidelity(state_a: np.ndarray, state_b: np.ndarray) -> float:
    """Fidelity F=|<psi_a|psi_b>|^2 between normalized pure states."""
    state_a = np.asarray(state_a, dtype=np.complex128)
    state_b = np.asarray(state_b, dtype=np.complex128)
    validate_normalization(state_a)
    validate_normalization(state_b)
    if state_a.shape != state_b.shape:
        raise ValueError("Pure-state vectors must have identical dimensions.")
    return float(abs(np.vdot(state_a, state_b)) ** 2)


def computational_basis_probabilities(state: np.ndarray) -> np.ndarray:
    """Return probabilities in lexicographic computational-basis order."""
    state = np.asarray(state, dtype=np.complex128)
    if state.ndim != 1 or state.size != STATE_DIMENSION:
        raise ValueError(
            f"Expected state vector dimension {STATE_DIMENSION}, "
            f"received shape {state.shape}."
        )
    validate_normalization(state)
    probabilities = np.abs(state) ** 2
    if not np.isclose(probabilities.sum(), 1.0, atol=1e-12, rtol=0.0):
        raise ValueError("Probabilities are not normalized.")
    return probabilities


def main() -> None:
    memberships = (0.85, 0.90, 0.45, 0.70)
    state = reference_state(memberships)
    rho = density_matrix(state)
    probabilities = computational_basis_probabilities(state)
    print("QFLPN 4-qubit reference model")
    print("--------------------------------")
    print("Memberships:", memberships)
    print("Number of qubits:", N_QUBITS)
    print("State dimension:", state.size)
    print("Norm:", np.linalg.norm(state))
    print("Density matrix shape:", rho.shape)
    print("Probability sum:", probabilities.sum())
    print("PSD residual:", positive_semidefinite_residual(rho))
    print("\nFuzzy -> RY angles:")
    for mu in memberships:
        print(f"mu={mu:.6f} -> theta={fuzzy_to_angle(mu):.12f}")
    print("\nComputational-basis probabilities:")
    for index, probability in enumerate(probabilities):
        if probability > 1e-14:
            print(f"|{index:04b}> : {probability:.12f}")


if __name__ == "__main__":
    main()
