"""Independent manuscript-alignment tests for QFLPN P2.

This module reconstructs the published four-qubit instance directly
from the mathematical definitions. It deliberately does not import
the P2 reference implementation.

Basis convention:
    Big-endian |q1 q2 q3 q4>, indices 0,...,15.

Canonical C3X:
    Controls q1,q2,q3; target q4.
    Swaps basis indices 14 and 15.

Alternative C3X:
    Controls q2,q3,q4; target q1.
    Swaps basis indices 7 and 15.

The operator-order experiment in test_ordering_sensitivity.py is
a separate experiment and is intentionally not modified here.
"""

from __future__ import annotations

import numpy as np


# Published canonical activations.
LAMBDAS = np.array(
    [0.85, 0.90, 0.45, 0.70],
    dtype=np.float64,
)

# Published rounded results.
EXPECTED_FIDELITY = 0.880745353014653
EXPECTED_TVD = 0.198450
EXPECTED_PURITY = 0.927763
EXPECTED_ENTROPY_BITS = 0.230836
EXPECTED_EIGENVALUES = np.array(
    [0.03752698, 0.96247302],
    dtype=np.float64,
)

# Strict numerical tolerance for independently reconstructed values.
ATOL = 1e-10

# The manuscript reports rounded decimal values.
PUBLISHED_ATOL = 1e-6


def independent_initial_state() -> np.ndarray:
    """Construct the tensor-product RY state from lambda values.

    Since:
        theta_i = 2 asin(sqrt(lambda_i))

    then:
        RY(theta_i)|0>
        = sqrt(1-lambda_i)|0> + sqrt(lambda_i)|1>.
    """
    state = np.array([1.0 + 0.0j], dtype=np.complex128)

    for lam in LAMBDAS:
        single_qubit_state = np.array(
            [
                np.sqrt(1.0 - lam),
                np.sqrt(lam),
            ],
            dtype=np.complex128,
        )
        state = np.kron(state, single_qubit_state)

    return state


def apply_basis_swap(
    state: np.ndarray,
    first: int,
    second: int,
) -> np.ndarray:
    """Apply a basis permutation by exchanging two amplitudes."""
    result = np.asarray(state, dtype=np.complex128).copy()

    if result.shape != (16,):
        raise ValueError("Expected a 16-dimensional state vector.")

    result[first], result[second] = (
        result[second],
        result[first],
    )

    return result


def canonical_state() -> np.ndarray:
    """Apply canonical C3X: target q4, swap indices 14 and 15."""
    return apply_basis_swap(
        independent_initial_state(),
        14,
        15,
    )


def alternative_target_state() -> np.ndarray:
    """Apply alternative C3X: target q1, swap indices 7 and 15."""
    return apply_basis_swap(
        independent_initial_state(),
        7,
        15,
    )


def squared_fidelity(
    state_a: np.ndarray,
    state_b: np.ndarray,
) -> float:
    """Pure-state fidelity F = |<a|b>|^2."""
    return float(abs(np.vdot(state_a, state_b)) ** 2)


def total_variation_distance(
    state_a: np.ndarray,
    state_b: np.ndarray,
) -> float:
    """TVD between computational-basis probability distributions."""
    probabilities_a = np.abs(state_a) ** 2
    probabilities_b = np.abs(state_b) ** 2

    return float(
        0.5 * np.sum(
            np.abs(probabilities_a - probabilities_b)
        )
    )


def reduced_density_q4(state: np.ndarray) -> np.ndarray:
    """Trace out q1,q2,q3 and retain q4.

    The tensor is indexed as psi[q1,q2,q3,q4].
    The resulting matrix has indices (q4, q4').
    """
    vector = np.asarray(state, dtype=np.complex128)

    if vector.shape != (16,):
        raise ValueError("Expected a 16-dimensional state vector.")

    if not np.all(np.isfinite(vector)):
        raise ValueError("State contains non-finite values.")

    if not np.isclose(
        np.linalg.norm(vector),
        1.0,
        atol=ATOL,
        rtol=0.0,
    ):
        raise ValueError("State must be normalized.")

    tensor = vector.reshape(2, 2, 2, 2)

    return np.einsum(
        "abcx,abcy->xy",
        tensor,
        tensor.conj(),
    )


def entropy_bits(eigenvalues: np.ndarray) -> float:
    """Von Neumann entropy in bits."""
    values = np.asarray(eigenvalues, dtype=np.float64)

    if np.any(values < -ATOL):
        raise ValueError("Negative density-matrix eigenvalue.")

    values = np.clip(values, 0.0, None)
    positive = values[values > 0.0]

    return float(
        -np.sum(positive * np.log2(positive))
    )


# ---------------------------------------------------------------------
# Ten independent manuscript-alignment tests
# ---------------------------------------------------------------------


def test_01_independent_initial_state_is_normalized():
    """The tensor-product RY state must have unit norm."""
    state = independent_initial_state()

    assert state.shape == (16,)
    assert np.all(np.isfinite(state))
    assert np.isclose(
        np.linalg.norm(state),
        1.0,
        atol=ATOL,
        rtol=0.0,
    )


def test_02_activation_encoding_matches_published_lambdas():
    """The RY encoding must reproduce each lambda as |amplitude_1|^2."""
    state = independent_initial_state()

    tensor = state.reshape(2, 2, 2, 2)

    for qubit_index, lam in enumerate(LAMBDAS):
        marginal = np.sum(
            np.abs(tensor) ** 2,
            axis=tuple(
                index
                for index in range(4)
                if index != qubit_index
            ),
        )

        assert np.isclose(
            marginal[1],
            lam,
            atol=ATOL,
            rtol=0.0,
        )


def test_03_canonical_target_convention_swaps_14_and_15():
    """Canonical C3X must exchange |1110> and |1111>."""
    initial = independent_initial_state()
    canonical = canonical_state()

    expected = initial.copy()
    expected[14], expected[15] = (
        initial[15],
        initial[14],
    )

    assert np.allclose(
        canonical,
        expected,
        atol=ATOL,
        rtol=0.0,
    )

    assert np.isclose(canonical[14], initial[15])
    assert np.isclose(canonical[15], initial[14])


def test_04_alternative_target_convention_swaps_7_and_15():
    """Alternative target q1 must exchange |0111> and |1111>."""
    initial = independent_initial_state()
    alternative = alternative_target_state()

    expected = initial.copy()
    expected[7], expected[15] = (
        initial[15],
        initial[7],
    )

    assert np.allclose(
        alternative,
        expected,
        atol=ATOL,
        rtol=0.0,
    )

    assert np.isclose(alternative[7], initial[15])
    assert np.isclose(alternative[15], initial[7])


def test_05_canonical_and_alternative_states_are_normalized():
    """Both target conventions must preserve state norm."""
    canonical = canonical_state()
    alternative = alternative_target_state()

    assert np.isclose(
        np.linalg.norm(canonical),
        1.0,
        atol=ATOL,
        rtol=0.0,
    )

    assert np.isclose(
        np.linalg.norm(alternative),
        1.0,
        atol=ATOL,
        rtol=0.0,
    )


def test_06_manuscript_target_convention_fidelity():
    """Reproduce the manuscript's squared pure-state overlap."""
    canonical = canonical_state()
    alternative = alternative_target_state()

    fidelity = squared_fidelity(
        canonical,
        alternative,
    )

    assert np.isclose(
        fidelity,
        EXPECTED_FIDELITY,
        atol=PUBLISHED_ATOL,
        rtol=0.0,
    )


def test_07_manuscript_target_convention_tvd():
    """Reproduce the manuscript's computational-basis TVD."""
    canonical = canonical_state()
    alternative = alternative_target_state()

    tvd = total_variation_distance(
        canonical,
        alternative,
    )

    assert np.isclose(
        tvd,
        EXPECTED_TVD,
        atol=PUBLISHED_ATOL,
        rtol=0.0,
    )


def test_08_q4_reduced_density_matrix_is_physical():
    """The q4 reduced density matrix must be Hermitian, PSD and trace one."""
    rho4 = reduced_density_q4(canonical_state())

    assert rho4.shape == (2, 2)

    assert np.allclose(
        rho4,
        rho4.conj().T,
        atol=ATOL,
        rtol=0.0,
    )

    assert np.isclose(
        np.trace(rho4),
        1.0,
        atol=ATOL,
        rtol=0.0,
    )

    eigenvalues = np.linalg.eigvalsh(rho4)

    assert np.min(eigenvalues) >= -ATOL


def test_09_q4_spectrum_and_purity_match_manuscript():
    """Reproduce the published q4 spectrum and purity."""
    rho4 = reduced_density_q4(canonical_state())

    eigenvalues = np.linalg.eigvalsh(rho4)
    purity = float(np.trace(rho4 @ rho4).real)

    assert np.allclose(
        eigenvalues,
        EXPECTED_EIGENVALUES,
        atol=PUBLISHED_ATOL,
        rtol=0.0,
    )

    assert np.isclose(
        purity,
        EXPECTED_PURITY,
        atol=PUBLISHED_ATOL,
        rtol=0.0,
    )


def test_10_q4_von_neumann_entropy_matches_manuscript_in_bits():
    """Reproduce the published entropy using log base 2."""
    rho4 = reduced_density_q4(canonical_state())

    eigenvalues = np.linalg.eigvalsh(rho4)
    entropy = entropy_bits(eigenvalues)

    assert np.isclose(
        entropy,
        EXPECTED_ENTROPY_BITS,
        atol=PUBLISHED_ATOL,
        rtol=0.0,
    )
