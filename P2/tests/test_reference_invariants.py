"""Independent invariant tests for the canonical QFLPN P2 reference."""

from __future__ import annotations

import numpy as np
import pytest

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    HILBERT_DIM,
    c3x_operator,
    density_matrix,
    initial_state,
    is_unitary,
    reference_state,
    rotation_operator,
    transition_operator,
    validate_activations,
)

ATOL = 1e-12


def test_reference_state_has_correct_dimension_and_finite_values():
    state = reference_state()

    assert state.shape == (HILBERT_DIM,)
    assert np.all(np.isfinite(state))


def test_reference_state_is_normalized():
    state = reference_state()

    assert np.isclose(
        np.linalg.norm(state),
        1.0,
        atol=ATOL,
        rtol=0.0,
    )


def test_probabilities_are_nonnegative_and_conserved():
    state = reference_state()
    probabilities = np.abs(state) ** 2

    assert np.all(probabilities >= 0.0)
    assert np.isclose(
        probabilities.sum(),
        1.0,
        atol=ATOL,
        rtol=0.0,
    )


def test_rotation_operator_is_unitary():
    operator = rotation_operator(DEFAULT_ACTIVATIONS)

    assert operator.shape == (16, 16)
    assert is_unitary(operator, atol=ATOL)


def test_c3x_operator_is_unitary_and_involutory():
    operator = c3x_operator()
    identity = np.eye(16, dtype=np.complex128)

    assert is_unitary(operator, atol=ATOL)
    assert np.allclose(
        operator @ operator,
        identity,
        atol=ATOL,
        rtol=0.0,
    )


def test_complete_transition_operator_is_unitary():
    operator = transition_operator(DEFAULT_ACTIVATIONS)

    assert is_unitary(operator, atol=ATOL)


def test_transition_operator_maps_initial_state_to_reference_state():
    operator = transition_operator(DEFAULT_ACTIVATIONS)
    initial = initial_state()
    expected = reference_state(DEFAULT_ACTIVATIONS)

    actual = operator @ initial

    assert np.allclose(
        actual,
        expected,
        atol=ATOL,
        rtol=0.0,
    )


def test_density_matrix_is_hermitian():
    state = reference_state()
    rho = density_matrix(state)

    assert np.allclose(
        rho,
        rho.conj().T,
        atol=ATOL,
        rtol=0.0,
    )


def test_density_matrix_has_unit_trace():
    rho = density_matrix(reference_state())

    assert abs(np.trace(rho).imag) <= ATOL
    assert np.isclose(
        np.trace(rho).real,
        1.0,
        atol=ATOL,
        rtol=0.0,
    )


def test_density_matrix_is_positive_semidefinite():
    rho = density_matrix(reference_state())
    eigenvalues = np.linalg.eigvalsh(rho)

    assert np.min(eigenvalues) >= -ATOL


def test_pure_state_density_matrix_is_idempotent():
    rho = density_matrix(reference_state())

    assert np.allclose(
        rho @ rho,
        rho,
        atol=ATOL,
        rtol=0.0,
    )


def test_pure_state_density_matrix_has_unit_purity():
    rho = density_matrix(reference_state())
    purity = float(np.trace(rho @ rho).real)

    assert np.isclose(
        purity,
        1.0,
        atol=ATOL,
        rtol=0.0,
    )


def test_density_matrix_is_rank_one_with_one_unit_eigenvalue():
    rho = density_matrix(reference_state())
    eigenvalues = np.linalg.eigvalsh(rho)

    assert np.isclose(
        eigenvalues[-1],
        1.0,
        atol=ATOL,
        rtol=0.0,
    )

    assert np.all(np.abs(eigenvalues[:-1]) <= ATOL)


def test_activation_validation_rejects_boolean_values():
    with pytest.raises(TypeError):
        validate_activations((True, 0.90, 0.45, 0.70))


def test_activation_validation_rejects_nonfinite_values():
    with pytest.raises(ValueError):
        validate_activations((0.85, np.nan, 0.45, 0.70))


def test_activation_validation_rejects_values_outside_unit_interval():
    with pytest.raises(ValueError):
        validate_activations((0.85, 1.10, 0.45, 0.70))


def test_activation_validation_requires_exactly_four_values():
    with pytest.raises(ValueError):
        validate_activations((0.85, 0.90, 0.45))


def test_initial_state_is_the_zero_computational_basis_state():
    state = initial_state()
    expected = np.zeros(16, dtype=np.complex128)
    expected[0] = 1.0

    assert np.array_equal(state, expected)
