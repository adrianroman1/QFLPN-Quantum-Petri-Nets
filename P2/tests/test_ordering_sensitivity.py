"""Quantitative ordering sensitivity for the canonical QFLPN transition."""

from __future__ import annotations

import numpy as np

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    c3x_operator,
    rotation_operator,
    transition_operator,
)

ATOL = 1e-10
EXPECTED_FIDELITY = 0.9433466414478964
EXPECTED_TVD = 0.1377


def squared_state_fidelity(a: np.ndarray, b: np.ndarray) -> float:
    return float(abs(np.vdot(a, b)) ** 2)


def total_variation_distance(a: np.ndarray, b: np.ndarray) -> float:
    p = np.abs(a) ** 2
    q = np.abs(b) ** 2
    return float(0.5 * np.sum(np.abs(p - q)))


def canonical_and_reversed_states() -> tuple[np.ndarray, np.ndarray]:
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    controlled_x = c3x_operator()
    initial = np.zeros(16, dtype=np.complex128)
    initial[0] = 1.0

    canonical = controlled_x @ rotation @ initial
    reversed_order = rotation @ controlled_x @ initial
    return canonical, reversed_order


def test_canonical_operator_order_is_c3x_after_rotations():
    expected = c3x_operator() @ rotation_operator(DEFAULT_ACTIVATIONS)
    actual = transition_operator(DEFAULT_ACTIVATIONS)
    assert np.allclose(actual, expected, atol=ATOL, rtol=0.0)


def test_reversed_order_is_a_distinct_unitary():
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    controlled_x = c3x_operator()
    canonical = controlled_x @ rotation
    reversed_order = rotation @ controlled_x

    identity = np.eye(16, dtype=np.complex128)
    assert np.allclose(canonical.conj().T @ canonical, identity, atol=ATOL)
    assert np.allclose(reversed_order.conj().T @ reversed_order, identity, atol=ATOL)
    assert not np.allclose(canonical, reversed_order, atol=ATOL, rtol=0.0)


def test_ordering_fidelity_matches_squared_overlap_definition():
    canonical, reversed_order = canonical_and_reversed_states()
    fidelity = squared_state_fidelity(canonical, reversed_order)

    assert np.isclose(fidelity, EXPECTED_FIDELITY, atol=ATOL, rtol=0.0)
    assert fidelity < 1.0


def test_ordering_tvd_matches_probability_distribution_definition():
    canonical, reversed_order = canonical_and_reversed_states()
    tvd = total_variation_distance(canonical, reversed_order)

    assert np.isclose(tvd, EXPECTED_TVD, atol=ATOL, rtol=0.0)
    assert tvd > 0.0


def test_ordering_difference_is_not_a_unitarity_failure():
    canonical, reversed_order = canonical_and_reversed_states()

    for state in (canonical, reversed_order):
        assert np.isclose(np.linalg.norm(state), 1.0, atol=ATOL, rtol=0.0)

    assert not np.allclose(canonical, reversed_order, atol=ATOL, rtol=0.0)
