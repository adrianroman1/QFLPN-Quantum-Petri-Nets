import numpy as np
import pytest

from qflpn_reference import density_matrix, reference_state


ATOL = 1e-10


def test_density_matrix_is_sixteen_by_sixteen():
    assert density_matrix(reference_state()).shape == (16, 16)


def test_density_matrix_is_hermitian():
    rho = density_matrix(reference_state())
    assert np.allclose(rho, rho.conj().T, atol=ATOL, rtol=0.0)


def test_density_matrix_has_unit_trace():
    rho = density_matrix(reference_state())
    assert np.isclose(np.trace(rho), 1.0, atol=ATOL, rtol=0.0)


def test_density_matrix_is_positive_semidefinite():
    rho = density_matrix(reference_state())
    assert np.min(np.linalg.eigvalsh(rho)) >= -ATOL


def test_pure_state_density_matrix_is_idempotent():
    rho = density_matrix(reference_state())
    assert np.allclose(rho @ rho, rho, atol=ATOL, rtol=0.0)


def test_pure_state_purity_is_one():
    rho = density_matrix(reference_state())
    purity = float(np.trace(rho @ rho).real)
    assert np.isclose(purity, 1.0, atol=ATOL, rtol=0.0)


def test_density_matrix_is_rank_one():
    eigenvalues = np.linalg.eigvalsh(density_matrix(reference_state()))
    assert np.count_nonzero(eigenvalues > ATOL) == 1


@pytest.mark.parametrize(
    "state",
    [
        np.zeros(8, dtype=np.complex128),
        np.zeros(17, dtype=np.complex128),
        np.full(16, np.nan, dtype=np.complex128),
        np.full(16, np.inf, dtype=np.complex128),
    ],
)
def test_invalid_state_is_rejected(state):
    with pytest.raises((ValueError, TypeError)):
        density_matrix(state)


def test_unnormalized_state_is_rejected():
    state = np.zeros(16, dtype=np.complex128)
    state[0] = 2.0
    with pytest.raises(ValueError):
        density_matrix(state)
