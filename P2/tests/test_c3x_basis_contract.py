import numpy as np

from qflpn_reference import c3x_operator


ATOL = 1e-12


def test_c3x_maps_basis_1110_to_1111():
    gate = c3x_operator()
    initial = np.zeros(16, dtype=np.complex128)
    initial[14] = 1.0

    result = gate @ initial
    expected = np.zeros(16, dtype=np.complex128)
    expected[15] = 1.0

    assert np.allclose(result, expected, atol=ATOL, rtol=0.0)


def test_c3x_maps_basis_1111_to_1110():
    gate = c3x_operator()
    initial = np.zeros(16, dtype=np.complex128)
    initial[15] = 1.0

    result = gate @ initial
    expected = np.zeros(16, dtype=np.complex128)
    expected[14] = 1.0

    assert np.allclose(result, expected, atol=ATOL, rtol=0.0)


def test_c3x_leaves_all_other_basis_states_unchanged():
    gate = c3x_operator()

    for index in range(14):
        initial = np.zeros(16, dtype=np.complex128)
        initial[index] = 1.0
        assert np.array_equal(gate @ initial, initial)


def test_c3x_has_exactly_one_nonzero_per_row_and_column():
    gate = c3x_operator()

    assert np.all(np.count_nonzero(gate, axis=0) == 1)
    assert np.all(np.count_nonzero(gate, axis=1) == 1)


def test_c3x_entries_are_binary():
    gate = c3x_operator()
    assert set(np.unique(gate)).issubset({0.0, 1.0})
