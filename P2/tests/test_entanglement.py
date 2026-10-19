"""Tests for reduced density matrices and entanglement diagnostics."""

from __future__ import annotations

import numpy as np

from qflpn_reference import DEFAULT_ACTIVATIONS, reference_state


ATOL = 1e-10


def reduced_density_first_qubit(state: np.ndarray) -> np.ndarray:
    """Trace out qubits 2, 3 and 4 in the big-endian basis."""
    vector = np.asarray(state, dtype=np.complex128)

    if vector.shape != (16,):
        raise ValueError("Expected a four-qubit state vector of shape (16,).")

    if not np.all(np.isfinite(vector)):
        raise ValueError("State contains non-finite values.")

    norm = np.linalg.norm(vector)
    if not np.isclose(norm, 1.0, atol=ATOL, rtol=0.0):
        raise ValueError("State must be normalized.")

    tensor = vector.reshape(2, 2, 2, 2)

    # rho[a,e] = sum_{b,c,d} psi[a,b,c,d] * conj(psi[e,b,c,d])
    return np.einsum("abcd,ebcd->ae", tensor, tensor.conj())


def test_reduced_density_matrix_has_qubit_dimension():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = reduced_density_first_qubit(state)

    assert rho.shape == (2, 2)


def test_reduced_density_matrix_is_hermitian():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = reduced_density_first_qubit(state)

    assert np.allclose(rho, rho.conj().T, atol=ATOL, rtol=0.0)


def test_reduced_density_matrix_has_unit_trace():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = reduced_density_first_qubit(state)

    assert np.isclose(np.trace(rho), 1.0, atol=ATOL, rtol=0.0)


def test_reduced_density_matrix_is_positive_semidefinite():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = reduced_density_first_qubit(state)

    eigenvalues = np.linalg.eigvalsh(rho)

    assert np.min(eigenvalues) >= -ATOL


def test_reduced_density_matrix_is_not_materially_nonhermitian():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = reduced_density_first_qubit(state)

    residual = np.linalg.norm(rho - rho.conj().T, ord="fro")

    assert residual <= ATOL


def test_reduced_density_matrix_purity_is_in_valid_range():
    state = reference_state(DEFAULT_ACTIVATIONS)
    rho = reduced_density_first_qubit(state)

    purity = float(np.trace(rho @ rho).real)

    assert -ATOL <= purity <= 1.0 + ATOL


def test_reduced_density_matrix_is_independent_copy():
    state = reference_state(DEFAULT_ACTIVATIONS)
    original = state.copy()

    reduced_density_first_qubit(state)

    assert np.array_equal(state, original)
