import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from P1.code.qflpn_transition_operator import c3x, kron_all, local_rotation_operator, qflpn_transition_operator, ry

ART = ROOT / "P1" / "artifacts"
TOL = 1e-12


def test_canonical_hilbert_dimension_and_shapes():
    operator = np.load(ART / "operator.npy", allow_pickle=False)
    initial = np.load(ART / "initial_state.npy", allow_pickle=False)
    final = np.load(ART / "final_state.npy", allow_pickle=False)
    rho = np.load(ART / "density_matrix.npy", allow_pickle=False)
    assert operator.shape == (16, 16)
    assert initial.shape == final.shape == (16,)
    assert rho.shape == (16, 16)


def test_big_endian_tensor_factor_order_behaviorally():
    zero = np.zeros(16, dtype=np.complex128)
    zero[0] = 1.0
    theta = 0.731
    target_zero = local_rotation_operator(theta, target=0, n_qubits=4) @ zero
    target_three = local_rotation_operator(theta, target=3, n_qubits=4) @ zero
    expected_zero = np.zeros(16, dtype=np.complex128)
    expected_zero[0], expected_zero[8] = math.cos(theta / 2), math.sin(theta / 2)
    expected_three = np.zeros(16, dtype=np.complex128)
    expected_three[0], expected_three[1] = math.cos(theta / 2), math.sin(theta / 2)
    assert np.linalg.norm(target_zero - expected_zero) <= TOL
    assert np.linalg.norm(target_three - expected_three) <= TOL


def test_c3x_truth_table_controls_zero_one_two_target_three():
    gate = c3x()
    for basis in range(16):
        expected = basis ^ 1 if (basis & 0b1110) == 0b1110 else basis
        assert int(np.argmax(np.abs(gate[:, basis]))) == expected


def test_production_operator_matches_explicit_gate_product():
    metadata = json.loads((ART / "reference_instance.json").read_text(encoding="utf-8"))
    local = kron_all(*(ry(theta) for theta in metadata["angles_rad"]))
    reconstructed = c3x() @ local
    production = qflpn_transition_operator(metadata["memberships"])
    assert np.linalg.norm(production - reconstructed, ord="fro") <= TOL
