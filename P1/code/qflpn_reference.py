"""Numerical reference primitives for the QFLPN P1 validation layer.

This module provides auditable NumPy reference calculations. It does not
claim to implement the complete Petri-net semantics described in the paper.
"""
from __future__ import annotations

import math
from numbers import Real
from typing import Iterable

import numpy as np


def _strict_real(value: object, name: str) -> float:
    """Accept real numeric scalars only; reject bool, strings and complex."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a real numeric scalar")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _finite_nonnegative_tolerance(tol: float) -> float:
    value = _strict_real(tol, "tol")
    if value < 0.0:
        raise ValueError("tol must be finite and non-negative")
    return value


def fuzzy_to_angle(mu: float) -> float:
    """Encode mu in [0,1] as theta = 2 asin(sqrt(mu))."""
    value = _strict_real(mu, "membership value")
    if not 0.0 <= value <= 1.0:
        raise ValueError("membership value must lie in [0, 1]")
    return 2.0 * math.asin(math.sqrt(value))


def ry_state(theta: float) -> np.ndarray:
    """Apply RY(theta) to the computational basis state |0>."""
    value = _strict_real(theta, "theta")
    return np.array(
        [math.cos(value / 2.0), math.sin(value / 2.0)],
        dtype=np.complex128,
    )


def kron_product(*operators: np.ndarray) -> np.ndarray:
    """Kronecker product of one or more vectors or matrices."""
    if not operators:
        raise ValueError("at least one operand is required")
    result = np.asarray(operators[0])
    for operand in operators[1:]:
        result = np.kron(result, np.asarray(operand))
    return result


def reference_state(memberships: Iterable[float]) -> np.ndarray:
    """Prepare a product state using the membership-to-angle encoding."""
    try:
        values = list(memberships)
    except TypeError as exc:
        raise ValueError("memberships must be an iterable of real numbers") from exc
    if not values:
        raise ValueError("at least one membership value is required")
    states = [ry_state(fuzzy_to_angle(mu)) for mu in values]
    return kron_product(*states).astype(np.complex128, copy=False)


def density_matrix(state: np.ndarray) -> np.ndarray:
    """Return |psi><psi| after validating a finite, nonzero state vector."""
    vector = np.asarray(state, dtype=np.complex128)
    if vector.ndim != 1 or vector.size == 0:
        raise ValueError("state must be a non-empty one-dimensional vector")
    if not np.all(np.isfinite(vector)):
        raise ValueError("state vector must contain only finite values")
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0.0:
        raise ValueError("state vector must have a finite, nonzero norm")
    vector = vector / norm
    return np.outer(vector, vector.conj())


def validate_normalization(state: np.ndarray, tol: float = 1e-10) -> float:
    """Return absolute norm error; reject invalid or out-of-tolerance input."""
    tolerance = _finite_nonnegative_tolerance(tol)
    vector = np.asarray(state, dtype=np.complex128)
    if vector.ndim != 1 or vector.size == 0:
        raise ValueError("state must be a non-empty one-dimensional vector")
    if not np.all(np.isfinite(vector)):
        raise ValueError("state vector must contain only finite values")
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm):
        raise ValueError("state norm is not finite")
    error = abs(norm - 1.0)
    if error > tolerance:
        raise ValueError(f"state is not normalized: error={error}")
    return error


def positive_semidefinite_residual(
    rho: np.ndarray, tol: float = 1e-10
) -> float:
    """Return max(0,-lambda_min) for a finite Hermitian square matrix."""
    tolerance = _finite_nonnegative_tolerance(tol)
    matrix = np.asarray(rho, dtype=np.complex128)
    if (
        matrix.ndim != 2
        or matrix.shape[0] != matrix.shape[1]
        or matrix.shape[0] == 0
    ):
        raise ValueError("density operator must be a non-empty square matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("density operator must contain only finite values")

    hermiticity_error = float(
        np.linalg.norm(matrix - matrix.conj().T, ord="fro")
    )
    if not math.isfinite(hermiticity_error):
        raise ValueError("Hermiticity residual is not finite")
    if hermiticity_error > tolerance:
        raise ValueError(
            f"density operator is not Hermitian: residual={hermiticity_error}"
        )

    eigenvalues = np.linalg.eigvalsh(
        (matrix + matrix.conj().T) / 2.0
    )
    if not np.all(np.isfinite(eigenvalues)):
        raise ValueError("density-operator eigenvalues are not finite")

    residual = max(0.0, -float(np.min(eigenvalues)))
    if not math.isfinite(residual):
        raise ValueError("positive-semidefinite residual is not finite")
    return residual


def pure_state_fidelity(
    state_a: np.ndarray, state_b: np.ndarray
) -> float:
    """Squared overlap fidelity for normalized pure state vectors."""
    a = np.asarray(state_a, dtype=np.complex128)
    b = np.asarray(state_b, dtype=np.complex128)
    if a.ndim != 1 or b.ndim != 1 or a.shape != b.shape or a.size == 0:
        raise ValueError("pure states must be non-empty vectors of equal dimension")
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError("pure states must contain only finite values")

    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if not math.isfinite(na) or not math.isfinite(nb) or na == 0.0 or nb == 0.0:
        raise ValueError("pure states must have finite, nonzero norms")

    overlap = np.vdot(a / na, b / nb)
    value = float(abs(overlap) ** 2)
    return min(1.0, max(0.0, value))


def computational_basis_probabilities(state: np.ndarray) -> np.ndarray:
    """Return normalized computational-basis probabilities."""
    vector = np.asarray(state, dtype=np.complex128)
    if vector.ndim != 1 or vector.size == 0:
        raise ValueError("state must be a finite, non-empty vector")
    if not np.all(np.isfinite(vector)):
        raise ValueError("state must contain only finite values")

    norm_sq = float(np.vdot(vector, vector).real)
    if not math.isfinite(norm_sq) or norm_sq <= 0.0:
        raise ValueError("state must have a finite, positive squared norm")

    probabilities = np.abs(vector) ** 2 / norm_sq
    return probabilities.astype(float)
