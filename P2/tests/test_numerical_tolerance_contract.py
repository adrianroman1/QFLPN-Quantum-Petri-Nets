import numpy as np

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    density_matrix,
    reference_state,
    rotation_operator,
    transition_operator,
)


ATOL = 1e-10


def test_rotation_unitarity_residual():
    operator = rotation_operator(DEFAULT_ACTIVATIONS)
    residual = np.linalg.norm(
        operator.conj().T @ operator - np.eye(16),
        ord="fro",
    )
    assert residual <= ATOL


def test_transition_unitarity_residual():
    operator = transition_operator(DEFAULT_ACTIVATIONS)
    residual = np.linalg.norm(
        operator.conj().T @ operator - np.eye(16),
        ord="fro",
    )
    assert residual <= ATOL


def test_state_normalization_residual():
    state = reference_state(DEFAULT_ACTIVATIONS)
    residual = abs(np.linalg.norm(state) - 1.0)
    assert residual <= ATOL


def test_probability_conservation_residual():
    probabilities = np.abs(reference_state(DEFAULT_ACTIVATIONS)) ** 2
    residual = abs(float(np.sum(probabilities)) - 1.0)
    assert residual <= ATOL


def test_density_hermiticity_residual():
    rho = density_matrix(reference_state(DEFAULT_ACTIVATIONS))
    residual = np.linalg.norm(rho - rho.conj().T, ord="fro")
    assert residual <= ATOL


def test_density_trace_residual():
    rho = density_matrix(reference_state(DEFAULT_ACTIVATIONS))
    residual = abs(np.trace(rho) - 1.0)
    assert residual <= ATOL


def test_density_positivity_residual():
    rho = density_matrix(reference_state(DEFAULT_ACTIVATIONS))
    minimum_eigenvalue = float(np.min(np.linalg.eigvalsh(rho)))
    assert minimum_eigenvalue >= -ATOL


def test_density_purity_residual():
    rho = density_matrix(reference_state(DEFAULT_ACTIVATIONS))
    residual = abs(float(np.trace(rho @ rho).real) - 1.0)
    assert residual <= ATOL
