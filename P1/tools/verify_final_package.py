"""Fail-closed final verifier for P1 artifacts, evidence, manifest, and hashes."""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path, PurePosixPath

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from P1.tools.constants import (
    BASIS_ORDERING, CANONICAL_MEMBERSHIPS, HILBERT_SPACE_DIMENSION,
    NUMERICAL_TOLERANCE, QUBIT_COUNT,
)

P1 = ROOT / "P1"
ART = P1 / "artifacts"
REPORTS = P1 / "reports"
REQUIRED = [
    "P1/artifacts/operator.npy", "P1/artifacts/initial_state.npy",
    "P1/artifacts/final_state.npy", "P1/artifacts/density_matrix.npy",
    "P1/artifacts/reference_instance.json", "P1/reports/residuals.json",
    "P1/reports/independent_agreement.json", "P1/reports/test_log.json",
    "P1/MANIFEST.txt", "P1/SHA256SUMS.txt",
]
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def safe_relative(value: str) -> bool:
    p = PurePosixPath(value)
    return bool(value) and not p.is_absolute() and ".." not in p.parts and "\\" not in value


def main() -> None:
    errors: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            fail(f"missing required file: {rel}", errors)
    if errors:
        print(json.dumps({"verdict": "P1_REJECTED", "errors": errors}, indent=2))
        raise SystemExit(1)

    manifest_lines = (P1 / "MANIFEST.txt").read_text(encoding="utf-8").splitlines()
    manifest = [line.strip() for line in manifest_lines if line.strip()]
    if len(manifest) != len(set(manifest)):
        fail("manifest contains duplicate paths", errors)
    for rel in manifest:
        if not safe_relative(rel):
            fail(f"unsafe manifest path: {rel}", errors)
        elif not (ROOT / rel).is_file():
            fail(f"manifest path does not exist: {rel}", errors)
    for rel in REQUIRED:
        if rel not in manifest:
            fail(f"required file absent from manifest: {rel}", errors)
    if "P1/MANIFEST.txt" in manifest or "P1/SHA256SUMS.txt" in manifest:
        fail("self-referential inventory file listed in manifest", errors)

    checksum_map: dict[str, str] = {}
    for line_no, line in enumerate((P1 / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("  ", 1)
        if len(parts) != 2 or not HEX64.fullmatch(parts[0]):
            fail(f"malformed checksum line {line_no}", errors)
            continue
        digest, rel = parts
        if rel in checksum_map:
            fail(f"duplicate checksum path: {rel}", errors)
        checksum_map[rel] = digest
    if set(manifest) != set(checksum_map):
        fail("manifest and checksum path sets differ", errors)
    for rel, expected in checksum_map.items():
        if not safe_relative(rel):
            fail(f"unsafe checksum path: {rel}", errors)
            continue
        path = ROOT / rel
        if not path.is_file():
            fail(f"checksum path does not exist: {rel}", errors)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            fail(f"SHA-256 mismatch: {rel}", errors)

    try:
        metadata = json.loads((ART / "reference_instance.json").read_text(encoding="utf-8"))
        if metadata.get("qubit_count") != QUBIT_COUNT:
            fail("metadata qubit_count mismatch", errors)
        if metadata.get("hilbert_space_dimension") != HILBERT_SPACE_DIMENSION:
            fail("metadata Hilbert dimension mismatch", errors)
        if metadata.get("basis_ordering") != BASIS_ORDERING:
            fail("metadata basis ordering mismatch", errors)
        if metadata.get("initial_state_label") != "|0000>" or metadata.get("initial_state_basis_index") != 0:
            fail("metadata initial state mismatch", errors)
        if metadata.get("memberships") != list(CANONICAL_MEMBERSHIPS):
            fail("metadata canonical memberships mismatch", errors)
        if metadata.get("repository_revision") in (None, "", "UNKNOWN"):
            fail("repository revision missing or UNKNOWN", errors)
        if metadata.get("theta_formula") != "theta_i = 2 * asin(sqrt(lambda_i))":
            fail("canonical fuzzy encoding formula mismatch", errors)
        if metadata.get("operator_expression") != (
            "C3X @ (RY(theta_1) kron RY(theta_2) kron RY(theta_3) kron RY(theta_4))"
        ):
            fail("global operator expression mismatch", errors)
        if metadata.get("c3x_controls") != [0, 1, 2] or metadata.get("c3x_target") != 3:
            fail("C3X control/target metadata mismatch", errors)
        if metadata.get("gate_sequence") is None or len(metadata["gate_sequence"]) != 5:
            fail("gate sequence missing or incomplete", errors)
        for key in ("python_version", "numpy_version", "scipy_version", "numeric_dtype", "operator_expression"):
            if not metadata.get(key):
                fail(f"metadata field missing: {key}", errors)
    except Exception as exc:
        fail(f"metadata validation error: {type(exc).__name__}: {exc}", errors)

    try:
        operator = np.load(ART / "operator.npy", allow_pickle=False)
        initial = np.load(ART / "initial_state.npy", allow_pickle=False)
        final = np.load(ART / "final_state.npy", allow_pickle=False)
        rho = np.load(ART / "density_matrix.npy", allow_pickle=False)
        expected_shapes = [(16, 16), (16,), (16,), (16, 16)]
        for label, array, shape in zip(("operator", "initial", "final", "rho"),
                                       (operator, initial, final, rho), expected_shapes):
            if array.shape != shape:
                fail(f"{label} shape mismatch: {array.shape} != {shape}", errors)
            if not np.isfinite(array.real).all() or not np.isfinite(array.imag).all():
                fail(f"{label} contains non-finite values", errors)
        expected_initial = np.zeros(16, dtype=np.complex128)
        expected_initial[0] = 1.0
        if np.linalg.norm(initial - expected_initial) > NUMERICAL_TOLERANCE:
            fail("initial state is not |0000>", errors)
    except Exception as exc:
        fail(f"array validation error: {type(exc).__name__}: {exc}", errors)

    try:
        residuals = json.loads((REPORTS / "residuals.json").read_text(encoding="utf-8"))
        independent = json.loads((REPORTS / "independent_agreement.json").read_text(encoding="utf-8"))
        test_log = json.loads((REPORTS / "test_log.json").read_text(encoding="utf-8"))
        if residuals.get("status") != "PASS" or residuals.get("all_checks_pass") is not True:
            fail("residual report is not PASS", errors)
        if residuals.get("numerical_tolerance") != NUMERICAL_TOLERANCE:
            fail("residual tolerance mismatch", errors)
        if independent.get("status") != "PASS" or independent.get("all_checks_pass") is not True:
            fail("independent agreement is not PASS", errors)
        if independent.get("numerical_tolerance") != NUMERICAL_TOLERANCE:
            fail("independent tolerance mismatch", errors)
        for key in ("operator_difference_frobenius", "state_difference_l2", "state_fidelity_error"):
            value = independent.get(key)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value > NUMERICAL_TOLERANCE:
                fail(f"independent metric invalid or out of tolerance: {key}", errors)
        checks = test_log.get("checks", {})
        if test_log.get("verdict") != "P1_PENDING_PACKAGE_INTEGRITY":
            fail("test log is rejected or not pending package integrity", errors)
        if not checks or not all(checks.values()):
            fail("one or more aggregated test-log checks failed", errors)
        pytest = test_log.get("pytest", {})
        if pytest.get("exit_code") != 0 or pytest.get("tests", 0) <= 0:
            fail("pytest exit code or test count invalid", errors)
        if pytest.get("failures") != 0 or pytest.get("errors") != 0 or pytest.get("skipped") != 0:
            fail("pytest failures/errors/skips must all be zero", errors)
        observed_cases = set(pytest.get("test_cases", []))
        required_case_suffixes = {
            "test_density_matrix_trace_is_one",
            "test_density_matrix_is_hermitian",
            "test_density_matrix_is_positive_semidefinite",
            "test_global_operator_is_unitary",
            "test_zero_membership_maps_to_zero_angle_and_identity_rotation",
            "test_unit_membership_maps_to_pi_angle",
            "test_canonical_hilbert_dimension_and_shapes",
            "test_big_endian_tensor_factor_order_behaviorally",
            "test_c3x_truth_table_controls_zero_one_two_target_three",
            "test_production_operator_matches_explicit_gate_product",
            "test_production_and_independent_operators_agree",
            "test_production_and_independent_state_vectors_agree",
            "test_squared_pure_state_fidelity_is_one_within_tolerance",
            "test_all_canonical_artifacts_exist_and_are_finite",
            "test_metadata_records_canonical_instance_and_environment",
            "test_density_matrix_is_outer_product_of_saved_final_state",
            "test_sha256_helper_matches_standard_library",
            "test_inventory_is_sorted_and_excludes_self_referential_files",
            "test_preflight_source_modules_and_report_generator_exist",
            "test_initial_state_is_the_canonical_zero_basis_vector",
        }
        observed_names = {entry.rsplit("::", 1)[-1] for entry in observed_cases}
        missing_cases = sorted(required_case_suffixes - observed_names)
        if missing_cases:
            fail("required acceptance test cases missing: " + ", ".join(missing_cases), errors)
    except Exception as exc:
        fail(f"report validation error: {type(exc).__name__}: {exc}", errors)

    verdict = "P1_ACCEPTED" if not errors else "P1_REJECTED"
    print(json.dumps({"verdict": verdict, "manifest_entries": len(manifest),
                      "checksum_entries": len(checksum_map), "errors": errors}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
