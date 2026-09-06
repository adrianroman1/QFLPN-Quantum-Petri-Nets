"""
Tests for the QFLPN 4-qubit reference model.
"""

import math

import numpy as np
import pytest

from qflpn_reference import (
    N_QUBITS,
    STATE_DIMENSION,
    computational_basis_probabilities,
    density_matrix,
    fuzzy_to_angle,
    pure_state_fidelity,
    reference_state,
    ry_state,
)


def test_fuzzy_to_angle_endpoints():
    assert np.isclose(fuzzy_to_angle(0.0), 0.0)
    assert np.isclose(fuzzy_to_angle(1.0), math.pi)


@pytest.mark.parametrize("mu", [0.0, 0.1, 0.45, 0.7, 0.9, 1.0])
def test_ry_probability_matches_membership(mu):
    state = ry_state(mu)

    probability_one = abs(state[1]) ** 2

    assert np.isclose(
        probability_one,
        mu,
        atol=1e-12,
        rtol=0.0,
    )


def test_reference_model_has_four_qubits():
    memberships = (0.85, 0.90, 0.45, 0.70)

    state = reference_state(memberships)

    assert N_QUBITS == 4
    assert state.shape == (STATE_DIMENSION,)
    assert state.shape == (16,)


def test_reference_state_is_normalized():
    state = reference_state(
        (0.85, 0.90, 0.45, 0.70)
    )

    assert np.isclose(
        np.linalg.norm(state),
        1.0,
        atol=1e-12,
        rtol=0.0,
    )


def test_probabilities_sum_to_one():
    state = reference_state(
        (0.85, 0.90, 0.45, 0.70)
    )

    probabilities = computational_basis_probabilities(state)

    assert probabilities.shape == (16,)
    assert np.isclose(
        probabilities.sum(),
        1.0,
        atol=1e-12,
        rtol=0.0,
    )


def test_density_matrix_is_hermitian():
    state = reference_state(
        (0.85, 0.90, 0.45, 0.70)
    )

    rho = density_matrix(state)

    assert rho.shape == (16, 16)
    assert np.allclose(
        rho,
        np.conjugate(rho.T),
        atol=1e-12,
        rtol=0.0,
    )


def test_density_matrix_has_unit_trace():
    state = reference_state(
        (0.85, 0.90, 0.45, 0.70)
    )

    rho = density_matrix(state)

    assert np.isclose(
        np.trace(rho),
        1.0,
        atol=1e-12,
        rtol=0.0,
    )


def test_self_fidelity_is_one():
    state = reference_state(
        (0.85, 0.90, 0.45, 0.70)
    )

    fidelity = pure_state_fidelity(state, state)

    assert np.isclose(
        fidelity,
        1.0,
        atol=1e-12,
        rtol=0.0,
    )


def test_invalid_membership_is_rejected():
    with pytest.raises(ValueError):
        fuzzy_to_angle(-0.01)

    with pytest.raises(ValueError):
        fuzzy_to_angle(1.01)


def test_wrong_number_of_qubits_is_rejected():
    with pytest.raises(ValueError):
        reference_state((0.5, 0.5, 0.5))
