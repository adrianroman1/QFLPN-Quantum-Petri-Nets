"""Mathematical validation of the canonical QFLPN four-qubit model."""

from __future__ import annotations

import numpy as np

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    HILBERT_DIM,
    density_matrix,
    fuzzy_to_angle,
    reference_state,
    validate_activations,
)

ATOL = 1e-12


def computational_basis_probabilities(state: np.ndarray) -> np.ndarray:
    vector = np.asarray(state, dtype=np.complex128)
    if vector.shape != (HILBERT_DIM,):
        raise ValueError("State must have shape (16,).")
    if not np.all(np.isfinite(vector)):
        raise ValueError("State contains non-finite values.")
    return np.abs(vector) ** 2


def pure_state_fidelity(
    state_a: np.ndarray, state_b: np.ndarray
) -> float:
    a = np.asarray(state_a, dtype=np.complex128)
    b = np.asarray(state_b, dtype=np.complex128)
    if a.shape != (HILBERT_DIM,) or b.shape != (HILBERT_DIM,):
        raise ValueError("Both states must have shape (16,).")
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError("States must contain only finite values.")
    if not np.isclose(np.linalg.norm(a), 1.0, atol=ATOL, rtol=0.0):
        raise ValueError("First state must be normalized.")
    if not np.isclose(np.linalg.norm(b), 1.0, atol=ATOL, rtol=0.0):
        raise ValueError("Second state must be normalized.")
    return float(abs(np.vdot(a, b)) ** 2)


def validate_fuzzy_quantum_mapping(
    memberships: np.ndarray,
) -> float:
    values = validate_activations(memberships)
    errors = []
    for mu in values:
        theta = fuzzy_to_angle(mu)
        probability_one = float(np.sin(theta / 2.0) ** 2)
        errors.append(abs(probability_one - mu))
    return max(errors, default=0.0)


def validate_state(state: np.ndarray) -> tuple[float, float]:
    probabilities = computational_basis_probabilities(state)
    norm_error = abs(float(np.linalg.norm(state)) - 1.0)
    probability_error = abs(float(probabilities.sum()) - 1.0)
    return norm_error, probability_error


def validate_density_matrix(
    state: np.ndarray,
) -> tuple[float, float, float]:
    rho = density_matrix(state)
    hermiticity_error = float(
        np.linalg.norm(rho - rho.conj().T, ord="fro")
    )
    trace_error = float(abs(np.trace(rho) - 1.0))
    minimum_eigenvalue = float(np.min(np.linalg.eigvalsh(rho)))
    return hermiticity_error, trace_error, minimum_eigenvalue


def validate_fidelity(state: np.ndarray) -> float:
    return abs(pure_state_fidelity(state, state) - 1.0)


def main() -> int:
    memberships = np.asarray(DEFAULT_ACTIVATIONS, dtype=float)
    state = reference_state(memberships)

    mapping_error = validate_fuzzy_quantum_mapping(memberships)
    norm_error, probability_error = validate_state(state)
    hermiticity_error, trace_error, min_eigenvalue = (
        validate_density_matrix(state)
    )
    fidelity_error = validate_fidelity(state)

    errors = {
        "mapping": mapping_error,
        "normalization": norm_error,
        "probability conservation": probability_error,
        "Hermiticity": hermiticity_error,
        "trace": trace_error,
        "self-fidelity": fidelity_error,
    }

    for name, error in errors.items():
        print(f"{name:28s}: {error:.3e}")

    print(f"{'minimum density eigenvalue':28s}: {min_eigenvalue:.3e}")

    failed = any(error > ATOL for error in errors.values())
    failed |= min_eigenvalue < -ATOL

    print("STATUS:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
