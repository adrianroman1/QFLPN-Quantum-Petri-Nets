"""Reference transition operators for the four-qubit P1 demonstrator."""
from __future__ import annotations

import math
import time
import numpy as np

if __package__:
    from .qflpn_reference import fuzzy_to_angle
else:  # Supports: python P1/code/qflpn_transition_operator.py
    from qflpn_reference import fuzzy_to_angle


I2 = np.eye(2, dtype=np.complex128)
X = np.array([[0, 1], [1, 0]], dtype=np.complex128)


def ry(theta: float) -> np.ndarray:
    """Return the analytic RY(theta) matrix."""
    value = float(theta)
    if not math.isfinite(value):
        raise ValueError("theta must be finite")
    c, s = math.cos(value / 2.0), math.sin(value / 2.0)
    return np.array([[c, -s], [s, c]], dtype=np.complex128)


def kron_all(*operators: np.ndarray) -> np.ndarray:
    if not operators:
        raise ValueError("at least one operator is required")
    result = np.asarray(operators[0], dtype=np.complex128)
    for operator in operators[1:]:
        result = np.kron(result, np.asarray(operator, dtype=np.complex128))
    return result


def local_rotation_operator(theta: float, target: int = 0, n_qubits: int = 4) -> np.ndarray:
    """Embed RY(theta) on target; qubit 0 is the leftmost Kronecker factor."""
    if not isinstance(n_qubits, int) or n_qubits < 1:
        raise ValueError("n_qubits must be a positive integer")
    if not isinstance(target, int) or not 0 <= target < n_qubits:
        raise ValueError("target must identify a qubit in the register")
    factors = [ry(theta) if index == target else I2 for index in range(n_qubits)]
    return kron_all(*factors)


def controlled_x(n_qubits: int = 2, control: int = 0, target: int = 1) -> np.ndarray:
    """Construct a multi-qubit controlled-X matrix."""
    if not isinstance(n_qubits, int) or n_qubits < 2:
        raise ValueError("controlled_x requires at least two qubits")
    if control == target or not (0 <= control < n_qubits and 0 <= target < n_qubits):
        raise ValueError("control and target must be distinct valid qubit indices")
    dimension = 2 ** n_qubits
    result = np.zeros((dimension, dimension), dtype=np.complex128)
    for basis in range(dimension):
        bits = [(basis >> (n_qubits - 1 - i)) & 1 for i in range(n_qubits)]
        output = basis
        if bits[control] == 1:
            output ^= 1 << (n_qubits - 1 - target)
        result[output, basis] = 1.0
    return result


def c3x() -> np.ndarray:
    """Four-qubit Toffoli with three controls and one target (C^3X)."""
    dimension = 16
    operator = np.zeros((dimension, dimension), dtype=np.complex128)
    for basis in range(dimension):
        # Big-endian basis convention: bits 0,1,2 are controls; bit 3 is target.
        output = basis ^ 1 if (basis & 0b1110) == 0b1110 else basis
        operator[output, basis] = 1.0
    return operator


def qflpn_transition_operator(memberships=(0.85, 0.90, 0.45, 0.70)) -> np.ndarray:
    """Compose local membership rotations and the C^3X demonstrator.

    Composition convention: rightmost operator acts first. The local rotations
    are applied as a tensor product, followed by C^3X.
    """
    values = tuple(memberships)
    if len(values) != 4:
        raise ValueError("the P1 global operator requires exactly four memberships")
    angles = [fuzzy_to_angle(value) for value in values]
    local = kron_all(*(ry(angle) for angle in angles))
    return c3x() @ local


def validate_unitarity(operator: np.ndarray, tol: float = 1e-10) -> float:
    """Return Frobenius unitarity residual; reject malformed/non-finite input."""
    tolerance = float(tol)
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("tol must be finite and non-negative")
    matrix = np.asarray(operator, dtype=np.complex128)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or matrix.shape[0] == 0:
        raise ValueError("operator must be a non-empty square matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("operator must contain only finite values")
    identity = np.eye(matrix.shape[0], dtype=np.complex128)
    residual = float(np.linalg.norm(matrix.conj().T @ matrix - identity, ord="fro"))
    if not math.isfinite(residual):
        raise ValueError("unitarity residual is not finite")
    if residual > tolerance:
        raise ValueError(f"operator is not unitary: residual={residual}")
    return residual


def benchmark_operator(repetitions: int = 10) -> dict:
    if not isinstance(repetitions, int) or repetitions < 1:
        raise ValueError("repetitions must be a positive integer")
    start = time.perf_counter()
    operator = qflpn_transition_operator()
    elapsed = (time.perf_counter() - start) / repetitions
    return {"dimension": int(operator.shape[0]), "average_construction_seconds": elapsed,
            "unitarity_residual": validate_unitarity(operator)}


def main() -> None:
    report = benchmark_operator()
    print(f"Global operator dimension: {report['dimension']}")
    print(f"Unitary residual: {report['unitarity_residual']:.3e}")
    print(f"Average construction time: {report['average_construction_seconds']:.6e} s")


if __name__ == "__main__":
    main()
