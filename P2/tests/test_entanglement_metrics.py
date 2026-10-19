"""Entanglement metrics for the partition (q1,q2,q3) | q4."""

from __future__ import annotations

import numpy as np

from qflpn_reference import DEFAULT_ACTIVATIONS, reference_state

ATOL = 1e-10
EXPECTED_PURITY = 0.9277625800
EXPECTED_VN_ENTROPY_NATS = 0.1600035153743018


def reduced_density_q123(state: np.ndarray) -> np.ndarray:
    vector = np.asarray(state, dtype=np.complex128)
    if vector.shape != (16,):
        raise ValueError("Expected a 16-dimensional four-qubit state.")
    if not np.all(np.isfinite(vector)):
        raise ValueError("State contains non-finite values.")
    if not np.isclose(np.linalg.norm(vector), 1.0, atol=ATOL, rtol=0.0):
        raise ValueError("State must be normalized.")

    tensor = vector.reshape(8, 2)
    return tensor @ tensor.conj().T


def spectral_metrics(rho: np.ndarray) -> tuple[np.ndarray, float, float]:
    eigenvalues = np.linalg.eigvalsh(rho)
    eigenvalues = np.clip(eigenvalues, 0.0, None)
    total = float(eigenvalues.sum())
    if not np.isclose(total, 1.0, atol=ATOL, rtol=0.0):
        raise ValueError("Reduced density spectrum must sum to one.")

    purity = float(np.sum(eigenvalues**2))
    positive = eigenvalues[eigenvalues > 0.0]
    entropy = float(-np.sum(positive * np.log(positive)))
    return eigenvalues, purity, entropy


def test_reduced_density_matrix_is_eight_by_eight():
    rho = reduced_density_q123(reference_state(DEFAULT_ACTIVATIONS))
    assert rho.shape == (8, 8)


def test_reduced_density_matrix_is_physical():
    rho = reduced_density_q123(reference_state(DEFAULT_ACTIVATIONS))
    assert np.allclose(rho, rho.conj().T, atol=ATOL, rtol=0.0)
    assert np.isclose(np.trace(rho), 1.0, atol=ATOL, rtol=0.0)
    assert np.min(np.linalg.eigvalsh(rho)) >= -ATOL


def test_reduced_spectrum_is_normalized_and_nonnegative():
    rho = reduced_density_q123(reference_state(DEFAULT_ACTIVATIONS))
    eigenvalues, _, _ = spectral_metrics(rho)
    assert np.min(eigenvalues) >= 0.0
    assert np.isclose(eigenvalues.sum(), 1.0, atol=ATOL, rtol=0.0)


def test_partition_purity_matches_reproducible_reference():
    rho = reduced_density_q123(reference_state(DEFAULT_ACTIVATIONS))
    _, purity, _ = spectral_metrics(rho)
    assert np.isclose(purity, EXPECTED_PURITY, atol=ATOL, rtol=0.0)


def test_partition_von_neumann_entropy_matches_definition():
    rho = reduced_density_q123(reference_state(DEFAULT_ACTIVATIONS))
    _, _, entropy = spectral_metrics(rho)
    assert np.isclose(
        entropy,
        EXPECTED_VN_ENTROPY_NATS,
        atol=ATOL,
        rtol=0.0,
    )


def test_reduced_state_has_at_most_two_nonzero_eigenvalues():
    rho = reduced_density_q123(reference_state(DEFAULT_ACTIVATIONS))
    eigenvalues, _, _ = spectral_metrics(rho)
    assert np.count_nonzero(eigenvalues > ATOL) <= 2
