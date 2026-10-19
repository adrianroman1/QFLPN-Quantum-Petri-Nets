"""Verify gate convention, operator construction, and independent agreement."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from P1.code.qflpn_transition_operator import (
    c3x, kron_all, local_rotation_operator, qflpn_transition_operator, ry,
)
from P1.tests.independent_reference import independent_global_operator
from P1.tools.constants import NUMERICAL_TOLERANCE

ART = ROOT / "P1" / "artifacts"
OUT = ROOT / "P1" / "reports" / "independent_agreement.json"


def main() -> None:
    metadata = json.loads((ART / "reference_instance.json").read_text(encoding="utf-8"))
    memberships = metadata["memberships"]
    angles = metadata["angles_rad"]
    operator_saved = np.load(ART / "operator.npy", allow_pickle=False)
    initial = np.load(ART / "initial_state.npy", allow_pickle=False)
    final_saved = np.load(ART / "final_state.npy", allow_pickle=False)

    production = qflpn_transition_operator(memberships)
    local = kron_all(*(ry(theta) for theta in angles))
    reconstructed = c3x() @ local
    independent = independent_global_operator(memberships)
    operator_difference = float(np.linalg.norm(production - independent, ord="fro"))
    saved_operator_difference = float(np.linalg.norm(operator_saved - production, ord="fro"))
    construction_difference = float(np.linalg.norm(production - reconstructed, ord="fro"))

    production_state = production @ initial
    independent_state = independent @ initial
    state_difference = float(np.linalg.norm(production_state - independent_state, ord=2))
    overlap = np.vdot(independent_state, production_state)
    fidelity = float(abs(overlap) ** 2)
    fidelity_error = float(abs(1.0 - fidelity))
    saved_state_difference = float(np.linalg.norm(final_saved - production_state, ord=2))

    # Behavioral big-endian test: target qubit 0 maps |0000> amplitude to |1000> (index 8).
    zero = np.zeros(16, dtype=np.complex128)
    zero[0] = 1.0
    theta_probe = 0.731
    left_target = local_rotation_operator(theta_probe, target=0, n_qubits=4) @ zero
    right_target = local_rotation_operator(theta_probe, target=3, n_qubits=4) @ zero
    expected_left = np.zeros(16, dtype=np.complex128)
    expected_left[0], expected_left[8] = math.cos(theta_probe / 2), math.sin(theta_probe / 2)
    expected_right = np.zeros(16, dtype=np.complex128)
    expected_right[0], expected_right[1] = math.cos(theta_probe / 2), math.sin(theta_probe / 2)
    big_endian_left = bool(np.linalg.norm(left_target - expected_left) <= NUMERICAL_TOLERANCE)
    big_endian_right = bool(np.linalg.norm(right_target - expected_right) <= NUMERICAL_TOLERANCE)

    gate = c3x()
    truth_table = all(
        int(np.argmax(np.abs(gate[:, basis]))) == (basis ^ 1 if (basis & 0b1110) == 0b1110 else basis)
        for basis in range(16)
    )
    checks = {
        "operator_agreement_frobenius": operator_difference <= NUMERICAL_TOLERANCE,
        "saved_operator_matches_production": saved_operator_difference <= NUMERICAL_TOLERANCE,
        "constructive_gate_reconstruction": construction_difference <= NUMERICAL_TOLERANCE,
        "state_difference_l2": state_difference <= NUMERICAL_TOLERANCE,
        "state_fidelity_error": fidelity_error <= NUMERICAL_TOLERANCE,
        "saved_final_state_matches_production": saved_state_difference <= NUMERICAL_TOLERANCE,
        "big_endian_qubit0_leftmost": big_endian_left,
        "big_endian_qubit3_rightmost": big_endian_right,
        "c3x_truth_table_controls_0_1_2_target_3": truth_table,
    }
    report = {
        "numerical_tolerance": NUMERICAL_TOLERANCE,
        "operator_difference_frobenius": operator_difference,
        "saved_operator_difference_frobenius": saved_operator_difference,
        "constructive_operator_difference_frobenius": construction_difference,
        "state_difference_l2": state_difference,
        "state_fidelity_squared_overlap": fidelity,
        "state_fidelity_error": fidelity_error,
        "saved_final_state_difference_l2": saved_state_difference,
        "big_endian_behavior": {"qubit0_leftmost": big_endian_left, "qubit3_rightmost": big_endian_right},
        "c3x_truth_table_pass": truth_table,
        "independent_implementation_imports_production": False,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["all_checks_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
