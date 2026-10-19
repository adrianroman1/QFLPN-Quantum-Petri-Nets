"""Independent numerical checks for the published P2 tables.

This module deliberately does not import qflpn_reference.
It reconstructs the mathematical instance from the manuscript
definitions and checks the published rounded numerical values.
"""

from __future__ import annotations

import numpy as np

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

ATOL_AMPLITUDES = 6e-9
ATOL_PROBABILITIES = 5e-7
ATOL_DENSITY = 5e-10


def independent_initial_state() -> np.ndarray:
    """Construct the tensor-product state from the published lambdas."""
    state = np.array([1.0], dtype=np.float64)

    for value in LAMBDAS:
        local = np.array(
            [
                np.sqrt(1.0 - value),
                np.sqrt(value),
            ],
            dtype=np.float64,
        )
        state = np.kron(state, local)

    return state


def independent_canonical_state() -> np.ndarray:
    """Apply C3X with controls q1,q2,q3 and target q4."""
    state = independent_initial_state()

    # Big-endian |q1 q2 q3 q4> convention.
    # C3X exchanges |1110> and |1111>.
    state[14], state[15] = state[15], state[14]

    return state


def independent_reduced_density_q4(
    state: np.ndarray,
) -> np.ndarray:
    """Trace out q1,q2,q3 and retain q4."""
    tensor = np.asarray(
        state,
        dtype=np.complex128,
    ).reshape(8, 2)

    return tensor.conj().T @ tensor


def test_published_table_11_amplitudes():
    """Check the sixteen rounded amplitudes in manuscript Table 11."""
    actual = independent_canonical_state()

    assert actual.shape == (16,)
    assert np.all(np.isfinite(actual))

    np.testing.assert_allclose(
        actual.real,
        EXPECTED_AMPLITUDES,
        atol=ATOL_AMPLITUDES,
        rtol=0.0,
    )

    np.testing.assert_allclose(
        actual.imag,
        np.zeros(16),
        atol=1e-14,
        rtol=0.0,
    )


def test_published_table_3_probabilities():
    """Check all sixteen rounded probabilities in manuscript Table 3."""
    state = independent_canonical_state()
    actual = np.abs(state) ** 2

    assert actual.shape == (16,)
    assert np.all(actual >= 0.0)

    np.testing.assert_allclose(
        actual,
        EXPECTED_PROBABILITIES,
        atol=ATOL_PROBABILITIES,
        rtol=0.0,
    )

    assert np.isclose(
        actual.sum(),
        1.0,
        atol=1e-12,
        rtol=0.0,
    )


def test_published_reduced_density_q4():
    """Check the published reduced density matrix for subsystem q4."""
    state = independent_canonical_state()
    rho4 = independent_reduced_density_q4(state)

    assert rho4.shape == (2, 2)

    np.testing.assert_allclose(
        rho4.real,
        EXPECTED_RHO_Q4,
        atol=ATOL_DENSITY,
        rtol=0.0,
    )

    np.testing.assert_allclose(
        rho4.imag,
        np.zeros((2, 2)),
        atol=1e-14,
        rtol=0.0,
    )

    assert np.isclose(
        np.trace(rho4).real,
        1.0,
        atol=1e-12,
        rtol=0.0,
    )

    assert np.min(np.linalg.eigvalsh(rho4)) >= -1e-12
