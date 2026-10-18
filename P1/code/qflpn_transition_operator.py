"""
QFLPN Transition Operators
==========================

Deterministic four-qubit transition-operator construction.

The P1 reference instance uses the three-control X operator C^3X on
qubits q1,q2,q3 -> q4, in lexicographic computational-basis order.
A generic one-control CX constructor remains available for other declared
transition semantics.

No Monte Carlo.
"""

from __future__ import annotations

import math
import time

import numpy as np

from qflpn_reference import fuzzy_to_angle


N_QUBITS = 4
DIMENSION = 2 ** N_QUBITS


def identity() -> np.ndarray:
    """2x2 identity matrix."""
    return np.eye(2, dtype=np.complex128)


def pauli_x() -> np.ndarray:
    """Pauli-X operator."""
    return np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)


def ry(theta: float) -> np.ndarray:
    """Single-qubit RY(theta) with the half-angle convention."""
    half = theta / 2.0
    return np.array(
        [[math.cos(half), -math.sin(half)],
         [math.sin(half), math.cos(half)]],
        dtype=np.complex128,
    )


def kron_all(matrices: list[np.ndarray]) -> np.ndarray:
    """Kronecker product of matrices in lexicographic qubit order."""
    if not matrices:
        raise ValueError("At least one matrix is required.")
    result = np.asarray(matrices[0], dtype=np.complex128)
    for matrix in matrices[1:]:
        result = np.kron(result, matrix)
    return result


def local_rotation_operator(memberships: tuple[float, ...]) -> np.ndarray:
    """Construct RY(theta_1) tensor ... tensor RY(theta_4)."""
    if len(memberships) != N_QUBITS:
        raise ValueError(f"Expected {N_QUBITS} memberships.")
    return kron_all([ry(fuzzy_to_angle(mu)) for mu in memberships])


def controlled_x(control: int, target: int) -> np.ndarray:
    """Construct a generic single-control CX in the four-qubit basis."""
    if control == target:
        raise ValueError("Control and target must be different.")
    if not 0 <= control < N_QUBITS:
        raise ValueError("Invalid control qubit.")
    if not 0 <= target < N_QUBITS:
        raise ValueError("Invalid target qubit.")
    operator = np.zeros((DIMENSION, DIMENSION), dtype=np.complex128)
    for basis in range(DIMENSION):
        output = basis
        control_bit = (basis >> (N_QUBITS - 1 - control)) & 1
        if control_bit:
            output ^= 1 << (N_QUBITS - 1 - target)
        operator[output, basis] = 1.0
    return operator


def c3x() -> np.ndarray:
    r"""Construct P1's C^3X=(I_8-P_c) tensor I_2 + P_c tensor X.

    P_c=|111><111| acts on the first three qubits; X acts on q4.
    In lexicographic order only |1110> and |1111> are exchanged.
    """
    projector = np.zeros((8, 8), dtype=np.complex128)
    projector[7, 7] = 1.0
    identity_8 = np.eye(8, dtype=np.complex128)
    return (
        np.kron(identity_8 - projector, identity())
        + np.kron(projector, pauli_x())
    )


def qflpn_transition_operator(
    memberships: tuple[float, ...],
    control: int | None = None,
    target: int | None = None,
) -> np.ndarray:
    r"""Build the P1 reference transition U=C^3X U_local.

    Supplying both ``control`` and ``target`` explicitly selects the generic
    single-control CX variant. Omitting both uses the P1 C^3X convention.
    """
    if (control is None) != (target is None):
        raise ValueError("Specify both control and target, or neither.")
    u_local = local_rotation_operator(memberships)
    u_controlled = c3x() if control is None else controlled_x(control, target)
    return u_controlled @ u_local


def validate_unitarity(
    operator: np.ndarray,
    tolerance: float = 1e-12,
) -> float:
    """Return ||U^dagger U-I||_F and raise if the tolerance is exceeded."""
    operator = np.asarray(operator, dtype=np.complex128)
    if operator.ndim != 2 or operator.shape[0] != operator.shape[1]:
        raise ValueError("Operator must be square.")
    dimension = operator.shape[0]
    identity_matrix = np.eye(dimension, dtype=np.complex128)
    error = np.linalg.norm(operator.conj().T @ operator - identity_matrix, ord="fro")
    if error > tolerance:
        raise ValueError(f"Operator is not unitary: error={error:.3e}")
    return float(error)


def benchmark_operator(
    memberships: tuple[float, ...],
    repetitions: int = 1000,
) -> dict[str, float]:
    """Deterministic timing benchmark; no random sampling is used."""
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1.")
    for _ in range(20):
        qflpn_transition_operator(memberships)
    timings_ns = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        qflpn_transition_operator(memberships)
        timings_ns.append(time.perf_counter_ns() - start)
    timings_ms = np.asarray(timings_ns, dtype=np.float64) / 1_000_000.0
    return {
        "mean_ms": float(np.mean(timings_ms)),
        "median_ms": float(np.median(timings_ms)),
        "min_ms": float(np.min(timings_ms)),
        "max_ms": float(np.max(timings_ms)),
    }


def main() -> None:
    memberships = (0.85, 0.90, 0.45, 0.70)
    operator = qflpn_transition_operator(memberships)
    unitarity_error = validate_unitarity(operator)
    print("QFLPN P1 transition operator")
    print("Operator dimension:", operator.shape)
    print(f"||U^dagger U-I||_F = {unitarity_error:.3e}")
    print("C^3X dimension:", c3x().shape)
    benchmark = benchmark_operator(memberships, repetitions=1000)
    for key, value in benchmark.items():
        print(f"{key} = {value:.6f}")


if __name__ == "__main__":
    main()
