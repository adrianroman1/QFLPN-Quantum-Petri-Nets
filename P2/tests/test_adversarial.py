"""Adversarial input tests for the QFLPN P2 reference implementation."""

from __future__ import annotations

import numpy as np
import pytest

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    density_matrix,
    fuzzy_to_angle,
    reference_state,
    validate_activations,
)
from qflpn_transition_operator import apply_transition


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        None,
        "0.25",
        complex(0.5, 0.0),
        float("nan"),
        float("inf"),
        float("-inf"),
        -1e-12,
        1.0 + 1e-12,
    ],
)
def test_fuzzy_encoding_rejects_adversarial_values(value):
    with pytest.raises((TypeError, ValueError)):
        fuzzy_to_angle(value)


@pytest.mark.parametrize(
    "values",
    [
        [0.5, 0.5, 0.5],
        [0.5, 0.5, 0.5, 0.5, 0.5],
        [0.5, 0.5, 0.5, True],
        [0.5, 0.5, 0.5, float("nan")],
        [0.5, 0.5, 0.5, float("inf")],
        [0.5, 0.5, 0.5, -0.1],
        [0.5, 0.5, 0.5, 1.1],
        None,
        "0.5,0.5,0.5,0.5",
    ],
)
def test_activation_validation_rejects_adversarial_inputs(values):
    with pytest.raises((TypeError, ValueError)):
        validate_activations(values)


def test_reference_state_rejects_invalid_activation_vector():
    with pytest.raises((TypeError, ValueError)):
        reference_state((0.5, 0.5, 0.5, 2.0))


@pytest.mark.parametrize(
    "state",
    [
        np.zeros(15, dtype=np.complex128),
        np.zeros(17, dtype=np.complex128),
        np.full(16, np.nan, dtype=np.complex128),
        np.full(16, np.inf, dtype=np.complex128),
        np.full(16, -np.inf, dtype=np.complex128),
    ],
)
def test_density_matrix_rejects_malformed_states(state):
    with pytest.raises((TypeError, ValueError)):
        density_matrix(state)


def test_density_matrix_rejects_non_normalized_state():
    state = np.zeros(16, dtype=np.complex128)
    state[0] = 3.0

    with pytest.raises((TypeError, ValueError)):
        density_matrix(state)


def test_transition_rejects_zero_vector():
    state = np.zeros(16, dtype=np.complex128)

    with pytest.raises(ValueError):
        apply_transition(state, DEFAULT_ACTIVATIONS)


def test_transition_rejects_nan_state():
    state = np.zeros(16, dtype=np.complex128)
    state[0] = np.nan

    with pytest.raises(ValueError):
        apply_transition(state, DEFAULT_ACTIVATIONS)


def test_transition_rejects_boolean_activation():
    state = np.zeros(16, dtype=np.complex128)
    state[0] = 1.0

    with pytest.raises((TypeError, ValueError)):
        apply_transition(state, (0.5, 0.5, 0.5, True))


def test_valid_boundary_activations_are_accepted():
    values = validate_activations((0.0, 0.0, 1.0, 1.0))

    assert values == (0.0, 0.0, 1.0, 1.0)


def test_valid_default_state_remains_normalized():
    state = reference_state(DEFAULT_ACTIVATIONS)

    assert np.isclose(np.linalg.norm(state), 1.0, atol=1e-10)
