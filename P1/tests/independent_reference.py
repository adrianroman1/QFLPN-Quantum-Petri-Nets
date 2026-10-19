"""Independent scalar-loop implementation used by P1 comparisons.

This module intentionally imports no P1 production implementation module.
"""
import math
from numbers import Real

import numpy as np


def _real(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a real numeric scalar")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def independent_angle(mu):
    x = _real(mu, "mu")
    if not 0.0 <= x <= 1.0:
        raise ValueError("mu outside finite [0,1]")
    return 2.0 * math.asin(math.sqrt(x))


def independent_ry(theta):
    t = _real(theta, "theta")
    return np.array(
        [
            [math.cos(t / 2.0), -math.sin(t / 2.0)],
            [math.sin(t / 2.0), math.cos(t / 2.0)],
        ],
        dtype=np.complex128,
    )


def independent_c3x():
    matrix = np.zeros((16, 16), dtype=np.complex128)
    for col in range(16):
        row = col ^ 1 if (col & 14) == 14 else col
        matrix[row, col] = 1.0
    return matrix


def independent_global_operator(memberships):
    values = tuple(memberships)
    if len(values) != 4:
        raise ValueError("four memberships required")

    local = np.array([[1.0 + 0j]])
    for membership in values:
        local = np.kron(
            local,
            independent_ry(independent_angle(membership)),
        )
    return independent_c3x() @ local


def independent_density_evolution(operator, state):
    vector = np.asarray(state, dtype=np.complex128)
    if vector.ndim != 1 or vector.size == 0:
        raise ValueError("state must be a non-empty vector")
    if not np.all(np.isfinite(vector)):
        raise ValueError("state must contain finite values")

    norm = math.sqrt(float(np.vdot(vector, vector).real))
    if not math.isfinite(norm) or norm == 0.0:
        raise ValueError("invalid state norm")

    vector = vector / norm
    rho = np.outer(vector, vector.conj())

    u = np.asarray(operator, dtype=np.complex128)
    if u.ndim != 2 or u.shape[0] != u.shape[1]:
        raise ValueError("operator must be square")
    if u.shape[1] != vector.size:
        raise ValueError("operator and state dimensions do not match")
    if not np.all(np.isfinite(u)):
        raise ValueError("operator must contain finite values")

    return u @ rho @ u.conj().T
