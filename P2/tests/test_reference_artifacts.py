"""Tests for generated P2 reference artifacts and strict config validation."""

from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


P2_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = P2_ROOT.parent

CONFIG = P2_ROOT / "reports" / "reference_config.json"
GENERATOR = P2_ROOT / "tools" / "generate_reference_artifacts.py"

EXPECTED_ARTIFACTS = {
    "state_vector.csv",
    "probabilities.csv",
    "density_matrix.csv",
    "reduced_density_q4.csv",
    "reduced_density_q123.csv",
    "metadata.json",
}


def load_generator_module():
    """Import the generator directly so its validator can be tested."""

    spec = importlib.util.spec_from_file_location(
        "p2_reference_artifact_generator",
        GENERATOR,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the P2 artifact generator.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


GENERATOR_MODULE = load_generator_module()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as stream:
        return list(csv.DictReader(stream))


def generate_artifacts(output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--config",
            str(CONFIG),
            "--output",
            str(output_dir),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def write_config(path: Path, activation_vector: list[object]) -> None:
    """Write a temporary configuration based on the canonical config."""

    config = json.loads(
        CONFIG.read_text(encoding="utf-8")
    )

    config["activation_vector"] = activation_vector

    path.write_text(
        json.dumps(
            config,
            indent=2,
            allow_nan=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_reference_configuration_exists_and_is_valid():
    assert CONFIG.is_file()

    config = GENERATOR_MODULE.load_config(CONFIG)

    assert config["qubits"] == 4
    assert config["hilbert_dimension"] == 16
    assert config["basis_order"] == "big-endian"
    assert config["activation_vector"] == [0.85, 0.90, 0.45, 0.70]
    assert config["controlled_gate_basis_indices"] == [14, 15]
    assert config["operator_order"] == "U = C3X @ U_rot"
    assert config["entropy_unit"] == "bits"


@pytest.mark.parametrize(
    "invalid_value",
    [
        True,
        False,
    ],
)
def test_configuration_rejects_boolean_activations(
    tmp_path: Path,
    invalid_value: bool,
):
    config_path = tmp_path / "boolean_activation.json"

    write_config(
        config_path,
        [0.85, invalid_value, 0.45, 0.70],
    )

    with pytest.raises(TypeError, match="JSON number"):
        GENERATOR_MODULE.load_config(config_path)


@pytest.mark.parametrize(
    "invalid_value",
    [
        "0.90",
        None,
        [],
        {},
    ],
)
def test_configuration_rejects_non_numeric_activations(
    tmp_path: Path,
    invalid_value: object,
):
    config_path = tmp_path / "non_numeric_activation.json"

    write_config(
        config_path,
        [0.85, invalid_value, 0.45, 0.70],
    )

    with pytest.raises(TypeError, match="JSON number"):
        GENERATOR_MODULE.load_config(config_path)


@pytest.mark.parametrize(
    "invalid_value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_configuration_rejects_non_finite_activations(
    tmp_path: Path,
    invalid_value: float,
):
    config_path = tmp_path / "non_finite_activation.json"

    write_config(
        config_path,
        [0.85, invalid_value, 0.45, 0.70],
    )

    with pytest.raises(ValueError, match="finite"):
        GENERATOR_MODULE.load_config(config_path)


@pytest.mark.parametrize(
    "invalid_value",
    [
        -1e-12,
        1.0 + 1e-12,
    ],
)
def test_configuration_rejects_out_of_domain_activations(
    tmp_path: Path,
    invalid_value: float,
):
    config_path = tmp_path / "out_of_domain_activation.json"

    write_config(
        config_path,
        [0.85, invalid_value, 0.45, 0.70],
    )

    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        GENERATOR_MODULE.load_config(config_path)


@pytest.mark.parametrize(
    "invalid_vector",
    [
        [0.85, 0.90, 0.45],
        [0.85, 0.90, 0.45, 0.70, 0.50],
        "0.85,0.90,0.45,0.70",
        None,
    ],
)
def test_configuration_requires_exactly_four_activation_values(
    tmp_path: Path,
    invalid_vector: object,
):
    config_path = tmp_path / "invalid_activation_vector.json"

    write_config(
        config_path,
        invalid_vector,
    )

    with pytest.raises(ValueError, match="Exactly four"):
        GENERATOR_MODULE.load_config(config_path)


def test_artifact_generator_completes_successfully(tmp_path: Path):
    output_dir = tmp_path / "generated"

    result = generate_artifacts(output_dir)

    assert result.returncode == 0, (
        "Artifact generation failed.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    assert "VERDICT: REFERENCE_ARTIFACTS_GENERATED" in result.stdout


def test_all_expected_artifacts_are_created(tmp_path: Path):
    output_dir = tmp_path / "generated"

    result = generate_artifacts(output_dir)

    assert result.returncode == 0, (
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    actual_files = {
        path.name
        for path in output_dir.iterdir()
        if path.is_file()
    }

    assert EXPECTED_ARTIFACTS.issubset(actual_files)


def test_state_vector_artifact_has_sixteen_entries(tmp_path: Path):
    output_dir = tmp_path / "generated"

    result = generate_artifacts(output_dir)

    assert result.returncode == 0

    rows = read_csv(output_dir / "state_vector.csv")

    assert len(rows) == 16
    assert rows[0]["basis"] == "0000"
    assert rows[-1]["basis"] == "1111"


def test_probability_artifact_is_normalized(tmp_path: Path):
    output_dir = tmp_path / "generated"

    result = generate_artifacts(output_dir)

    assert result.returncode == 0

    rows = read_csv(output_dir / "probabilities.csv")

    probabilities = np.array(
        [float(row["probability"]) for row in rows],
        dtype=np.float64,
    )

    assert probabilities.shape == (16,)
    assert np.all(np.isfinite(probabilities))
    assert np.all(probabilities >= 0.0)
    assert np.isclose(
        probabilities.sum(),
        1.0,
        atol=1e-12,
        rtol=0.0,
    )


def test_density_matrix_artifact_has_256_entries(tmp_path: Path):
    output_dir = tmp_path / "generated"

    result = generate_artifacts(output_dir)

    assert result.returncode == 0

    rows = read_csv(output_dir / "density_matrix.csv")

    assert len(rows) == 256


def test_reduced_density_artifact_dimensions(tmp_path: Path):
    output_dir = tmp_path / "generated"

    result = generate_artifacts(output_dir)

    assert result.returncode == 0

    q4_rows = read_csv(output_dir / "reduced_density_q4.csv")
    q123_rows = read_csv(output_dir / "reduced_density_q123.csv")

    assert len(q4_rows) == 4
    assert len(q123_rows) == 64


def test_metadata_reports_physical_reference_values(tmp_path: Path):
    output_dir = tmp_path / "generated"

    result = generate_artifacts(output_dir)

    assert result.returncode == 0

    metadata = json.loads(
        (output_dir / "metadata.json").read_text(encoding="utf-8")
    )

    assert metadata["state_dimension"] == 16

    assert np.isclose(
        metadata["state_norm"],
        1.0,
        atol=1e-12,
        rtol=0.0,
    )

    assert np.isclose(
        metadata["probability_sum"],
        1.0,
        atol=1e-12,
        rtol=0.0,
    )

    assert np.isclose(
        metadata["density_trace"]["real"],
        1.0,
        atol=1e-12,
        rtol=0.0,
    )

    assert abs(metadata["density_trace"]["imag"]) <= 1e-12

    assert metadata["density_hermiticity_residual"] <= 1e-12

    assert metadata["density_minimum_eigenvalue"] >= -1e-12

    assert metadata["q4_von_neumann_entropy_bits"] >= 0.0
    assert metadata["q4_purity"] <= 1.0 + 1e-12

    assert np.isclose(
        sum(metadata["q4_eigenvalues"]),
        1.0,
        atol=1e-12,
        rtol=0.0,
    )
