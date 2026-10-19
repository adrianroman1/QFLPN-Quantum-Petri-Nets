import numpy as np

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    c3x_operator,
    initial_state,
    rotation_operator,
    transition_operator,
)


ATOL = 1e-10


def test_canonical_operator_product():
    expected = c3x_operator() @ rotation_operator(DEFAULT_ACTIVATIONS)
    actual = transition_operator(DEFAULT_ACTIVATIONS)
    assert np.allclose(actual, expected, atol=ATOL, rtol=0.0)


def test_reversed_operator_product_is_different():
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    c3x = c3x_operator()

    canonical = c3x @ rotation
    reversed_order = rotation @ c3x

    assert not np.allclose(
        canonical,
        reversed_order,
        atol=ATOL,
        rtol=0.0,
    )


def test_both_operator_orders_remain_unitary():
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    c3x = c3x_operator()
    identity = np.eye(16, dtype=np.complex128)

    for operator in (c3x @ rotation, rotation @ c3x):
        assert np.allclose(
            operator.conj().T @ operator,
            identity,
            atol=ATOL,
            rtol=0.0,
        )


def test_operator_order_changes_output_for_initial_state():
    rotation = rotation_operator(DEFAULT_ACTIVATIONS)
    c3x = c3x_operator()
    initial = initial_state()

    canonical = c3x @ rotation @ initial
    reversed_order = rotation @ c3x @ initial

    assert not np.allclose(
        canonical,
        reversed_order,
        atol=ATOL,
        rtol=0.0,
    )


def test_canonical_output_matches_reference():
    actual = transition_operator() @ initial_state()
    expected = rotation_operator() @ initial_state()
    expected = c3x_operator() @ expected

    assert np.allclose(actual, expected, atol=ATOL, rtol=0.0)
