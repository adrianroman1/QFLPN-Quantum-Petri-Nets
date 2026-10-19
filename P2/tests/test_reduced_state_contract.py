import numpy as np

from qflpn_reference import reference_state


ATOL = 1e-10


def reduced_density_q123(state):
    tensor = np.asarray(state, dtype=np.complex128).reshape(8, 2)
    return tensor @ tensor.conj().T


def reduced_density_q4(state):
    tensor = np.asarray(state, dtype=np.complex128).reshape(8, 2)
    return tensor.conj().T @ tensor


def test_reduced_q123_is_eight_by_eight():
    rho = reduced_density_q123(reference_state())
    assert rho.shape == (8, 8)


def test_reduced_q4_is_two_by_two():
    rho = reduced_density_q4(reference_state())
    assert rho.shape == (2, 2)


def test_reduced_q123_is_hermitian():
    rho = reduced_density_q123(reference_state())
    assert np.allclose(rho, rho.conj().T, atol=ATOL, rtol=0.0)


def test_reduced_q4_is_hermitian():
    rho = reduced_density_q4(reference_state())
    assert np.allclose(rho, rho.conj().T, atol=ATOL, rtol=0.0)


def test_reduced_states_have_unit_trace():
    state = reference_state()
    assert np.isclose(np.trace(reduced_density_q123(state)), 1.0, atol=ATOL)
    assert np.isclose(np.trace(reduced_density_q4(state)), 1.0, atol=ATOL)


def test_reduced_states_are_positive_semidefinite():
    state = reference_state()
    assert np.min(np.linalg.eigvalsh(reduced_density_q123(state))) >= -ATOL
    assert np.min(np.linalg.eigvalsh(reduced_density_q4(state))) >= -ATOL


def test_reduced_states_have_matching_nonzero_spectra():
    state = reference_state()
    large = np.linalg.eigvalsh(reduced_density_q123(state))
    small = np.linalg.eigvalsh(reduced_density_q4(state))

    large_nonzero = large[large > ATOL]
    small_nonzero = small[small > ATOL]

    assert np.allclose(
        np.sort(large_nonzero),
        np.sort(small_nonzero),
        atol=ATOL,
        rtol=0.0,
    )
