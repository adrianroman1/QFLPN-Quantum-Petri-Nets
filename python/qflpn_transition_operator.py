"""
QFLPN Transition Operators
==========================

Deterministic 4-qubit QFLPN transition-operator construction.

Model:
    - fuzzy memberships are mapped to RY angles;
    - local RY operators prepare the four-qubit state;
    - a controlled-X interaction models a transition coupling
      between two QFLPN qubits.

The global transition operator is unitary.

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
    return np.array(
        [
            [0.0, 1.0],
            [1.0, 0.0],
        ],
        dtype=np.complex128,
    )


def ry(theta: float) -> np.ndarray:
    """Single-qubit RY(theta) operator."""
    half = theta / 2.0

    return np.array(
        [
            [
                math.cos(half),
                -math.sin(half),
            ],
            [
                math.sin(half),
                math.cos(half),
            ],
        ],
        dtype=np.complex128,
    )


def kron_all(matrices: list[np.ndarray]) -> np.ndarray:
    """Kronecker product of all matrices in order."""
    result = matrices[0]

    for matrix in matrices[1:]:
        result = np.kron(result, matrix)

    return result


def local_rotation_operator(
    memberships: tuple[float, ...],
) -> np.ndarray:
    """
    Construct the tensor-product local RY operator.

    U_local =
        RY(theta_1) ⊗ RY(theta_2)
        ⊗ RY(theta_3) ⊗ RY(theta_4)
    """
    if len(memberships) != N_QUBITS:
        raise ValueError(
            f"Expected {N_QUBITS} memberships."
        )

    rotations = [
        ry(fuzzy_to_angle(mu))
        for mu in memberships
    ]

    return kron_all(rotations)


def controlled_x(
    control: int,
    target: int,
) -> np.ndarray:
    """
    Construct a controlled-X operator for four qubits.

    Qubit indices are:
        0, 1, 2, 3

    The operator is constructed directly in the
    computational basis.
    """
    if control == target:
        raise ValueError(
            "Control and target must be different."
        )

    if not 0 <= control < N_QUBITS:
        raise ValueError("Invalid control qubit.")

    if not 0 <= target < N_QUBITS:
        raise ValueError("Invalid target qubit.")

    operator = np.zeros(
        (DIMENSION, DIMENSION),
        dtype=np.complex128,
    )

    for basis in range(DIMENSION):

        output = basis

        control_bit = (
            basis >> (N_QUBITS - 1 - control)
        ) & 1

        if control_bit == 1:
            output ^= (
                1 << (N_QUBITS - 1 - target)
            )

        operator[output, basis] = 1.0

    return operator


def qflpn_transition_operator(
    memberships: tuple[float, ...],
    control: int = 0,
    target: int = 1,
) -> np.ndarray:
    """
    Construct the global QFLPN transition operator.

        U_transition = CX(control,target) @ U_local

    The order is explicit: first local fuzzy-derived
    rotations, then the controlled transition coupling.
    """
    u_local = local_rotation_operator(memberships)

    u_cx = controlled_x(
        control=control,
        target=target,
    )

    return u_cx @ u_local


def validate_unitarity(
    operator: np.ndarray,
    tolerance: float = 1e-12,
) -> float:
    """
    Return ||U*U - I||_F.
    """
    dimension = operator.shape[0]

    identity_matrix = np.eye(
        dimension,
        dtype=np.complex128,
    )

    error = np.linalg.norm(
        operator.conj().T @ operator
        - identity_matrix,
        ord="fro",
    )

    if error > tolerance:
        raise ValueError(
            f"Operator is not unitary: error={error:.3e}"
        )

    return float(error)


def benchmark_operator(
    memberships: tuple[float, ...],
    repetitions: int = 1000,
) -> dict[str, float]:
    """
    Deterministic timing benchmark.

    No random sampling is used.
    """
    for _ in range(20):
        qflpn_transition_operator(memberships)

    timings_ns = []

    for _ in range(repetitions):
        start = time.perf_counter_ns()

        qflpn_transition_operator(memberships)

        end = time.perf_counter_ns()

        timings_ns.append(end - start)

    timings_ms = np.asarray(
        timings_ns,
        dtype=np.float64,
    ) / 1_000_000.0

    return {
        "mean_ms": float(np.mean(timings_ms)),
        "median_ms": float(np.median(timings_ms)),
        "min_ms": float(np.min(timings_ms)),
        "max_ms": float(np.max(timings_ms)),
    }


def main() -> None:
    memberships = (
        0.85,
        0.90,
        0.45,
        0.70,
    )

    print("=" * 60)
    print("QFLPN TRANSITION OPERATOR")
    print("=" * 60)

    operator = qflpn_transition_operator(
        memberships
    )

    print("\nOperator dimension:")
    print(operator.shape)

    unitarity_error = validate_unitarity(
        operator
    )

    print("\nUnitarity:")
    print(
        f"||U†U-I||_F = "
        f"{unitarity_error:.3e}"
    )

    benchmark = benchmark_operator(
        memberships,
        repetitions=1000,
    )

    print("\nDeterministic timing:")
    print(
        f"mean   = {benchmark['mean_ms']:.6f} ms"
    )
    print(
        f"median = {benchmark['median_ms']:.6f} ms"
    )
    print(
        f"min    = {benchmark['min_ms']:.6f} ms"
    )
    print(
        f"max    = {benchmark['max_ms']:.6f} ms"
    )

    target_ms = 15.0

    print("\n15 ms target:")

    if benchmark["mean_ms"] <= target_ms:
        print(
            f"PASS: mean <= {target_ms:.1f} ms"
        )
    else:
        print(
            f"TARGET NOT MET: mean > "
            f"{target_ms:.1f} ms"
        )


if __name__ == "__main__":
    main()
