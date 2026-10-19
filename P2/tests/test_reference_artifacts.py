"""Tests for generated P2 reference artifacts."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


P2_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = P2_ROOT.parent

CONFIG = P2_ROOT / "reports" / "reference_config.json"
GENERATOR = P2_ROOT / "tools" / "generate_reference_artifacts.py"
OUTPUT = P2_ROOT / "reports" / "reference_artifacts"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as stream:
        return list(csv.DictReader(stream))


def generate_artifacts() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--config",
            str(CONFIG),
            "--output",
            str(OUTPUT),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_reference_configuration_exists_and_is_valid():
    assert CONFIG.is_file()

    config = json.loads(
        CONFIG.read_text(encoding="utf-8")
    )

    assert config["qubits"] == 4
    assert config["hilbert_dimension"] == 16
    assert config["basis_order"] == "big-endian"
    assert config["activation_vector"] == [0.85, 0.90, 0.45, 0.70]
    assert config["controlled_gate_basis_indices"] == [14, 15]


def test_artifact_generator_completes_successfully():
    result = generate_artifacts()

    assert result.returncode == 0, (
        "Artifact generation failed.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


def test_all_expected_artifacts_are_created():
    result = generate_artifacts()

    assert result.returncode == 0

    expected_files = {
        "state_vector.csv",
        "probabilities.csv",
        "density_matrix.csv",
        "reduced_density_q4.csv",
        "reduced_density_q123.csv",
        "metadata.json",
    }

    actual_files = {
        path.name
        for path in OUTPUT.iterdir()
        if path.is_file()
    }

    assert expected_files.issubset(actual_files)


def test_state_vector_artifact_has_sixteen_entries():
    result = generate_artifacts()

    assert result.returncode == 0

    rows = read_csv(OUTPUT / "state_vector.csv")

    assert len(rows) == 16
    assert rows[0]["basis"] == "0000"
    assert rows[-1]["basis"] == "1111"


def test_probability_artifact_is_normalized():
    result = generate_artifacts()

    assert result.returncode == 0

    rows = read_csv(OUTPUT / "probabilities.csv")

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


def test_density_matrix_artifact_has_256_entries():
    result = generate_artifacts()

    assert result.returncode == 0

    rows = read_csv(OUTPUT / "density_matrix.csv")

    assert len(rows) == 256


def test_reduced_density_artifact_dimensions():
    result = generate_artifacts()

    assert result.returncode == 0

    q4_rows = read_csv(OUTPUT / "reduced_density_q4.csv")
    q123_rows = read_csv(OUTPUT / "reduced_density_q123.csv")

    assert len(q4_rows) == 4
    assert len(q123_rows) == 64


def test_metadata_reports_physical_reference_values():
    result = generate_artifacts()

    assert result.returncode == 0

    metadata = json.loads(
        (OUTPUT / "metadata.json").read_text(encoding="utf-8")
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
    assert metadata["q4_von_neumann_entropy_bits"] >= 0.0
    assert metadata["q4_purity"] <= 1.0 + 1e-12
