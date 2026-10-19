import numpy as np
import pytest

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    HILBERT_DIM,
    initial_state,
    reference_state,
    transition_operator,
)


ATOL = 1e-12


def test_initial_state_is_zero_basis_state():
    expected = np.zeros(HILBERT_DIM, dtype=np.complex128)
    expected[0] = 1.0
    assert np.array_equal(initial_state(), expected)


def test_reference_state_has_sixteen_amplitudes():
    assert reference_state().shape == (16,)


def test_reference_state_is_finite():
    assert np.all(np.isfinite(reference_state()))


def test_reference_state_is_normalized():
    assert np.isclose(
        np.linalg.norm(reference_state()),
        1.0,
        atol=ATOL,
        rtol=0.0,
    )


def test_probabilities_are_nonnegative():
    probabilities = np.abs(reference_state()) ** 2
    assert np.all(probabilities >= 0.0)


def test_probabilities_sum_to_one():
    probabilities = np.abs(reference_state()) ** 2
    assert np.isclose(probabilities.sum(), 1.0, atol=ATOL, rtol=0.0)


def test_operator_application_reproduces_reference_state():
    actual = transition_operator(DEFAULT_ACTIVATIONS) @ initial_state()
    expected = reference_state(DEFAULT_ACTIVATIONS)
    assert np.allclose(actual, expected, atol=ATOL, rtol=0.0)


def test_reference_state_is_deterministic():
    first = reference_state()
    second = reference_state()
    assert np.array_equal(first, second)


def test_operator_preserves_norm_for_basis_input():
    operator = transition_operator()
    state = np.zeros(16, dtype=np.complex128)
    state[7] = 1.0
    result = operator @ state
    assert np.isclose(np.linalg.norm(result), 1.0, atol=ATOL, rtol=0.0)
