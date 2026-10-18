"""
P1 mathematical and numerical validation.

Checks the fuzzy-to-quantum encoding, four-qubit state conventions,
density-matrix properties, C^3X action, operator unitarity and fidelity.

This numerical validation does not prove the complete Petri-net semantics.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from qflpn_reference import (
    computational_basis_probabilities,
    density_matrix,
    fuzzy_to_angle,
    positive_semidefinite_residual,
    pure_state_fidelity,
    reference_state,
    ry_state,
)
from qflpn_transition_operator import (
    c3x,
    qflpn_transition_operator,
    validate_unitarity,
)

REFERENCE_MEMBERSHIPS = np.array([0.85, 0.90, 0.45, 0.70], dtype=float)
TOLERANCE = 1e-12


def validate_fuzzy_quantum_mapping(memberships: np.ndarray) -> float:
    errors = []
    print("\n[1] Fuzzy -> quantum RY mapping")

    for mu in memberships:
        theta = fuzzy_to_angle(float(mu))
        state = ry_state(theta)
        probability_one = float(abs(state[1]) ** 2)
        error = abs(probability_one - float(mu))
        errors.append(error)

        print(
            f"mu={mu:.6f} | theta={theta:.12f} rad "
            f"| P(|1>)={probability_one:.12f} | error={error:.3e}"
        )

    return float(max(errors))


def validate_state(state: np.ndarray) -> tuple[float, float]:
    norm_error = abs(float(np.linalg.norm(state)) - 1.0)
    probabilities = computational_basis_probabilities(state)
    probability_sum = float(probabilities.sum())
    probability_error = abs(probability_sum - 1.0)

    print("\n[2] State validation")
    print(f"Norm error        = {norm_error:.3e}")
    print(f"Probability sum   = {probability_sum:.15f}")
    print(f"Probability error = {probability_error:.3e}")

    return norm_error, probability_error


def validate_density_matrix(
    state: np.ndarray,
) -> tuple[float, float, float]:
    rho = density_matrix(state)

    hermiticity_error = float(
        np.linalg.norm(rho - rho.conj().T, ord="fro")
    )
    trace_error = float(abs(np.trace(rho) - 1.0))
    psd_residual = positive_semidefinite_residual(rho)

    print("\n[3] Density-matrix validation")
    print(f"Shape             = {rho.shape}")
    print(f"Hermiticity error = {hermiticity_error:.3e}")
    print(f"Trace             = {np.trace(rho).real:.15f}")
    print(f"Trace error       = {trace_error:.3e}")
    print(f"PSD residual      = {psd_residual:.3e}")

    return hermiticity_error, trace_error, psd_residual


def validate_c3x() -> float:
    operator = c3x()

    if operator.shape != (16, 16):
        raise AssertionError(
            f"C^3X must be 16x16, got {operator.shape}."
        )

    expected = np.eye(16, dtype=np.complex128)
    expected[14, 14] = 0.0
    expected[15, 15] = 0.0
    expected[14, 15] = 1.0
    expected[15, 14] = 1.0

    action_error = float(np.max(np.abs(operator - expected)))
    unitarity_error = validate_unitarity(operator)
    involution_error = float(
        np.linalg.norm(
            operator @ operator - np.eye(16),
            ord="fro",
        )
    )

    print("\n[4] C^3X reference operator")
    print(f"Basis-action error = {action_error:.3e}")
    print(f"Unitarity error    = {unitarity_error:.3e}")
    print(f"Involution error   = {involution_error:.3e}")

    return max(action_error, unitarity_error, involution_error)


def validate_global_transition(
    memberships: tuple[float, ...],
) -> float:
    operator = qflpn_transition_operator(memberships)
    error = validate_unitarity(operator)

    print("\n[5] Global reference transition")
    print(f"Dimension       = {operator.shape}")
    print(f"Unitarity error = {error:.3e}")

    return error


def validate_fidelity(state: np.ndarray) -> float:
    fidelity = pure_state_fidelity(state, state)
    error = abs(fidelity - 1.0)

    print("\n[6] Fidelity sanity check")
    print(f"Self-fidelity  = {fidelity:.15f}")
    print(f"Fidelity error = {error:.3e}")

    return error


def validate_psd_diagnostic_guards() -> None:
    nonhermitian = np.array(
        [[1.0, 1.0], [0.0, 1.0]],
        dtype=np.complex128,
    )

    try:
        positive_semidefinite_residual(nonhermitian)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "PSD diagnostic must reject non-Hermitian input."
        )

    known_indefinite = np.diag([-1e-7, 1.0]).astype(
        np.complex128
    )
    residual = positive_semidefinite_residual(known_indefinite)

    if not np.isclose(
        residual,
        1e-7,
        atol=1e-12,
        rtol=0.0,
    ):
        raise AssertionError(
            f"PSD residual mismatch: expected 1e-7, got {residual}."
        )


def main() -> None:
    print("=" * 64)
    print("QFLPN P1 — PREPRINT-ALIGNED NUMERICAL VALIDATION")
    print("=" * 64)

    mapping_error = validate_fuzzy_quantum_mapping(
        REFERENCE_MEMBERSHIPS
    )

    state = reference_state(REFERENCE_MEMBERSHIPS)

    norm_error, probability_error = validate_state(state)

    hermiticity_error, trace_error, psd_residual = (
        validate_density_matrix(state)
    )

    c3x_error = validate_c3x()

    transition_error = validate_global_transition(
        tuple(REFERENCE_MEMBERSHIPS)
    )

    fidelity_error = validate_fidelity(state)

    validate_psd_diagnostic_guards()

    maximum_error = max(
        mapping_error,
        norm_error,
        probability_error,
        hermiticity_error,
        trace_error,
        psd_residual,
        c3x_error,
        transition_error,
        fidelity_error,
    )

    print("\n" + "=" * 64)
    print(f"Maximum numerical residual = {maximum_error:.3e}")

    if maximum_error > TOLERANCE:
        raise AssertionError(
            f"P1 validation failed: {maximum_error:.3e} "
            f"> {TOLERANCE:.3e}"
        )

    print("STATUS: PASS")


if __name__ == "__main__":
    main()
