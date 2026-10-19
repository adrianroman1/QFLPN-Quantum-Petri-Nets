import math

import numpy as np
import pytest

from P1.code.qflpn_reference import (
    fuzzy_to_angle,
    reference_state,
    ry_state,
    validate_normalization,
    positive_semidefinite_residual,
)
from P1.code.qflpn_transition_operator import (
    ry,
    local_rotation_operator,
    controlled_x,
    qflpn_transition_operator,
    validate_unitarity,
    benchmark_operator,
)
from P1.tests.independent_reference import (
    independent_angle,
    independent_ry,
    independent_global_operator,
)


@pytest.mark.parametrize(
    "bad",
    [True, False, np.bool_(True), "0.5", "1", "nan", None, 1 + 0j],
)
def test_fuzzy_to_angle_rejects_non_real_numeric_types(bad):
    with pytest.raises(ValueError):
        fuzzy_to_angle(bad)


@pytest.mark.parametrize(
    "bad",
    [float("nan"), float("inf"), -float("inf"), np.float64("nan")],
)
def test_fuzzy_to_angle_rejects_nonfinite_values(bad):
    with pytest.raises(ValueError):
        fuzzy_to_angle(bad)


@pytest.mark.parametrize("bad", [-1e-12, 1.0 + 1e-12])
def test_fuzzy_to_angle_rejects_values_outside_unit_interval(bad):
    with pytest.raises(ValueError):
        fuzzy_to_angle(bad)


@pytest.mark.parametrize("valid", [0, 0.0, 0.25, 0.5, 1, 1.0, np.float64(0.75)])
def test_fuzzy_to_angle_accepts_real_values_in_domain(valid):
    theta = fuzzy_to_angle(valid)
    assert math.isfinite(theta)
    assert math.sin(theta / 2.0) ** 2 == pytest.approx(float(valid), abs=1e-14)


@pytest.mark.parametrize("bad", [True, False, "0.2", 1 + 0j, float("nan"), float("inf")])
def test_ry_rejects_invalid_theta_types_and_values(bad):
    with pytest.raises(ValueError):
        ry(bad)


@pytest.mark.parametrize("bad", [True, False, "0.2", 1 + 0j, float("nan")])
def test_ry_state_rejects_invalid_theta_types_and_values(bad):
    with pytest.raises(ValueError):
        ry_state(bad)


@pytest.mark.parametrize("bad", [True, False, 1.0, "1", np.bool_(True)])
def test_local_rotation_rejects_noninteger_target(bad):
    with pytest.raises(ValueError):
        local_rotation_operator(0.2, target=bad)


@pytest.mark.parametrize("bad", [True, False, 4.0, "4", np.bool_(True)])
def test_local_rotation_rejects_noninteger_qubit_count(bad):
    with pytest.raises(ValueError):
        local_rotation_operator(0.2, n_qubits=bad)


@pytest.mark.parametrize("bad", [True, False, 2.0, "2"])
def test_controlled_x_rejects_noninteger_qubit_count(bad):
    with pytest.raises(ValueError):
        controlled_x(n_qubits=bad)


@pytest.mark.parametrize("bad", [True, False, 0.0, "0"])
def test_controlled_x_rejects_noninteger_control(bad):
    with pytest.raises(ValueError):
        controlled_x(control=bad)


@pytest.mark.parametrize("bad", [True, False, 1.0, "1"])
def test_controlled_x_rejects_noninteger_target(bad):
    with pytest.raises(ValueError):
        controlled_x(target=bad)


@pytest.mark.parametrize(
    "bad",
    [
        (True, 0.2, 0.3, 0.4),
        (0.1, "0.2", 0.3, 0.4),
        (0.1, 0.2, float("nan"), 0.4),
        (0.1, 0.2, 0.3, float("inf")),
        (-0.1, 0.2, 0.3, 0.4),
        (0.1, 0.2, 0.3, 1.1),
    ],
)
def test_global_operator_rejects_invalid_memberships(bad):
    with pytest.raises(ValueError):
        qflpn_transition_operator(bad)


@pytest.mark.parametrize("bad", [True, False, "1e-12", 1 + 0j, float("nan"), -1.0])
def test_unitarity_rejects_invalid_tolerance(bad):
    with pytest.raises(ValueError):
        validate_unitarity(np.eye(2), tol=bad)


@pytest.mark.parametrize("bad", [True, False, "1e-10", float("nan"), -1.0])
def test_normalization_rejects_invalid_tolerance(bad):
    with pytest.raises(ValueError):
        validate_normalization(np.array([1.0]), tol=bad)


@pytest.mark.parametrize("bad", [True, False, "1e-10", float("nan"), -1.0])
def test_psd_rejects_invalid_tolerance(bad):
    with pytest.raises(ValueError):
        positive_semidefinite_residual(np.eye(2), tol=bad)


@pytest.mark.parametrize("bad", [True, False, 1.0, "1", 0])
def test_benchmark_rejects_invalid_repetitions(bad):
    with pytest.raises(ValueError):
        benchmark_operator(repetitions=bad)


@pytest.mark.parametrize("bad", [True, False, "0.5", 1 + 0j, float("nan")])
def test_independent_reference_rejects_invalid_membership(bad):
    with pytest.raises(ValueError):
        independent_angle(bad)


@pytest.mark.parametrize("bad", [True, False, "0.5", 1 + 0j, float("inf")])
def test_independent_reference_rejects_invalid_angle(bad):
    with pytest.raises(ValueError):
        independent_ry(bad)


def test_production_and_independent_operator_agree_after_strict_validation():
    memberships = (0.85, 0.90, 0.45, 0.70)
    production = qflpn_transition_operator(memberships)
    independent = independent_global_operator(memberships)
    np.testing.assert_allclose(production, independent, atol=1e-12, rtol=0.0)


def test_reference_state_rejects_invalid_membership_inside_iterable():
    with pytest.raises(ValueError):
        reference_state([0.2, True, 0.4, 0.6])


def test_boundary_memberships_generate_expected_angles():
    assert fuzzy_to_angle(0.0) == pytest.approx(0.0, abs=1e-15)
    assert fuzzy_to_angle(1.0) == pytest.approx(math.pi, abs=1e-15)
