"""Contract tests for the canonical QFLPN reference model."""

from __future__ import annotations

import numpy as np
import pytest

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    HILBERT_DIM,
    N_QUBITS,
    basis_label,
    c3x_operator,
    fuzzy_to_angle,
    initial_state,
    reference_state,
    rotation_operator,
    transition_operator,
    validate_activations,
)

ATOL = 1e-12


def test_qubit_count_and_hilbert_dimension():
    assert N_QUBITS == 4
    assert HILBERT_DIM == 16
    assert HILBERT_DIM == 2**N_QUBITS


def test_default_activations_are_canonical():
    assert DEFAULT_ACTIVATIONS == (0.85, 0.90, 0.45, 0.70)
    assert validate_activations(DEFAULT_ACTIVATIONS) == DEFAULT_ACTIVATIONS


def test_activation_angles_follow_declared_mapping():
    for activation in DEFAULT_ACTIVATIONS:
        theta = fuzzy_to_angle(activation)
        assert np.isclose(
            np.sin(theta / 2.0) ** 2,
            activation,
            atol=ATOL,
            rtol=0.0,
        )


def test_initial_state_is_big_endian_zero_basis():
    state = initial_state()

    expected = np.zeros(16, dtype=np.complex128)
    expected[0] = 1.0

    assert np.array_equal(state, expected)
    assert basis_label(0) == "0000"
    assert basis_label(14) == "1110"
    assert basis_label(15) == "1111"


def test_rotation_operator_has_canonical_shape_and_unitarity():
    operator = rotation_operator(DEFAULT_ACTIVATIONS)

    assert operator.shape == (16, 16)
    assert np.allclose(
        operator.conj().T @ operator,
        np.eye(16),
        atol=ATOL,
        rtol=0.0,
    )


def test_c3x_operator_has_canonical_action():
    operator = c3x_operator()

    assert operator.shape == (16, 16)

    expected = np.eye(16, dtype=np.complex128)
    expected[14, 14] = 0.0
    expected[15, 15] = 0.0
    expected[14, 15] = 1.0
    expected[15, 14] = 1.0

    assert np.array_equal(operator, expected)


def test_transition_operator_preserves_declared_order():
    expected = (
        c3x_operator()
        @ rotation_operator(DEFAULT_ACTIVATIONS)
    )

    actual = transition_operator(DEFAULT_ACTIVATIONS)

    assert np.allclose(
        actual,
        expected,
        atol=ATOL,
        rtol=0.0,
    )


def test_reference_state_is_normalized():
    state = reference_state(DEFAULT_ACTIVATIONS)

    assert state.shape == (16,)
    assert np.all(np.isfinite(state))
    assert np.isclose(
        np.linalg.norm(state),
        1.0,
        atol=ATOL,
        rtol=0.0,
    )


@pytest.mark.parametrize(
    "bad",
    [True, False, np.nan, np.inf, -0.1, 1.1],
)
def test_invalid_activation_values_are_rejected(bad):
    with pytest.raises((TypeError, ValueError)):
        validate_activations((bad, 0.2, 0.3, 0.4))


def test_wrong_activation_count_is_rejected():
    with pytest.raises(ValueError):
        validate_activations((0.1, 0.2, 0.3))
