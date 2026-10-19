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
    BASIS_ORDERING,
    CANONICAL_MEMBERSHIPS,
    HILBERT_SPACE_DIMENSION,
    NUMERICAL_TOLERANCE,
    QUBIT_COUNT,
)

P1 = ROOT / "P1"
ART = P1 / "artifacts"
REPORTS = P1 / "reports"

# Files that must exist and must be tracked by both inventories.
REQUIRED = [
    "P1/artifacts/operator.npy",
    "P1/artifacts/initial_state.npy",
    "P1/artifacts/final_state.npy",
    "P1/artifacts/density_matrix.npy",
    "P1/artifacts/reference_instance.json",
    "P1/reports/residuals.json",
    "P1/reports/independent_agreement.json",
    "P1/reports/test_log.json",
]

# Inventory files must exist physically, but must never inventory themselves.
INVENTORY_FILES = [
    "P1/MANIFEST.txt",
    "P1/SHA256SUMS.txt",
]

INVENTORY_FILE_SET = set(INVENTORY_FILES)
MANIFEST_REQUIRED = set(REQUIRED)

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str, errors: list[str]) -> None:
    """Record a validation failure without stopping subsequent checks."""
    errors.append(message)


def safe_relative(value: str) -> bool:
    """Accept only normalized, repository-relative POSIX paths."""
    if not value or "\\" in value:
        return False

    path = PurePosixPath(value)

    if path.is_absolute():
        return False

    if ".." in path.parts:
        return False

    if path.as_posix() != value:
        return False

    return True


def load_json(path: Path, label: str, errors: list[str]):
    """Load a JSON report and record errors instead of aborting validation."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(
            f"{label} validation error: {type(exc).__name__}: {exc}",
            errors,
        )
        return None


def validate_inventory(errors: list[str]):
    """Validate manifest/checksum structure and return parsed inventories."""
    manifest_path = P1 / "MANIFEST.txt"
    checksum_path = P1 / "SHA256SUMS.txt"

    manifest: list[str] = []
    checksum_map: dict[str, str] = {}

    # Physical existence is checked independently from inventory membership.
    for rel in INVENTORY_FILES:
        if not (ROOT / rel).is_file():
            fail(f"missing required inventory file: {rel}", errors)

    if not manifest_path.is_file() or not checksum_path.is_file():
        return manifest, checksum_map

    try:
        manifest_lines = manifest_path.read_text(
            encoding="utf-8"
        ).splitlines()

        manifest = [
            line.strip()
            for line in manifest_lines
            if line.strip()
        ]
    except Exception as exc:
        fail(
            f"manifest read error: {type(exc).__name__}: {exc}",
            errors,
        )

    if len(manifest) != len(set(manifest)):
        fail("manifest contains duplicate paths", errors)

    for rel in manifest:
        if not safe_relative(rel):
            fail(f"unsafe manifest path: {rel}", errors)
            continue

        if rel in INVENTORY_FILE_SET:
            fail(
                f"self-referential inventory file listed in manifest: {rel}",
                errors,
            )
            continue

        if not (ROOT / rel).is_file():
            fail(f"manifest path does not exist: {rel}", errors)

    # Every tracked required artifact/report must appear in the manifest.
    for rel in sorted(MANIFEST_REQUIRED):
        if rel not in manifest:
            fail(
                f"required file absent from manifest: {rel}",
                errors,
            )

    # Parse SHA-256 inventory.
    try:
        checksum_lines = checksum_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except Exception as exc:
        fail(
            f"checksum inventory read error: {type(exc).__name__}: {exc}",
            errors,
        )
        checksum_lines = []

    for line_no, line in enumerate(checksum_lines, 1):
        parts = line.split("  ", 1)

        if len(parts) != 2 or not HEX64.fullmatch(parts[0]):
            fail(f"malformed checksum line {line_no}", errors)
            continue

        digest, rel = parts

        if rel in checksum_map:
            fail(f"duplicate checksum path: {rel}", errors)
            continue

        checksum_map[rel] = digest

    # Inventory files must not be included in their own checksum inventory.
    for rel in INVENTORY_FILES:
        if rel in checksum_map:
            fail(
                f"self-referential inventory file listed in SHA-256 inventory: {rel}",
                errors,
            )

    # The manifest and checksum inventory must describe exactly the same files.
    manifest_paths = set(manifest)

    checksum_paths = set(checksum_map) - INVENTORY_FILE_SET

    if manifest_paths != checksum_paths:
        missing_from_checksums = sorted(
            manifest_paths - checksum_paths
        )
        missing_from_manifest = sorted(
            checksum_paths - manifest_paths
        )

        fail(
            "manifest and checksum path sets differ "
            f"(missing from checksums: {missing_from_checksums}; "
            f"missing from manifest: {missing_from_manifest})",
            errors,
        )

    # Recalculate every checksum from the actual file contents.
    for rel, expected in checksum_map.items():
        if not safe_relative(rel):
            fail(f"unsafe checksum path: {rel}", errors)
            continue

        if rel in INVENTORY_FILE_SET:
            continue

        path = ROOT / rel

        if not path.is_file():
            fail(f"checksum path does not exist: {rel}", errors)
            continue

        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception as exc:
            fail(
                f"checksum read error for {rel}: "
                f"{type(exc).__name__}: {exc}",
                errors,
            )
            continue

        if actual != expected:
            fail(f"SHA-256 mismatch: {rel}", errors)

    return manifest, checksum_map


def validate_metadata(errors: list[str]) -> None:
    metadata = load_json(
        ART / "reference_instance.json",
        "metadata",
        errors,
    )

    if metadata is None:
        return

    if not isinstance(metadata, dict):
        fail("metadata root must be a JSON object", errors)
        return

    if metadata.get("qubit_count") != QUBIT_COUNT:
        fail("metadata qubit_count mismatch", errors)

    if metadata.get("hilbert_space_dimension") != HILBERT_SPACE_DIMENSION:
        fail("metadata Hilbert dimension mismatch", errors)

    if metadata.get("basis_ordering") != BASIS_ORDERING:
        fail("metadata basis ordering mismatch", errors)

    if (
        metadata.get("initial_state_label") != "|0000>"
        or metadata.get("initial_state_basis_index") != 0
    ):
        fail("metadata initial state mismatch", errors)

    if metadata.get("memberships") != list(CANONICAL_MEMBERSHIPS):
        fail("metadata canonical memberships mismatch", errors)

    if metadata.get("repository_revision") in (None, "", "UNKNOWN"):
        fail("repository revision missing or UNKNOWN", errors)

    if metadata.get("theta_formula") != (
        "theta_i = 2 * asin(sqrt(lambda_i))"
    ):
        fail("canonical fuzzy encoding formula mismatch", errors)

    expected_operator_expression = (
        "C3X @ (RY(theta_1) kron RY(theta_2) "
        "kron RY(theta_3) kron RY(theta_4))"
    )

    if metadata.get("operator_expression") != expected_operator_expression:
        fail("global operator expression mismatch", errors)

    if (
        metadata.get("c3x_controls") != [0, 1, 2]
        or metadata.get("c3x_target") != 3
    ):
        fail("C3X control/target metadata mismatch", errors)

    gate_sequence = metadata.get("gate_sequence")

    if not isinstance(gate_sequence, list) or len(gate_sequence) != 5:
        fail("gate sequence missing or incomplete", errors)

    for key in (
        "python_version",
        "numpy_version",
        "scipy_version",
        "numeric_dtype",
        "operator_expression",
    ):
        if not metadata.get(key):
            fail(f"metadata field missing: {key}", errors)


def validate_arrays(errors: list[str]) -> None:
    try:
        operator = np.load(
            ART / "operator.npy",
            allow_pickle=False,
        )
        initial = np.load(
            ART / "initial_state.npy",
            allow_pickle=False,
        )
        final = np.load(
            ART / "final_state.npy",
            allow_pickle=False,
        )
        rho = np.load(
            ART / "density_matrix.npy",
            allow_pickle=False,
        )

        expected_shapes = [
            (16, 16),
            (16,),
            (16,),
            (16, 16),
        ]

        arrays = (
            operator,
            initial,
            final,
            rho,
        )

        labels = (
            "operator",
            "initial",
            "final",
            "rho",
        )

        for label, array, shape in zip(
            labels,
            arrays,
            expected_shapes,
        ):
            if array.shape != shape:
                fail(
                    f"{label} shape mismatch: "
                    f"{array.shape} != {shape}",
                    errors,
                )

            if (
                not np.isfinite(array.real).all()
                or not np.isfinite(array.imag).all()
            ):
                fail(
                    f"{label} contains non-finite values",
                    errors,
                )

        expected_initial = np.zeros(
            16,
            dtype=np.complex128,
        )
        expected_initial[0] = 1.0

        if initial.shape == expected_initial.shape:
            initial_difference = np.linalg.norm(
                initial - expected_initial
            )

            if initial_difference > NUMERICAL_TOLERANCE:
                fail(
                    "initial state is not |0000>",
                    errors,
                )

    except Exception as exc:
        fail(
            f"array validation error: {type(exc).__name__}: {exc}",
            errors,
        )


def validate_reports(errors: list[str]) -> None:
    residuals = load_json(
        REPORTS / "residuals.json",
        "residual report",
        errors,
    )

    independent = load_json(
        REPORTS / "independent_agreement.json",
        "independent agreement report",
        errors,
    )

    test_log = load_json(
        REPORTS / "test_log.json",
        "test log",
        errors,
    )

    if residuals is not None:
        if not isinstance(residuals, dict):
            fail("residual report root must be a JSON object", errors)
        else:
            if (
                residuals.get("status") != "PASS"
                or residuals.get("all_checks_pass") is not True
            ):
                fail("residual report is not PASS", errors)

            if residuals.get("numerical_tolerance") != NUMERICAL_TOLERANCE:
                fail("residual tolerance mismatch", errors)

    if independent is not None:
        if not isinstance(independent, dict):
            fail(
                "independent agreement report root must be a JSON object",
                errors,
            )
        else:
            if (
                independent.get("status") != "PASS"
                or independent.get("all_checks_pass") is not True
            ):
                fail("independent agreement is not PASS", errors)

            if (
                independent.get("numerical_tolerance")
                != NUMERICAL_TOLERANCE
            ):
                fail("independent tolerance mismatch", errors)

            for key in (
                "operator_difference_frobenius",
                "state_difference_l2",
                "state_fidelity_error",
            ):
                value = independent.get(key)

                if (
                    not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or value < 0
                    or value > NUMERICAL_TOLERANCE
                ):
                    fail(
                        f"independent metric invalid or out of tolerance: {key}",
                        errors,
                    )

    if test_log is None:
        return

    if not isinstance(test_log, dict):
        fail("test log root must be a JSON object", errors)
        return

    checks = test_log.get("checks", {})

    if test_log.get("verdict") != "P1_PENDING_PACKAGE_INTEGRITY":
        fail(
            "test log is rejected or not pending package integrity",
            errors,
        )

    if not isinstance(checks, dict) or not checks or not all(
        value is True for value in checks.values()
    ):
        fail(
            "one or more aggregated test-log checks failed",
            errors,
        )

    pytest = test_log.get("pytest", {})

    if not isinstance(pytest, dict):
        fail("pytest section missing or invalid", errors)
        return

    if pytest.get("exit_code") != 0 or pytest.get("tests", 0) <= 0:
        fail(
            "pytest exit code or test count invalid",
            errors,
        )

    if (
        pytest.get("failures") != 0
        or pytest.get("errors") != 0
        or pytest.get("skipped") != 0
    ):
        fail(
            "pytest failures/errors/skips must all be zero",
            errors,
        )

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

    observed_names = {
        entry.rsplit("::", 1)[-1]
        for entry in observed_cases
    }

    missing_cases = sorted(
        required_case_suffixes - observed_names
    )

    if missing_cases:
        fail(
            "required acceptance test cases missing: "
            + ", ".join(missing_cases),
            errors,
        )


def main() -> None:
    errors: list[str] = []

    # Required artifact and report files must exist physically.
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            fail(f"missing required file: {rel}", errors)

    # Validate inventories independently from tracked-file requirements.
    manifest, checksum_map = validate_inventory(errors)

    # Validate canonical metadata, numerical artifacts, and evidence reports.
    validate_metadata(errors)
    validate_arrays(errors)
    validate_reports(errors)

    verdict = "P1_ACCEPTED" if not errors else "P1_REJECTED"

    print(
        json.dumps(
            {
                "verdict": verdict,
                "manifest_entries": len(manifest),
                "checksum_entries": len(checksum_map),
                "errors": errors,
            },
            indent=2,
        )
    )

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
