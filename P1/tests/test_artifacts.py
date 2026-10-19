import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "P1" / "artifacts"
TOL = 1e-12


def test_all_canonical_artifacts_exist_and_are_finite():
    names = ["operator.npy", "initial_state.npy", "final_state.npy", "density_matrix.npy", "reference_instance.json"]
    for name in names:
        assert (ART / name).is_file(), name
    for name in names[:4]:
        array = np.load(ART / name, allow_pickle=False)
        assert np.isfinite(array.real).all()
        assert np.isfinite(array.imag).all()


def test_metadata_records_canonical_instance_and_environment():
    metadata = json.loads((ART / "reference_instance.json").read_text(encoding="utf-8"))
    assert metadata["qubit_count"] == 4
    assert metadata["hilbert_space_dimension"] == 16
    assert metadata["basis_ordering"] == "big-endian lexicographic"
    assert metadata["initial_state_label"] == "|0000>"
    assert metadata["theta_formula"] == "theta_i = 2 * asin(sqrt(lambda_i))"
    assert metadata["numeric_dtype"] == "complex128"
    assert metadata["operator_expression"] == (
        "C3X @ (RY(theta_1) kron RY(theta_2) kron RY(theta_3) kron RY(theta_4))"
    )
    assert metadata["c3x_controls"] == [0, 1, 2]
    assert metadata["c3x_target"] == 3
    assert metadata["python_version"] and metadata["numpy_version"] and metadata["scipy_version"]
    assert metadata["repository_revision"] not in (None, "", "UNKNOWN")
    for membership, angle in zip(metadata["memberships"], metadata["angles_rad"]):
        expected = 2.0 * np.arcsin(np.sqrt(membership))
        assert abs(angle - expected) <= TOL


def test_preflight_source_modules_and_report_generator_exist():
    required = [
        ROOT / "P1" / "code" / "qflpn_reference.py",
        ROOT / "P1" / "code" / "qflpn_transition_operator.py",
        ROOT / "P1" / "tests" / "independent_reference.py",
        ROOT / "P1" / "tools" / "generate_p1_reports.py",
    ]
    assert all(path.is_file() for path in required)


def test_initial_state_is_the_canonical_zero_basis_vector():
    initial = np.load(ART / "initial_state.npy", allow_pickle=False)
    expected = np.zeros(16, dtype=np.complex128)
    expected[0] = 1.0
    assert np.linalg.norm(initial - expected) <= TOL


def test_density_matrix_is_outer_product_of_saved_final_state():
    state = np.load(ART / "final_state.npy", allow_pickle=False)
    rho = np.load(ART / "density_matrix.npy", allow_pickle=False)
    assert np.linalg.norm(rho - np.outer(state, state.conj()), ord="fro") <= TOL
