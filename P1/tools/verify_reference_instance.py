"""Verify the canonical P1 instance and independent numerical agreement."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from P1.code.qflpn_reference import fuzzy_to_angle
from P1.code.qflpn_transition_operator import (
    c3x,
    kron_all,
    local_rotation_operator,
    qflpn_transition_operator,
    ry,
)
from P1.tests.independent_reference import independent_global_operator
from P1.tools.constants import (
    BASIS_ORDERING,
    CANONICAL_MEMBERSHIPS,
    GATE_SEQUENCE,
    HILBERT_SPACE_DIMENSION,
    INITIAL_STATE_LABEL,
    NUMERICAL_TOLERANCE,
    NUMERIC_DTYPE,
    OPERATOR_EXPRESSION,
    QUBIT_COUNT,
)

ART = ROOT / "P1" / "artifacts"
OUT = ROOT / "P1" / "reports" / "independent_agreement.json"


def write_report(report: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def fail_report(message: str) -> None:
    report = {
        "status": "FAIL",
        "all_checks_pass": False,
        "error": message,
        "checks": {},
    }
    write_report(report)
    print(json.dumps(report, indent=2))
    raise SystemExit(1)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def finite_array(value: np.ndarray) -> bool:
    return bool(
        np.isfinite(value.real).all()
        and np.isfinite(value.imag).all()
    )


def main() -> None:
    try:
        metadata_path = ART / "reference_instance.json"
        require(metadata_path.is_file(), "Missing reference_instance.json")

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        require(isinstance(metadata, dict), "Metadata must be a JSON object")

        expected_memberships = np.asarray(
            CANONICAL_MEMBERSHIPS, dtype=np.float64
        )
        expected_angles = np.asarray(
            [fuzzy_to_angle(float(x)) for x in expected_memberships],
            dtype=np.float64,
        )

        memberships_raw = metadata.get("memberships")
        angles_raw = metadata.get("angles_rad")

        require(
            isinstance(memberships_raw, list) and len(memberships_raw) == QUBIT_COUNT,
            "Invalid memberships metadata",
        )
        require(
            isinstance(angles_raw, list) and len(angles_raw) == QUBIT_COUNT,
            "Invalid angles_rad metadata",
        )

        require(
            all(
                isinstance(x, (int, float)) and not isinstance(x, bool)
                for x in memberships_raw
            ),
            "Membership values must be numeric and must not be booleans",
        )
        require(
            all(
                isinstance(x, (int, float)) and not isinstance(x, bool)
                for x in angles_raw
            ),
            "Angle values must be numeric and must not be booleans",
        )

        memberships = np.asarray(memberships_raw, dtype=np.float64)
        angles = np.asarray(angles_raw, dtype=np.float64)

        require(finite_array(memberships), "Non-finite membership values")
        require(finite_array(angles), "Non-finite angle values")

        metadata_checks = {
            "schema_version": metadata.get("schema_version") == 1,
            "instance_id": metadata.get("instance_id") == "P1-CANONICAL-4Q-001",
            "qubit_count": metadata.get("qubit_count") == QUBIT_COUNT,
            "hilbert_space_dimension": (
                metadata.get("hilbert_space_dimension")
                == HILBERT_SPACE_DIMENSION
            ),
            "basis_ordering": metadata.get("basis_ordering") == BASIS_ORDERING,
            "initial_state_label": (
                metadata.get("initial_state_label") == INITIAL_STATE_LABEL
            ),
            "initial_state_basis_index": (
                metadata.get("initial_state_basis_index") == 0
            ),
            "operator_expression": (
                metadata.get("operator_expression") == OPERATOR_EXPRESSION
            ),
            "gate_sequence": metadata.get("gate_sequence") == list(GATE_SEQUENCE),
            "c3x_controls": metadata.get("c3x_controls") == [0, 1, 2],
            "c3x_target": metadata.get("c3x_target") == 3,
            "composition_convention": (
                metadata.get("composition_convention")
                == "rightmost operator acts first"
            ),
            "numeric_dtype": metadata.get("numeric_dtype") == NUMERIC_DTYPE,
            "array_serialization": (
                metadata.get("array_serialization")
                == "NumPy .npy, allow_pickle=False, C-order arrays"
            ),
        }

        membership_error = float(
            np.max(np.abs(memberships - expected_memberships))
        )
        angle_error = float(np.max(np.abs(angles - expected_angles)))

        metadata_checks["canonical_memberships"] = (
            membership_error <= NUMERICAL_TOLERANCE
        )
        metadata_checks["canonical_angles"] = (
            angle_error <= NUMERICAL_TOLERANCE
        )

        require(
            all(metadata_checks.values()),
            "Reference metadata does not match the canonical P1 specification",
        )

        operator_path = ART / "operator.npy"
        initial_path = ART / "initial_state.npy"
        final_path = ART / "final_state.npy"

        for path in (operator_path, initial_path, final_path):
            require(path.is_file(), f"Missing artifact: {path.name}")

        operator_saved = np.load(operator_path, allow_pickle=False)
        initial = np.load(initial_path, allow_pickle=False)
        final_saved = np.load(final_path, allow_pickle=False)

        require(
            operator_saved.shape == (
                HILBERT_SPACE_DIMENSION,
                HILBERT_SPACE_DIMENSION,
            ),
            "Invalid saved operator shape",
        )
        require(
            initial.shape == (HILBERT_SPACE_DIMENSION,),
            "Invalid initial state shape",
        )
        require(
            final_saved.shape == (HILBERT_SPACE_DIMENSION,),
            "Invalid final state shape",
        )

        for name, array in (
            ("operator", operator_saved),
            ("initial_state", initial),
            ("final_state", final_saved),
        ):
            require(
                np.issubdtype(array.dtype, np.number),
                f"{name} must have a numeric dtype",
            )
            require(finite_array(array), f"{name} contains non-finite values")

        production = qflpn_transition_operator(memberships.tolist())
        local = kron_all(*(ry(float(theta)) for theta in angles))
        reconstructed = c3x() @ local
        independent = independent_global_operator(memberships.tolist())

        operator_difference = float(
            np.linalg.norm(production - independent, ord="fro")
        )
        saved_operator_difference = float(
            np.linalg.norm(operator_saved - production, ord="fro")
        )
        construction_difference = float(
            np.linalg.norm(production - reconstructed, ord="fro")
        )

        production_state = production @ initial
        independent_state = independent @ initial

        state_difference = float(
            np.linalg.norm(production_state - independent_state, ord=2)
        )
        overlap = np.vdot(independent_state, production_state)
        fidelity = float(abs(overlap) ** 2)
        fidelity_error = float(abs(1.0 - fidelity))
        saved_state_difference = float(
            np.linalg.norm(final_saved - production_state, ord=2)
        )

        zero = np.zeros(HILBERT_SPACE_DIMENSION, dtype=np.complex128)
        zero[0] = 1.0
        theta_probe = 0.731

        left_target = local_rotation_operator(
            theta_probe, target=0, n_qubits=QUBIT_COUNT
        ) @ zero
        right_target = local_rotation_operator(
            theta_probe, target=3, n_qubits=QUBIT_COUNT
        ) @ zero

        expected_left = np.zeros_like(zero)
        expected_left[0] = math.cos(theta_probe / 2)
        expected_left[8] = math.sin(theta_probe / 2)

        expected_right = np.zeros_like(zero)
        expected_right[0] = math.cos(theta_probe / 2)
        expected_right[1] = math.sin(theta_probe / 2)

        big_endian_left = bool(
            np.linalg.norm(left_target - expected_left)
            <= NUMERICAL_TOLERANCE
        )
        big_endian_right = bool(
            np.linalg.norm(right_target - expected_right)
            <= NUMERICAL_TOLERANCE
        )

        gate = c3x()
        truth_table = all(
            int(np.argmax(np.abs(gate[:, basis])))
            == (
                basis ^ 1
                if (basis & 0b1110) == 0b1110
                else basis
            )
            for basis in range(HILBERT_SPACE_DIMENSION)
        )

        checks = {
            **metadata_checks,
            "operator_agreement_frobenius": (
                operator_difference <= NUMERICAL_TOLERANCE
            ),
            "saved_operator_matches_production": (
                saved_operator_difference <= NUMERICAL_TOLERANCE
            ),
            "constructive_gate_reconstruction": (
                construction_difference <= NUMERICAL_TOLERANCE
            ),
            "state_difference_l2": (
                state_difference <= NUMERICAL_TOLERANCE
            ),
            "state_fidelity_error": (
                fidelity_error <= NUMERICAL_TOLERANCE
            ),
            "saved_final_state_matches_production": (
                saved_state_difference <= NUMERICAL_TOLERANCE
            ),
            "big_endian_qubit0_leftmost": big_endian_left,
            "big_endian_qubit3_rightmost": big_endian_right,
            "c3x_truth_table_controls_0_1_2_target_3": truth_table,
        }

        report = {
            "numerical_tolerance": NUMERICAL_TOLERANCE,
            "membership_max_abs_error": membership_error,
            "angle_max_abs_error": angle_error,
            "operator_difference_frobenius": operator_difference,
            "saved_operator_difference_frobenius": saved_operator_difference,
            "constructive_operator_difference_frobenius": construction_difference,
            "state_difference_l2": state_difference,
            "state_fidelity_squared_overlap": fidelity,
            "state_fidelity_error": fidelity_error,
            "saved_final_state_difference_l2": saved_state_difference,
            "big_endian_behavior": {
                "qubit0_leftmost": big_endian_left,
                "qubit3_rightmost": big_endian_right,
            },
            "c3x_truth_table_pass": truth_table,
            "independent_implementation_imports_production": False,
            "checks": checks,
            "all_checks_pass": all(checks.values()),
            "status": "PASS" if all(checks.values()) else "FAIL",
        }

        write_report(report)
        print(json.dumps(report, indent=2))

        if not report["all_checks_pass"]:
            raise SystemExit(1)

    except SystemExit:
        raise
    except Exception as exc:
        fail_report(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
