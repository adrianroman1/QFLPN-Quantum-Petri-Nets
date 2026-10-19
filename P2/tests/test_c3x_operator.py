"""Structural and algebraic tests for the four-qubit C3X operator."""

from __future__ import annotations

import numpy as np

from qflpn_reference import c3x_operator

ATOL = 1e-12


def test_c3x_has_sixteen_by_sixteen_shape():
    assert c3x_operator().shape == (16, 16)


def test_c3x_swaps_only_basis_indices_fourteen_and_fifteen():
    operator = c3x_operator()
    expected = np.eye(16, dtype=np.complex128)
    expected[14, 14] = expected[15, 15] = 0.0
    expected[14, 15] = expected[15, 14] = 1.0
    assert np.array_equal(operator, expected)


def test_c3x_is_hermitian_and_involutory():
    operator = c3x_operator()
    assert np.allclose(operator, operator.conj().T, atol=ATOL, rtol=0.0)
    assert np.allclose(operator @ operator, np.eye(16), atol=ATOL, rtol=0.0)


def test_c3x_is_unitary():
    operator = c3x_operator()
    assert np.allclose(
        operator.conj().T @ operator,
        np.eye(16),
        atol=ATOL,
        rtol=0.0,
    )


def test_c3x_preserves_all_basis_states_without_all_controls():
    operator = c3x_operator()
    for index in range(14):
        basis = np.zeros(16, dtype=np.complex128)
        basis[index] = 1.0
        assert np.array_equal(operator @ basis, basis)


def test_c3x_maps_index_fourteen_to_fifteen_and_back():
    operator = c3x_operator()
    state_14 = np.eye(16, dtype=np.complex128)[:, 14]
    state_15 = np.eye(16, dtype=np.complex128)[:, 15]
    assert np.array_equal(operator @ state_14, state_15)
    assert np.array_equal(operator @ state_15, state_14)
