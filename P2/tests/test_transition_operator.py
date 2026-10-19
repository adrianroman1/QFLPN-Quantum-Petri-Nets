"""Tests for the QFLPN transition operator."""

from __future__ import annotations

import numpy as np
import pytest

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    HILBERT_DIM,
    c3x_operator,
    rotation_operator,
    transition_operator,
)
from qflpn_transition_operator import (
    apply_transition,
    build_rotation_operator,
    build_transition_operator,
    controlled_x_operator,
    verify_transition_structure,
)


IDENTITY = np.eye(HILBERT_DIM, dtype=np.complex128)


def is_unitary(operator: np.ndarray) -> bool:
    return bool(
        np.allclose(
            operator.conj().T @ operator,
            IDENTITY,
            atol=1e-10,
            rtol=0.0,
        )
    )


def test_c3x_operator_has_expected_shape():
    operator = c3x_operator()

    assert operator.shape == (16, 16)


def test_c3x_operator_is_unitary():
    assert is_unitary(c3x_operator())


def test_c3x_operator_swaps_only_controlled_basis_states():
    operator = c3x_operator()

    expected = np.eye(16, dtype=np.complex128)
    expected[14, 14] = 0.0
    expected[15, 15] = 0.0
    expected[14, 15] = 1.0
    expected[15, 14] = 1.0

    assert np.array_equal(operator, expected)


def test_controlled_x_wrapper_matches_reference():
    assert np.array_equal(
        controlled_x_operator(),
        c3x_operator(),
    )


def test_transition_structure_verification_passes():
    assert verify_transition_structure() is True


def test_rotation_operator_has_expected_shape():
    operator = rotation_operator(DEFAULT_ACTIVATIONS)

    assert operator.shape == (16, 16)


def test_rotation_operator_is_unitary():
    assert is_unitary(rotation_operator(DEFAULT_ACTIVATIONS))


def test_rotation_wrapper_matches_reference():
    assert np.allclose(
        build_rotation_operator(DEFAULT_ACTIVATIONS),
        rotation_operator(DEFAULT_ACTIVATIONS),
        atol=1e-12,
        rtol=0.0,
    )


def test_transition_operator_has_expected_shape():
    operator = transition_operator(DEFAULT_ACTIVATIONS)

    assert operator.shape == (16, 16)


def test_transition_operator_is_unitary():
    operator = transition_operator(DEFAULT_ACTIVATIONS)

    assert is_unitary(operator)


def test_transition_wrapper_matches_reference():
    expected = transition_operator(DEFAULT_ACTIVATIONS)
    actual = build_transition_operator(DEFAULT_ACTIVATIONS)

    assert np.allclose(
        actual,
        expected,
        atol=1e-12,
        rtol=0.0,
    )


def test_transition_operator_uses_c3x_after_rotations():
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    controlled_x = c3x_operator()

    expected = controlled_x @ rotation
    actual = build_transition_operator(DEFAULT_ACTIVATIONS)

    assert np.allclose(
        actual,
        expected,
        atol=1e-12,
        rtol=0.0,
    )


def test_apply_transition_preserves_normalization():
    state = np.zeros(HILBERT_DIM, dtype=np.complex128)
    state[0] = 1.0

    result = apply_transition(state, DEFAULT_ACTIVATIONS)

    assert result.shape == (HILBERT_DIM,)
    assert np.isclose(np.linalg.norm(result), 1.0, atol=1e-10)


def test_apply_transition_rejects_wrong_shape():
    invalid_state = np.zeros(8, dtype=np.complex128)

    with pytest.raises(ValueError):
        apply_transition(invalid_state, DEFAULT_ACTIVATIONS)


@pytest.mark.parametrize(
    "invalid_state",
    [
        np.zeros(16, dtype=np.complex128),
        np.full(16, np.nan, dtype=np.complex128),
        np.full(16, np.inf, dtype=np.complex128),
    ],
)
def test_apply_transition_rejects_invalid_state(invalid_state):
    with pytest.raises((ValueError, ArithmeticError)):
        apply_transition(invalid_state, DEFAULT_ACTIVATIONS)


def test_apply_transition_rejects_unnormalized_state():
    state = np.zeros(HILBERT_DIM, dtype=np.complex128)
    state[0] = 2.0

    with pytest.raises(ValueError):
        apply_transition(state, DEFAULT_ACTIVATIONS)


def test_apply_transition_rejects_invalid_activations():
    state = np.zeros(HILBERT_DIM, dtype=np.complex128)
    state[0] = 1.0

    with pytest.raises((TypeError, ValueError)):
        apply_transition(state, (0.5, 0.5, 0.5, 1.5))
