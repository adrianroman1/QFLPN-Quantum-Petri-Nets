"""Tests for QFLPN density-matrix construction and properties."""

from __future__ import annotations

import numpy as np
import pytest

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    HILBERT_DIM,
    density_matrix,
    reference_state,
)


ATOL = 1e-10


def assert_density_matrix_properties(rho: np.ndarray) -> None:
    """Check basic mathematical properties of a density matrix."""
    assert rho.shape == (HILBERT_DIM, HILBERT_DIM)

    assert np.allclose(
        rho,
        rho.conj().T,
        atol=ATOL,
        rtol=0.0,
    )

    assert np.isclose(
        np.trace(rho),
        1.0,
        atol=ATOL,
        rtol=0.0,
    )

    eigenvalues = np.linalg.eigvalsh(rho)

    assert np.min(eigenvalues) >= -ATOL


def test_density_matrix_has_expected_shape():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = density_matrix(state)

    assert rho.shape == (16, 16)


def test_density_matrix_is_hermitian():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = density_matrix(state)

    assert np.allclose(
        rho,
        rho.conj().T,
        atol=ATOL,
        rtol=0.0,
    )


def test_density_matrix_has_unit_trace():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = density_matrix(state)

    assert np.isclose(
        np.trace(rho),
        1.0,
        atol=ATOL,
        rtol=0.0,
    )


def test_density_matrix_is_positive_semidefinite():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = density_matrix(state)

    eigenvalues = np.linalg.eigvalsh(rho)

    assert np.min(eigenvalues) >= -ATOL


def test_density_matrix_is_rank_one_for_pure_state():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = density_matrix(state)

    eigenvalues = np.linalg.eigvalsh(rho)
    numerical_rank = np.count_nonzero(eigenvalues > ATOL)

    assert numerical_rank == 1


def test_density_matrix_matches_outer_product():
    state = reference_state(DEFAULT_ACTIVATIONS)
    expected = np.outer(state, state.conj())

    actual = density_matrix(state)

    assert np.allclose(
        actual,
        expected,
        atol=ATOL,
        rtol=0.0,
    )


def test_density_matrix_is_idempotent_for_pure_state():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = density_matrix(state)

    assert np.allclose(
        rho @ rho,
        rho,
        atol=ATOL,
        rtol=0.0,
    )


def test_pure_state_purity_is_one():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = density_matrix(state)

    purity = np.trace(rho @ rho).real

    assert np.isclose(
        purity,
        1.0,
        atol=ATOL,
        rtol=0.0,
    )


def test_density_matrix_rejects_wrong_state_shape():
    invalid_state = np.zeros(8, dtype=np.complex128)

    with pytest.raises((ValueError, TypeError)):
        density_matrix(invalid_state)


@pytest.mark.parametrize(
    "invalid_state",
    [
        np.full(16, np.nan, dtype=np.complex128),
        np.full(16, np.inf, dtype=np.complex128),
    ],
)
def test_density_matrix_rejects_non_finite_state(invalid_state):
    with pytest.raises((ValueError, TypeError)):
        density_matrix(invalid_state)


def test_density_matrix_rejects_unnormalized_state():
    invalid_state = np.zeros(16, dtype=np.complex128)
    invalid_state[0] = 2.0

    with pytest.raises((ValueError, TypeError)):
        density_matrix(invalid_state)


def test_density_matrix_does_not_modify_input_state():
    state = reference_state(DEFAULT_ACTIVATIONS)
    original = state.copy()

    density_matrix(state)

    assert np.array_equal(state, original)
