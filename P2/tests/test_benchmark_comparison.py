
"""Tests for the P2 paired benchmark comparison contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

P2_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = P2_ROOT / "benchmarks" / "benchmark_runner.py"

SPEC = importlib.util.spec_from_file_location(
    "p2_benchmark_runner",
    RUNNER_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load P2 benchmark runner.")

RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_statistics_for_known_sample():
    result = RUNNER.statistics_for(
        [100, 200, 300, 400, 500]
    )

    assert result["minimum_ns"] == 100
    assert result["median_ns"] == 300
    assert result["maximum_ns"] == 500
    assert result["samples"] == 5
    assert result["operations_per_second"] == pytest.approx(
        1_000_000_000 / 300
    )


def test_independent_rotation_matches_production_rotation():
    activations = tuple(RUNNER.DEFAULT_ACTIVATIONS)

    production = RUNNER.rotation_operator(activations)
    independent = RUNNER.independent_rotation_operator(
        activations
    )

    assert production.shape == (16, 16)
    assert independent.shape == (16, 16)

    assert np.linalg.norm(
        production - independent
    ) <= 1e-12


def test_independent_c3x_matches_production_c3x():
    production = RUNNER.c3x_operator()
    independent = RUNNER.independent_c3x_operator()

    assert production.shape == (16, 16)

    assert np.linalg.norm(
        production - independent
    ) <= 1e-12


def test_independent_density_matrix_matches_production():
    state = RUNNER.reference_state()

    production = RUNNER.density_matrix(state)
    independent = RUNNER.independent_density_matrix(state)

    assert production.shape == (16, 16)

    assert np.linalg.norm(
        production - independent
    ) <= 1e-12


def test_independent_reduced_states_match_production():
    state = RUNNER.reference_state()

    independent_q4, independent_q123 = (
        RUNNER.independent_reduced_states(state)
    )

    production_q4 = RUNNER.reduced_density_q4(state)
    production_q123 = RUNNER.reduced_density_q123(state)

    assert independent_q4.shape == (2, 2)
    assert independent_q123.shape == (8, 8)

    assert np.linalg.norm(
        production_q4 - independent_q4
    ) <= 1e-12

    assert np.linalg.norm(
        production_q123 - independent_q123
    ) <= 1e-12


def test_world_record_is_not_fabricated():
    assert (
        RUNNER.WORLD_RECORD_STATUS
        == "NO_DIRECTLY_COMPARABLE_RECORD"
    )

    assert (
        "N/A" in RUNNER.WORLD_RECORD_DISPLAY
    )


def test_literature_sources_have_identifiers_and_urls():
    assert RUNNER.LITERATURE_BENCHMARKS

    for source in RUNNER.LITERATURE_BENCHMARKS:
        assert source["id"]
        assert source["title"]
        assert source["year"] >= 2025
        assert source["doi"]
        assert source["url"].startswith("https://")


def test_reference_state_is_normalized():
    result = RUNNER.independent_reference(
        tuple(RUNNER.DEFAULT_ACTIVATIONS)
    )

    state = result["state_evolution"]

    assert state.shape == (16,)

    assert np.linalg.norm(state) == pytest.approx(
        1.0,
        abs=1e-12,
    )


def test_independent_density_matrix_has_unit_trace():
    result = RUNNER.independent_reference(
        tuple(RUNNER.DEFAULT_ACTIVATIONS)
    )

    rho = result["density_matrix"]

    assert rho.shape == (16, 16)

    assert np.trace(rho).real == pytest.approx(
        1.0,
        abs=1e-12,
    )


def test_independent_density_matrix_is_hermitian():
    result = RUNNER.independent_reference(
        tuple(RUNNER.DEFAULT_ACTIVATIONS)
    )

    rho = result["density_matrix"]

    assert np.linalg.norm(
        rho - rho.conj().T
    ) <= 1e-12


def test_pair_timing_records_both_implementations():
    expected = np.array([1.0, 0.0], dtype=np.complex128)

    result = RUNNER.time_paired_operation(
        name="test_operation",
        production_function=lambda: expected.copy(),
        independent_function=lambda: expected.copy(),
        expected=expected,
        warmups=5,
        repetitions=30,
        tolerance=1e-12,
    )

    assert result["passed"] is True
    assert result["independent_passed"] is True

    assert result["production"]["samples"] == 30
    assert result["independent"]["samples"] == 30

    assert len(result["paired_samples"]) == 30

    assert (
        result["paired_comparison"]["production_win_rate_percent"]
        >= 0.0
    )

    assert (
        result["world_record"]["verified_value_ns"]
        is None
    )


def test_pair_timing_rejects_incorrect_production_result():
    expected = np.array([1.0, 0.0], dtype=np.complex128)
    incorrect = np.array([0.0, 1.0], dtype=np.complex128)

    result = RUNNER.time_paired_operation(
        name="incorrect_operation",
        production_function=lambda: incorrect.copy(),
        independent_function=lambda: expected.copy(),
        expected=expected,
        warmups=5,
        repetitions=30,
        tolerance=1e-12,
    )

    assert result["passed"] is False
    assert result["independent_passed"] is True
    assert result["numerical_error"] > 1e-12


def test_pair_timing_rejects_incorrect_independent_result():
    expected = np.array([1.0, 0.0], dtype=np.complex128)
    incorrect = np.array([0.0, 1.0], dtype=np.complex128)

    result = RUNNER.time_paired_operation(
        name="incorrect_reference",
        production_function=lambda: expected.copy(),
        independent_function=lambda: incorrect.copy(),
        expected=expected,
        warmups=5,
        repetitions=30,
        tolerance=1e-12,
    )

    assert result["passed"] is False
    assert result["independent_passed"] is False
    assert result["independent_numerical_error"] > 1e-12
