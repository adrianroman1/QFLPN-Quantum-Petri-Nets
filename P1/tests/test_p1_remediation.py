import math
import numpy as np
import pytest

from P1.code.qflpn_reference import (
    fuzzy_to_angle, ry_state, reference_state, density_matrix,
    validate_normalization, positive_semidefinite_residual,
    pure_state_fidelity, computational_basis_probabilities,
)
from P1.code.qflpn_transition_operator import (
    ry, c3x, qflpn_transition_operator, validate_unitarity,
)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_psd_rejects_nonfinite(bad):
    matrix = np.eye(2, dtype=np.complex128)
    matrix[0, 0] = bad
    with pytest.raises(ValueError):
        positive_semidefinite_residual(matrix)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_unitarity_rejects_nonfinite(bad):
    matrix = np.eye(2, dtype=np.complex128)
    matrix[0, 0] = bad
    with pytest.raises(ValueError):
        validate_unitarity(matrix)


@pytest.mark.parametrize("mu", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_membership_encoding(mu):
    theta = fuzzy_to_angle(mu)
    assert math.isclose(math.sin(theta / 2.0) ** 2, mu, abs_tol=1e-14)


@pytest.mark.parametrize("mu", [-1e-9, 1.000000001, float("nan"), float("inf"), -float("inf")])
def test_membership_rejects_invalid_values(mu):
    with pytest.raises(ValueError):
        fuzzy_to_angle(mu)


@pytest.mark.parametrize("theta", [-2.3, -0.1, 0.0, 0.7, math.pi])
def test_ry_matches_analytic_formula(theta):
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    expected = np.array([[c, -s], [s, c]], dtype=np.complex128)
    np.testing.assert_allclose(ry(theta), expected, atol=1e-14, rtol=0)


def test_fidelity_identical_orthogonal_and_global_phase():
    zero = np.array([1, 0], dtype=complex)
    one = np.array([0, 1], dtype=complex)
    phased = np.exp(1j * 0.731) * zero
    assert pure_state_fidelity(zero, zero) == pytest.approx(1.0)
    assert pure_state_fidelity(zero, one) == pytest.approx(0.0, abs=1e-15)
    assert pure_state_fidelity(zero, phased) == pytest.approx(1.0, abs=1e-14)


def test_density_matrix_trace_hermiticity_and_psd():
    state = reference_state([0.2, 0.4, 0.6, 0.8])
    rho = density_matrix(state)
    assert np.trace(rho) == pytest.approx(1.0 + 0j, abs=1e-14)
    np.testing.assert_allclose(rho, rho.conj().T, atol=1e-14)
    assert positive_semidefinite_residual(rho) <= 1e-12
    assert validate_normalization(state) <= 1e-12


def test_unitary_evolution_preserves_density_properties():
    state = reference_state([0.1, 0.3, 0.5, 0.7])
    rho = density_matrix(state)
    operator = qflpn_transition_operator([0.1, 0.3, 0.5, 0.7])
    evolved = operator @ rho @ operator.conj().T
    assert np.trace(evolved) == pytest.approx(1.0 + 0j, abs=1e-12)
    np.testing.assert_allclose(evolved, evolved.conj().T, atol=1e-12)
    assert positive_semidefinite_residual(evolved, tol=1e-10) <= 1e-10


def test_c3x_truth_table_all_sixteen_basis_states():
    operator = c3x()
    assert operator.shape == (16, 16)
    for basis in range(16):
        vector = np.eye(16, dtype=complex)[:, basis]
        output = operator @ vector
        expected = basis ^ 1 if (basis & 0b1110) == 0b1110 else basis
        assert int(np.argmax(np.abs(output))) == expected
        assert np.count_nonzero(np.abs(output) > 1e-12) == 1


def test_global_operator_dimension_unitarity_and_application():
    operator = qflpn_transition_operator()
    assert operator.shape == (16, 16)
    assert validate_unitarity(operator, tol=1e-12) <= 1e-12
    state = np.zeros(16, dtype=complex)
    state[0] = 1
    output = operator @ state
    assert output.shape == (16,)
    assert np.linalg.norm(output) == pytest.approx(1.0, abs=1e-12)


def test_sequential_composition_is_unitary():
    u1 = np.kron(ry(0.2), np.eye(2))
    u2 = np.kron(np.eye(2), ry(-0.4))
    u3 = np.kron(np.array([[0, 1], [1, 0]], dtype=complex), np.eye(2))
    composed = u3 @ u2 @ u1
    assert validate_unitarity(composed, tol=1e-12) <= 1e-12


def test_probability_distribution_is_normalized():
    probabilities = computational_basis_probabilities(reference_state([0.1, 0.2, 0.3, 0.4]))
    assert np.all(probabilities >= 0)
    assert probabilities.sum() == pytest.approx(1.0, abs=1e-14)
