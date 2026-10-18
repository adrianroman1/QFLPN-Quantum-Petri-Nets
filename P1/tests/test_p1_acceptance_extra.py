"""Additional acceptance tests for the QFLPN P1 numerical reference layer.

These tests complement test_p1_remediation.py. They do not replace the
existing validation suite or claim to validate the complete Petri-net model.
"""

import numpy as np
import pytest

from P1.code.qflpn_reference import (
    computational_basis_probabilities,
    density_matrix,
    fuzzy_to_angle,
    positive_semidefinite_residual,
    pure_state_fidelity,
    reference_state,
    validate_normalization,
)
from P1.code.qflpn_transition_operator import (
    controlled_x,
    qflpn_transition_operator,
    ry,
    validate_unitarity,
)


@pytest.mark.parametrize(
    "mu",
    [0.0, 0.25, 0.5, 0.75, 1.0],
)
def test_encoding_probability_matches_membership(mu):
    theta = fuzzy_to_angle(mu)
    state = np.array(
        [np.cos(theta / 2.0), np.sin(theta / 2.0)],
        dtype=np.complex128,
    )
    assert abs(abs(state[1]) ** 2 - mu) <= 1e-12


@pytest.mark.parametrize(
    "mu",
    [-1.0, 1.000001, np.nan, np.inf, -np.inf],
)
def test_encoding_rejects_invalid_membership(mu):
    with pytest.raises(ValueError):
        fuzzy_to_angle(mu)


@pytest.mark.parametrize(
    "state",
    [
        np.array([], dtype=complex),
        np.array([[1.0, 0.0]], dtype=complex),
        np.array([np.nan, 0.0], dtype=complex),
        np.array([np.inf, 0.0], dtype=complex),
        np.array([0.0, 0.0], dtype=complex),
    ],
)
def test_density_matrix_rejects_invalid_state(state):
    with pytest.raises(ValueError):
        density_matrix(state)


@pytest.mark.parametrize(
    "state",
    [
        np.array([], dtype=complex),
        np.array([[1.0, 0.0]], dtype=complex),
        np.array([np.nan, 0.0], dtype=complex),
        np.array([np.inf, 0.0], dtype=complex),
        np.array([0.0, 0.0], dtype=complex),
    ],
)
def test_normalization_rejects_invalid_state(state):
    with pytest.raises(ValueError):
        validate_normalization(state, tol=1e-12)


def test_normalization_rejects_state_outside_tolerance():
    state = np.array([1.0, 1e-5], dtype=complex)
    with pytest.raises(ValueError):
        validate_normalization(state, tol=1e-12)


def test_probability_calculation_rejects_zero_state():
    with pytest.raises(ValueError):
        computational_basis_probabilities(
            np.zeros(4, dtype=complex)
        )


@pytest.mark.parametrize(
    "state",
    [
        np.array([], dtype=complex),
        np.array([[1.0, 0.0]], dtype=complex),
        np.array([np.nan, 0.0], dtype=complex),
        np.array([np.inf, 0.0], dtype=complex),
        np.array([0.0, 0.0], dtype=complex),
    ],
)
def test_probability_calculation_rejects_invalid_state(state):
    with pytest.raises(ValueError):
        computational_basis_probabilities(state)


def test_fidelity_is_invariant_under_global_phase():
    state = np.array([1.0, 1.0j], dtype=complex)
    phase = np.exp(1j * 0.417)
    assert pure_state_fidelity(
        state, phase * state
    ) == pytest.approx(1.0, abs=1e-12)


def test_fidelity_rejects_different_dimensions():
    with pytest.raises(ValueError):
        pure_state_fidelity(
            np.array([1.0, 0.0]),
            np.array([1.0, 0.0, 0.0]),
        )


def test_psd_residual_rejects_nonhermitian_matrix():
    matrix = np.array(
        [[1.0, 1.0], [0.0, 1.0]],
        dtype=complex,
    )
    with pytest.raises(ValueError):
        positive_semidefinite_residual(matrix)


def test_psd_residual_detects_negative_eigenvalue():
    matrix = np.diag([-1e-7, 1.0]).astype(complex)
    assert positive_semidefinite_residual(
        matrix, tol=1e-12
    ) == pytest.approx(1e-7, abs=1e-12)


def test_ry_is_unitary_for_representative_angles():
    for theta in (-np.pi, -0.7, 0.0, 0.7, np.pi):
        assert validate_unitarity(
            ry(theta), tol=1e-12
        ) <= 1e-12


def test_controlled_x_is_unitary():
    operator = controlled_x(
        n_qubits=2,
        control=0,
        target=1,
    )
    assert operator.shape == (4, 4)
    assert validate_unitarity(
        operator, tol=1e-12
    ) <= 1e-12


def test_controlled_x_maps_all_two_qubit_basis_states():
    operator = controlled_x(
        n_qubits=2,
        control=0,
        target=1,
    )

    expected = {
        0: 0,
        1: 1,
        2: 3,
        3: 2,
    }

    for basis, expected_output in expected.items():
        vector = np.eye(4, dtype=complex)[:, basis]
        output = operator @ vector
        assert np.argmax(np.abs(output)) == expected_output
        assert np.count_nonzero(np.abs(output) > 1e-12) == 1


def test_global_transition_preserves_normalization():
    operator = qflpn_transition_operator()
    state = reference_state([0.85, 0.90, 0.45, 0.70])
    output = operator @ state

    assert validate_normalization(
        output, tol=1e-12
    ) <= 1e-12

    probabilities = computational_basis_probabilities(output)
    assert np.all(probabilities >= 0.0)
    assert probabilities.sum() == pytest.approx(
        1.0, abs=1e-12
      )
  
