"""Independent scalar-loop implementation used by R14 comparisons.

This module intentionally imports no P1 implementation module.
"""
import math
import numpy as np


def independent_angle(mu):
    x = float(mu)
    if not math.isfinite(x) or x < 0.0 or x > 1.0:
        raise ValueError("mu outside finite [0,1]")
    return 2.0 * math.asin(math.sqrt(x))


def independent_ry(theta):
    t = float(theta)
    if not math.isfinite(t):
        raise ValueError("theta must be finite")
    return np.array([[math.cos(t / 2), -math.sin(t / 2)],
                     [math.sin(t / 2), math.cos(t / 2)]], dtype=np.complex128)


def independent_c3x():
    matrix = np.zeros((16, 16), dtype=np.complex128)
    for col in range(16):
        row = col ^ 1 if (col & 14) == 14 else col
        matrix[row, col] = 1.0
    return matrix


def independent_global_operator(memberships):
    if len(memberships) != 4:
        raise ValueError("four memberships required")
    local = np.array([[1.0 + 0j]])
    for membership in memberships:
        local = np.kron(local, independent_ry(independent_angle(membership)))
    return independent_c3x() @ local


def independent_density_evolution(operator, state):
    vector = np.asarray(state, dtype=np.complex128)
    norm = math.sqrt(float(np.vdot(vector, vector).real))
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("invalid state norm")
    vector = vector / norm
    rho = np.outer(vector, vector.conj())
    u = np.asarray(operator, dtype=np.complex128)
    return u @ rho @ u.conj().T
