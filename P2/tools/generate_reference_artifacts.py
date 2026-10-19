"""Generate manuscript-aligned numerical reference artifacts for P2."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


P2_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = P2_ROOT.parent
CODE_DIR = P2_ROOT / "code"

DEFAULT_CONFIG = P2_ROOT / "reports" / "reference_config.json"
DEFAULT_OUTPUT = P2_ROOT / "reports" / "reference_artifacts"

sys.path.insert(0, str(CODE_DIR))

from qflpn_reference import (  # noqa: E402
    DEFAULT_ACTIVATIONS,
    basis_label,
    density_matrix,
    reference_state,
    transition_operator,
)


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)

    if not isinstance(config, dict):
        raise ValueError("Reference configuration must be a JSON object.")

    required = {
        "schema_version",
        "project",
        "qubits",
        "hilbert_dimension",
        "basis_order",
        "activation_vector",
        "controlled_gate",
        "controlled_gate_basis_indices",
        "operator_order",
        "reduced_partition",
        "entropy_unit",
    }

    missing = sorted(required - set(config))

    if missing:
        raise ValueError(
            "Missing configuration fields: " + ", ".join(missing)
        )

    if config["qubits"] != 4:
        raise ValueError("P2 reference requires exactly four qubits.")

    if config["hilbert_dimension"] != 16:
        raise ValueError("P2 Hilbert dimension must be 16.")

    if config["basis_order"] != "big-endian":
        raise ValueError("Unsupported basis-order convention.")

    if config["controlled_gate_basis_indices"] != [14, 15]:
        raise ValueError("P2 C3X must exchange basis indices 14 and 15.")

    if config["operator_order"] != "U = C3X @ U_rot":
        raise ValueError("Unexpected operator-order convention.")

    if config["entropy_unit"] != "bits":
        raise ValueError("P2 manuscript entropy unit must be bits.")

    activations = config["activation_vector"]

    if not isinstance(activations, list) or len(activations) != 4:
        raise ValueError("Exactly four activation values are required.")

    if not np.all(np.isfinite(np.asarray(activations, dtype=float))):
        raise ValueError("Activation vector contains non-finite values.")

    if np.any(np.asarray(activations, dtype=float) < 0.0):
        raise ValueError("Activation values must be nonnegative.")

    if np.any(np.asarray(activations, dtype=float) > 1.0):
        raise ValueError("Activation values must not exceed one.")

    return config


def write_csv(
    path: Path,
    header: list[str],
    rows: list[list[object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def reduced_density_q4(state: np.ndarray) -> np.ndarray:
    tensor = np.asarray(
        state,
        dtype=np.complex128,
    ).reshape(8, 2)

    return tensor.conj().T @ tensor


def reduced_density_q123(state: np.ndarray) -> np.ndarray:
    tensor = np.asarray(
        state,
        dtype=np.complex128,
    ).reshape(8, 2)

    return tensor @ tensor.conj().T


def complex_value(value: complex) -> dict[str, float]:
    return {
        "real": float(value.real),
        "imag": float(value.imag),
    }


def generate(config_path: Path, output_dir: Path) -> dict:
    config = load_config(config_path)

    activations = tuple(
        float(value)
        for value in config["activation_vector"]
    )

    state = reference_state(activations)
    rho = density_matrix(state)
    operator = transition_operator(activations)
    probabilities = np.abs(state) ** 2

    rho_q4 = reduced_density_q4(state)
    rho_q123 = reduced_density_q123(state)

    eigenvalues_q4 = np.linalg.eigvalsh(rho_q4)
    eigenvalues_q4 = np.clip(eigenvalues_q4, 0.0, None)

    positive_eigenvalues = eigenvalues_q4[eigenvalues_q4 > 0.0]

    entropy_bits = float(
        -np.sum(positive_eigenvalues * np.log2(positive_eigenvalues))
    )

    purity_q4 = float(np.trace(rho_q4 @ rho_q4).real)

    output_dir.mkdir(parents=True, exist_ok=True)

    state_rows = [
        [
            index,
            basis_label(index),
            float(state[index].real),
            float(state[index].imag),
        ]
        for index in range(16)
    ]

    write_csv(
        output_dir / "state_vector.csv",
        ["index", "basis", "real", "imag"],
        state_rows,
    )

    probability_rows = [
        [
            index,
            basis_label(index),
            float(probabilities[index]),
        ]
        for index in range(16)
    ]

    write_csv(
        output_dir / "probabilities.csv",
        ["index", "basis", "probability"],
        probability_rows,
    )

    density_rows = [
        [
            row,
            column,
            float(rho[row, column].real),
            float(rho[row, column].imag),
        ]
        for row in range(16)
        for column in range(16)
    ]

    write_csv(
        output_dir / "density_matrix.csv",
        ["row", "column", "real", "imag"],
        density_rows,
    )

    q4_rows = [
        [
            row,
            column,
            float(rho_q4[row, column].real),
            float(rho_q4[row, column].imag),
        ]
        for row in range(2)
        for column in range(2)
    ]

    write_csv(
        output_dir / "reduced_density_q4.csv",
        ["row", "column", "real", "imag"],
        q4_rows,
    )

    q123_rows = [
        [
            row,
            column,
            float(rho_q123[row, column].real),
            float(rho_q123[row, column].imag),
        ]
        for row in range(8)
        for column in range(8)
    ]

    write_csv(
        output_dir / "reduced_density_q123.csv",
        ["row", "column", "real", "imag"],
        q123_rows,
    )

    metadata = {
        "schema_version": 1,
        "project": config["project"],
        "manuscript": config.get("manuscript"),
        "configuration": config,
        "activation_vector": list(activations),
        "basis_order": config["basis_order"],
        "state_dimension": int(state.size),
        "state_norm": float(np.linalg.norm(state)),
        "probability_sum": float(probabilities.sum()),
        "operator_unitarity_residual": float(
            np.linalg.norm(
                operator.conj().T @ operator - np.eye(16),
                ord="fro",
            )
        ),
        "density_trace": complex_value(np.trace(rho)),
        "density_hermiticity_residual": float(
            np.linalg.norm(rho - rho.conj().T, ord="fro")
        ),
        "density_minimum_eigenvalue": float(
            np.min(np.linalg.eigvalsh(rho))
        ),
        "q4_reduced_density_matrix": [
            [complex_value(value) for value in row]
            for row in rho_q4
        ],
        "q4_eigenvalues": [
            float(value) for value in eigenvalues_q4
        ],
        "q4_purity": purity_q4,
        "q4_von_neumann_entropy_bits": entropy_bits,
        "numerical_dtype": "complex128",
    }

    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate P2 manuscript-aligned reference artifacts."
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    try:
        config_path = args.config.resolve(strict=True)
        output_dir = args.output.resolve()

        config_path.relative_to(P2_ROOT.resolve())

        metadata = generate(
            config_path,
            output_dir,
        )

    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("FAIL:", exc)
        return 2

    print("Reference configuration:", config_path)
    print("Artifacts directory:", output_dir)
    print("State norm:", metadata["state_norm"])
    print("Probability sum:", metadata["probability_sum"])
    print("Q4 purity:", metadata["q4_purity"])
    print(
        "Q4 entropy (bits):",
        metadata["q4_von_neumann_entropy_bits"],
    )
    print("VERDICT: REFERENCE_ARTIFACTS_GENERATED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
