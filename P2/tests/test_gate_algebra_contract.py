import numpy as np
import pytest

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    c3x_operator,
    rotation_operator,
    transition_operator,
    ry_matrix,
)


ATOL = 1e-12


def test_ry_is_unitary():
    for theta in (0.0, 0.3, 1.2, np.pi):
        matrix = ry_matrix(theta)
        assert np.allclose(
            matrix.conj().T @ matrix,
            np.eye(2),
            atol=ATOL,
            rtol=0.0,
        )


def test_ry_has_determinant_one():
    assert np.isclose(np.linalg.det(ry_matrix(0.7)), 1.0, atol=ATOL)


def test_c3x_is_hermitian():
    gate = c3x_operator()
    assert np.allclose(gate, gate.conj().T, atol=ATOL, rtol=0.0)


def test_c3x_is_involutory():
    gate = c3x_operator()
    assert np.allclose(gate @ gate, np.eye(16), atol=ATOL, rtol=0.0)


def test_c3x_is_unitary():
    gate = c3x_operator()
    assert np.allclose(
        gate.conj().T @ gate,
        np.eye(16),
        atol=ATOL,
        rtol=0.0,
    )


def test_rotation_operator_is_unitary():
    operator = rotation_operator(DEFAULT_ACTIVATIONS)
    assert operator.shape == (16, 16)
    assert np.allclose(
        operator.conj().T @ operator,
        np.eye(16),
        atol=ATOL,
        rtol=0.0,
    )


def test_complete_operator_is_unitary():
    operator = transition_operator(DEFAULT_ACTIVATIONS)
    assert np.allclose(
        operator.conj().T @ operator,
        np.eye(16),
        atol=ATOL,
        rtol=0.0,
    )


def test_transition_order_is_c3x_after_rotation():
    expected = c3x_operator() @ rotation_operator(DEFAULT_ACTIVATIONS)
    actual = transition_operator(DEFAULT_ACTIVATIONS)
    assert np.allclose(actual, expected, atol=ATOL, rtol=0.0)


@pytest.mark.parametrize("theta", [True, False, "0.5", None])
def test_ry_rejects_invalid_theta(theta):
    with pytest.raises(TypeError):
        ry_matrix(theta)
