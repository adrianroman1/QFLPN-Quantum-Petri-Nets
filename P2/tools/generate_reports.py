"""Generate manuscript-aligned P2 numerical and parity reports."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pennylane as qml

P2_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = P2_ROOT / "code"
REPORTS_DIR = P2_ROOT / "reports"
ARTIFACTS_DIR = P2_ROOT / "artifacts"

if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from qflpn_reference import (  # noqa: E402
    DEFAULT_ACTIVATIONS,
    c3x_operator,
    density_matrix,
    initial_state,
    reference_state,
    rotation_operator,
    transition_operator,
)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )


def pennylane_state(activations: tuple[float, ...]) -> np.ndarray:
    device = qml.device(
        "default.qubit",
        wires=4,
    )

    @qml.qnode(device)
    def circuit(values):
        for wire, value in enumerate(values):
            theta = 2.0 * np.arcsin(np.sqrt(value))
            qml.RY(theta, wires=wire)

        controlled_x = qml.ctrl(
            qml.PauliX,
            control=[0, 1, 2],
        )

        controlled_x(wires=3)

        return qml.state()

    return np.asarray(
        circuit(activations),
        dtype=np.complex128,
    )


def validate_artifacts() -> dict:
    required = {
        "state_vector.csv",
        "probabilities.csv",
        "density_matrix.csv",
        "reduced_density_q4.csv",
        "reduced_density_q123.csv",
        "metadata.json",
    }

    missing = sorted(
        name
        for name in required
        if not (ARTIFACTS_DIR / name).is_file()
    )

    if missing:
        return {
            "schema_version": 1,
            "status": "FAIL",
            "missing_files": missing,
            "all_checks_pass": False,
        }

    metadata = json.loads(
        (ARTIFACTS_DIR / "metadata.json").read_text(
            encoding="utf-8"
        )
    )

    checks = {
        "state_dimension_is_16": (
            metadata.get("state_dimension") == 16
        ),
        "state_norm_is_finite": (
            np.isfinite(metadata.get("state_norm", np.nan))
        ),
        "state_norm_is_one": (
            abs(metadata.get("state_norm", 0.0) - 1.0) <= 1e-12
        ),
        "probability_sum_is_one": (
            abs(metadata.get("probability_sum", 0.0) - 1.0) <= 1e-12
        ),
        "operator_unitarity_is_valid": (
            metadata.get("operator_unitarity_residual", float("inf"))
            <= 1e-12
        ),
        "density_hermiticity_is_valid": (
            metadata.get("density_hermiticity_residual", float("inf"))
            <= 1e-12
        ),
    }

    return {
        "schema_version": 1,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "required_files": sorted(required),
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }


def generate_numerical_report() -> dict:
    activations = tuple(DEFAULT_ACTIVATIONS)

    rotation = rotation_operator(activations)
    gate = c3x_operator()
    operator = transition_operator(activations)

    state = operator @ initial_state()
    expected_state = reference_state(activations)
    rho = density_matrix(state)

    checks = {
        "rotation_shape_is_16_by_16": rotation.shape == (16, 16),
        "c3x_shape_is_16_by_16": gate.shape == (16, 16),
        "operator_shape_is_16_by_16": operator.shape == (16, 16),
        "rotation_is_unitary": np.linalg.norm(
            rotation.conj().T @ rotation - np.eye(16)
        ) <= 1e-12,
        "c3x_is_unitary": np.linalg.norm(
            gate.conj().T @ gate - np.eye(16)
        ) <= 1e-12,
        "operator_is_unitary": np.linalg.norm(
            operator.conj().T @ operator - np.eye(16)
        ) <= 1e-12,
        "state_is_normalized": abs(
            np.linalg.norm(state) - 1.0
        ) <= 1e-12,
        "state_matches_reference": np.linalg.norm(
            state - expected_state
        ) <= 1e-12,
        "density_trace_is_one": abs(
            np.trace(rho).real - 1.0
        ) <= 1e-12,
        "density_is_hermitian": np.linalg.norm(
            rho - rho.conj().T
        ) <= 1e-12,
        "density_is_positive_semidefinite": (
            np.min(np.linalg.eigvalsh(rho)) >= -1e-12
        ),
    }

    return {
        "schema_version": 1,
        "project": "QFLPN P2",
        "qubits": 4,
        "hilbert_dimension": 16,
        "activation_vector": list(activations),
        "operator_order": "U = C3X @ U_rot",
        "numerical_tolerance": 1e-12,
        "metrics": {
            "state_norm": float(np.linalg.norm(state)),
            "probability_sum": float(np.sum(np.abs(state) ** 2)),
            "operator_unitarity_residual": float(
                np.linalg.norm(
                    operator.conj().T @ operator - np.eye(16)
                )
            ),
            "density_trace": float(np.trace(rho).real),
            "density_hermiticity_residual": float(
                np.linalg.norm(rho - rho.conj().T)
            ),
            "density_minimum_eigenvalue": float(
                np.min(np.linalg.eigvalsh(rho))
            ),
        },
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def generate_pennylane_report() -> dict:
    activations = tuple(DEFAULT_ACTIVATIONS)

    reference = reference_state(activations)
    observed = pennylane_state(activations)

    difference = float(
        np.linalg.norm(observed - reference)
    )

    checks = {
        "state_shape_is_16": observed.shape == (16,),
        "state_is_finite": bool(np.all(np.isfinite(observed))),
        "state_is_normalized": (
            abs(np.linalg.norm(observed) - 1.0) <= 1e-12
        ),
        "probability_sum_is_one": (
            abs(np.sum(np.abs(observed) ** 2) - 1.0) <= 1e-12
        ),
        "matches_numpy_reference": difference <= 1e-12,
    }

    return {
        "schema_version": 1,
        "project": "QFLPN P2",
        "backend": "PennyLane default.qubit",
        "reference_backend": "NumPy",
        "activation_vector": list(activations),
        "maximum_state_difference": difference,
        "numerical_tolerance": 1e-12,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def main() -> int:
    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        artifact_report = validate_artifacts()
        numerical_report = generate_numerical_report()
        parity_report = generate_pennylane_report()

        write_json(
            REPORTS_DIR / "artifact_validation.json",
            artifact_report,
        )

        write_json(
            REPORTS_DIR / "numerical_validation.json",
            numerical_report,
        )

        write_json(
            REPORTS_DIR / "pennylane_parity.json",
            parity_report,
        )

    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        ImportError,
    ) as exc:
        print("FAIL:", exc)
        return 2

    reports = {
        "artifact_validation": artifact_report,
        "numerical_validation": numerical_report,
        "pennylane_parity": parity_report,
    }

    for name, report in reports.items():
        print(
            name,
            "=>",
            report.get("status"),
        )

    if not all(
        report.get("all_checks_pass") is True
        for report in reports.values()
    ):
        print("VERDICT: P2_REPORTS_REJECTED")
        return 1

    print("VERDICT: P2_REPORTS_GENERATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
