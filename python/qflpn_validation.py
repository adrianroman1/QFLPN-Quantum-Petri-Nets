"""
QFLPN Validation
================

Mathematical and numerical validation of the 4-qubit QFLPN reference model.

Checks:
- fuzzy -> quantum mapping
- normalization
- probability conservation
- density matrix properties
- fidelity
- numerical errors

No Monte Carlo.
"""

from __future__ import annotations

import numpy as np

from qflpn_reference import (
    computational_basis_probabilities,
    density_matrix,
    fuzzy_to_angle,
    pure_state_fidelity,
    reference_state,
    ry_state,
)


REFERENCE_MEMBERSHIPS = np.array(
    [0.85, 0.90, 0.45, 0.70],
    dtype=float,
)


def validate_fuzzy_quantum_mapping(
    memberships: np.ndarray,
) -> float:
    errors = []

    print("\n[1] Fuzzy -> quantum mapping")

    for mu in memberships:
        state = ry_state(float(mu))
        probability_one = abs(state[1]) ** 2
        error = abs(probability_one - mu)
        errors.append(error)

        print(
            f"mu={mu:.6f} | "
            f"P(|1>)={probability_one:.12f} | "
            f"error={error:.3e}"
        )

    return float(max(errors))


def validate_state(state: np.ndarray) -> tuple[float, float]:
    norm = np.linalg.norm(state)
    probabilities = computational_basis_probabilities(state)
    probability_sum = float(probabilities.sum())

    norm_error = abs(norm - 1.0)
    probability_error = abs(probability_sum - 1.0)

    print("\n[2] State validation")
    print(f"Norm                 = {norm:.15f}")
    print(f"Normalization error  = {norm_error:.3e}")
    print(f"Probability sum      = {probability_sum:.15f}")
    print(f"Probability error    = {probability_error:.3e}")

    return norm_error, probability_error


def validate_density_matrix(
    state: np.ndarray,
) -> tuple[float, float]:
    rho = density_matrix(state)

    hermiticity_error = np.linalg.norm(
        rho - rho.conj().T,
        ord="fro",
    )

    trace_error = abs(np.trace(rho) - 1.0)

    print("\n[3] Density matrix validation")
    print(f"Shape                = {rho.shape}")
    print(f"Hermiticity error    = {hermiticity_error:.3e}")
    print(f"Trace                 = {np.trace(rho).real:.15f}")
    print(f"Trace error           = {trace_error:.3e}")

    return float(hermiticity_error), float(trace_error)


def validate_fidelity(state: np.ndarray) -> float:
    fidelity = pure_state_fidelity(state, state)
    fidelity_error = abs(fidelity - 1.0)

    print("\n[4] Fidelity validation")
    print(f"Self-fidelity        = {fidelity:.15f}")
    print(f"Fidelity error       = {fidelity_error:.3e}")

    return fidelity_error


def main() -> None:
    print("=" * 60)
    print("QFLPN 4-QUBIT MATHEMATICAL VALIDATION")
    print("=" * 60)

    print("\nReference memberships:")
    print(REFERENCE_MEMBERSHIPS)

    mapping_error = validate_fuzzy_quantum_mapping(
        REFERENCE_MEMBERSHIPS
    )

    state = reference_state(
        REFERENCE_MEMBERSHIPS
    )

    norm_error, probability_error = validate_state(
        state
    )

    hermiticity_error, trace_error = (
        validate_density_matrix(state)
    )

    fidelity_error = validate_fidelity(state)

    max_error = max(
        mapping_error,
        norm_error,
        probability_error,
        hermiticity_error,
        trace_error,
        fidelity_error,
    )

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    print(f"Maximum numerical error = {max_error:.3e}")

    if max_error <= 1e-12:
        print("STATUS: PASS")
    else:
        print("STATUS: REVIEW REQUIRED")


if __name__ == "__main__":
    main()
