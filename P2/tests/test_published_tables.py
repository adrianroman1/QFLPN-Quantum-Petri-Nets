"""Independent regression tests for numerical values published in P2.

This module deliberately reconstructs the four-qubit state without importing
the production implementation from qflpn_reference.
"""

from __future__ import annotations

import numpy as np


ATOL = 6e-9

LAMBDAS = np.array(
    [0.85, 0.90, 0.45, 0.70],
    dtype=np.float64,
)

EXPECTED_AMPLITUDES = np.array(
    [
        0.04974937,
        0.07599342,
        0.04500000,
        0.06873864,
        0.14924812,
        0.22798026,
        0.13500000,
        0.20621591,
        0.11842719,
        0.18090053,
        0.10712143,
        0.16363068,
        0.35528158,
        0.54270158,
        0.49089205,
        0.32136428,
    ],
    dtype=np.float64,
)

EXPECTED_PROBABILITIES = np.array(
    [
        0.002475,
        0.005775,
        0.002025,
        0.004725,
        0.022275,
        0.051975,
        0.018225,
        0.042525,
        0.014025,
        0.032725,
        0.011475,
        0.026775,
        0.126225,
        0.294525,
        0.240975,
        0.103275,
    ],
    dtype=np.float64,
)

EXPECTED_RHO_Q4 = np.array(
    [
        [0.4377000000, 0.4582575695],
        [0.4582575695, 0.5623000000],
    ],
    dtype=np.float64,
)


def independent_product_state() -> np.ndarray:
    """Construct the tensor-product RY state from the published lambdas."""
    local_states = []

    for activation in LAMBDAS:
        local_states.append(
            np.array(
                [
                    np.sqrt(1.0 - activation),
                    np.sqrt(activation),
                ],
                dtype=np.float64,
            )
        )

    state = local_states[0]

    for local_state in local_states[1:]:
        state = np.kron(state, local_state)

    return np.asarray(state, dtype=np.complex128)


def independent_c3x(state: np.ndarray) -> np.ndarray:
    """Apply C3X with q1,q2,q3 as controls and q4 as target."""
    result = np.asarray(state, dtype=np.complex128).copy()

    if result.shape != (16,):
        raise ValueError("Expected a 16-dimensional state vector.")

    result[14], result[15] = result[15], result[14]

    return result


def independent_reference_state() -> np.ndarray:
    """Reconstruct the manuscript state without production-code imports."""
    return independent_c3x(independent_product_state())


def independent_reduced_density_q4(state: np.ndarray) -> np.ndarray:
    """Trace out q1,q2,q3 and retain q4."""
    vector = np.asarray(state, dtype=np.complex128)

    if vector.shape != (16,):
        raise ValueError("Expected a 16-dimensional state vector.")

    tensor = vector.reshape(8, 2)

    return tensor.conj().T @ tensor


def test_independent_state_is_normalized():
    state = independent_reference_state()

    assert np.isclose(
        np.linalg.norm(state),
        1.0,
        atol=1e-12,
        rtol=0.0,
    )


def test_published_state_amplitudes():
    state = independent_reference_state()

    assert np.allclose(
        state.real,
        EXPECTED_AMPLITUDES,
        atol=ATOL,
        rtol=0.0,
    )

    assert np.allclose(
        state.imag,
        0.0,
        atol=1e-12,
        rtol=0.0,
    )


def test_published_probabilities():
    probabilities = np.abs(independent_reference_state()) ** 2

    assert np.allclose(
        probabilities,
        EXPECTED_PROBABILITIES,
        atol=ATOL,
        rtol=0.0,
    )

    assert np.isclose(
        probabilities.sum(),
        1.0,
        atol=1e-12,
        rtol=0.0,
    )


def test_published_q4_reduced_density_matrix():
    rho_q4 = independent_reduced_density_q4(
        independent_reference_state()
    )

    assert np.allclose(
        rho_q4,
        EXPECTED_RHO_Q4,
        atol=ATOL,
        rtol=0.0,
    )


def test_published_q4_density_matrix_is_physical():
    rho_q4 = independent_reduced_density_q4(
        independent_reference_state()
    )

    assert np.allclose(
        rho_q4,
        rho_q4.conj().T,
        atol=1e-12,
        rtol=0.0,
    )

    assert np.isclose(
        np.trace(rho_q4).real,
        1.0,
        atol=1e-12,
        rtol=0.0,
    )

    assert np.min(np.linalg.eigvalsh(rho_q4)) >= -1e-12
