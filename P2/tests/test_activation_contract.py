import numpy as np
import pytest

from qflpn_reference import (
    DEFAULT_ACTIVATIONS,
    fuzzy_to_angle,
    validate_activations,
)


def test_default_activation_vector_is_exact():
    assert validate_activations() == DEFAULT_ACTIVATIONS


@pytest.mark.parametrize("value", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_activation_encoding_reconstructs_probability(value):
    theta = fuzzy_to_angle(value)
    reconstructed = np.sin(theta / 2.0) ** 2
    assert np.isclose(reconstructed, value, atol=1e-12, rtol=0.0)


@pytest.mark.parametrize("value", [True, False, np.bool_(True)])
def test_boolean_activation_is_rejected(value):
    with pytest.raises(TypeError):
        fuzzy_to_angle(value)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_activation_is_rejected(value):
    with pytest.raises(ValueError):
        fuzzy_to_angle(value)


@pytest.mark.parametrize("value", [-1e-12, 1.0 + 1e-12])
def test_out_of_domain_activation_is_rejected(value):
    with pytest.raises(ValueError):
        fuzzy_to_angle(value)


@pytest.mark.parametrize("value", ["0.5", None, 0.5 + 0j])
def test_non_real_activation_is_rejected(value):
    with pytest.raises(TypeError):
        fuzzy_to_angle(value)


def test_activation_vector_requires_four_values():
    with pytest.raises(ValueError):
        validate_activations((0.1, 0.2, 0.3))


def test_activation_vector_rejects_invalid_member():
    with pytest.raises((TypeError, ValueError)):
        validate_activations((0.1, 0.2, 0.3, True))
