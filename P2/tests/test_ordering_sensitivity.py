"""Tests for transition-operator ordering sensitivity."""

from __future__ import annotations

import numpy as np

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    c3x_operator,
    rotation_operator,
    transition_operator,
)


ATOL = 1e-10


def test_canonical_order_is_controlled_x_after_rotations():
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    controlled_x = c3x_operator()

    expected = controlled_x @ rotation
    actual = transition_operator(DEFAULT_ACTIVATIONS)

    assert np.allclose(actual, expected, atol=ATOL, rtol=0.0)


def test_reversed_order_is_computed_separately():
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    controlled_x = c3x_operator()

    reversed_order = rotation @ controlled_x

    assert reversed_order.shape == (16, 16)


def test_canonical_and_reversed_order_are_not_identical():
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    controlled_x = c3x_operator()

    canonical = controlled_x @ rotation
    reversed_order = rotation @ controlled_x

    assert not np.allclose(
        canonical,
        reversed_order,
        atol=ATOL,
        rtol=0.0,
    )


def test_commutator_norm_is_positive_for_default_activations():
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    controlled_x = c3x_operator()

    commutator = controlled_x @ rotation - rotation @ controlled_x
    commutator_norm = np.linalg.norm(commutator, ord="fro")

    assert commutator_norm > ATOL


def test_both_orderings_preserve_unitarity():
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    controlled_x = c3x_operator()

    canonical = controlled_x @ rotation
    reversed_order = rotation @ controlled_x
    identity = np.eye(16, dtype=np.complex128)

    assert np.allclose(
        canonical.conj().T @ canonical,
        identity,
        atol=ATOL,
        rtol=0.0,
    )

    assert np.allclose(
        reversed_order.conj().T @ reversed_order,
        identity,
        atol=ATOL,
        rtol=0.0,
    )


def test_ordering_sensitivity_is_not_a_unitarity_failure():
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    controlled_x = c3x_operator()

    canonical = controlled_x @ rotation
    reversed_order = rotation @ controlled_x

    assert np.allclose(
        canonical.conj().T @ canonical,
        np.eye(16),
        atol=ATOL,
        rtol=0.0,
    )

    assert np.allclose(
        reversed_order.conj().T @ reversed_order,
        np.eye(16),
        atol=ATOL,
        rtol=0.0,
    )

    assert not np.allclose(
        canonical,
        reversed_order,
        atol=ATOL,
        rtol=0.0,
    )
