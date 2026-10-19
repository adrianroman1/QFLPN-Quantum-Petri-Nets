"""Tests for the canonical NumPy QFLPN reference implementation."""

from __future__ import annotations

import numpy as np
import pytest

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    HILBERT_DIM,
    N_QUBITS,
    basis_label,
    fuzzy_to_angle,
    initial_state,
    reference_state,
    validate_activations,
)


def test_canonical_dimensions():
    assert N_QUBITS == 4
    assert HILBERT_DIM == 16


def test_default_activations_are_valid():
    values = validate_activations(DEFAULT_ACTIVATIONS)

    assert len(values) == 4
    assert all(0.0 <= value <= 1.0 for value in values)


@pytest.mark.parametrize(
    "value",
    [
        0.0,
        0.25,
        0.5,
        0.75,
        1.0,
    ],
)
def test_fuzzy_to_angle_is_finite(value):
    angle = fuzzy_to_angle(value)

    assert np.isfinite(angle)
    assert 0.0 <= angle <= np.pi


@pytest.mark.parametrize(
    "invalid_value",
    [
        -0.01,
        1.01,
        float("nan"),
        float("inf"),
        float("-inf"),
        True,
        False,
        "0.5",
        None,
    ],
)
def test_fuzzy_to_angle_rejects_invalid_values(invalid_value):
    with pytest.raises((TypeError, ValueError)):
        fuzzy_to_angle(invalid_value)


@pytest.mark.parametrize(
    "invalid_values",
    [
        (),
        (0.5, 0.5, 0.5),
        (0.5, 0.5, 0.5, 0.5, 0.5),
        (0.5, 0.5, 0.5, 1.1),
        (0.5, 0.5, 0.5, float("nan")),
        (0.5, 0.5, 0.5, True),
    ],
)
def test_validate_activations_rejects_invalid_inputs(invalid_values):
    with pytest.raises((TypeError, ValueError)):
        validate_activations(invalid_values)


def test_initial_state_is_zero_basis_vector():
    state = initial_state()

    expected = np.zeros(HILBERT_DIM, dtype=np.complex128)
    expected[0] = 1.0

    assert state.shape == (HILBERT_DIM,)
    assert np.array_equal(state, expected)


def test_initial_state_is_normalized():
    state = initial_state()

    assert np.isclose(np.linalg.norm(state), 1.0, atol=1e-12)


def test_reference_state_has_expected_shape():
    state = reference_state(DEFAULT_ACTIVATIONS)

    assert state.shape == (HILBERT_DIM,)
    assert state.dtype == np.complex128


def test_reference_state_is_normalized():
    state = reference_state(DEFAULT_ACTIVATIONS)

    assert np.isclose(np.linalg.norm(state), 1.0, atol=1e-10)


def test_reference_state_is_reproducible():
    first = reference_state(DEFAULT_ACTIVATIONS)
    second = reference_state(DEFAULT_ACTIVATIONS)

    assert np.array_equal(first, second)


def test_basis_label_uses_four_bit_representation():
    assert basis_label(0) == "0000"
    assert basis_label(1) == "0001"
    assert basis_label(15) == "1111"


@pytest.mark.parametrize("index", [-1, 16, 100])
def test_basis_label_rejects_out_of_range_indices(index):
    with pytest.raises((ValueError, IndexError)):
        basis_label(index)
