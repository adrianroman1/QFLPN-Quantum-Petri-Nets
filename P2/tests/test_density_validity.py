"""Physical-validity tests for QFLPN density operators."""

from __future__ import annotations

import numpy as np
import pytest

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    density_matrix,
    reference_state,
)

ATOL = 1e-10


def test_density_matrix_has_expected_dimension():
    rho = density_matrix(reference_state(DEFAULT_ACTIVATIONS))
    assert rho.shape == (16, 16)


def test_density_matrix_is_hermitian():
    rho = density_matrix(reference_state(DEFAULT_ACTIVATIONS))
    assert np.allclose(rho, rho.conj().T, atol=ATOL, rtol=0.0)


def test_density_matrix_has_unit_trace():
    rho = density_matrix(reference_state(DEFAULT_ACTIVATIONS))
    assert np.isclose(np.trace(rho), 1.0, atol=ATOL, rtol=0.0)


def test_density_matrix_is_positive_semidefinite():
    rho = density_matrix(reference_state(DEFAULT_ACTIVATIONS))
    eigenvalues = np.linalg.eigvalsh(rho)
    assert float(np.min(eigenvalues)) >= -ATOL


def test_density_matrix_matches_state_vector_outer_product():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = density_matrix(state)
    expected = np.outer(state, state.conj())
    assert np.allclose(rho, expected, atol=ATOL, rtol=0.0)


def test_vector_and_density_expectation_values_agree():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = density_matrix(state)

    observable = np.diag(np.linspace(-1.0, 1.0, 16)).astype(np.complex128)

    vector_expectation = np.vdot(state, observable @ state)
    density_expectation = np.trace(rho @ observable)

    assert np.isclose(
        vector_expectation,
        density_expectation,
        atol=ATOL,
        rtol=0.0,
    )


@pytest.mark.parametrize(
    "bad_state",
    [
        np.zeros(8, dtype=np.complex128),
        np.full(16, np.nan, dtype=np.complex128),
        np.full(16, np.inf, dtype=np.complex128),
        np.full(16, 2.0, dtype=np.complex128),
    ],
)
def test_invalid_state_vectors_are_rejected(bad_state):
    with pytest.raises((ValueError, TypeError)):
        density_matrix(bad_state)
