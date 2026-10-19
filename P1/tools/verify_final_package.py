"""Fail-closed final verifier for P1 artifacts, evidence, manifest, and hashes."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from P1.tools.constants import (
    BASIS_ORDERING,
    CANONICAL_MEMBERSHIPS,
    GATE_SEQUENCE,
    HILBERT_SPACE_DIMENSION,
    NUMERICAL_TOLERANCE,
    QUBIT_COUNT,
)

P1 = ROOT / "P1"
ART = P1 / "artifacts"
REPORTS = P1 / "reports"

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

INVENTORY_FILES = [
    "P1/MANIFEST.txt",
    "P1/SHA256SUMS.txt",
]

INVENTORY_FILE_SET = set(INVENTORY_FILES)
MANIFEST_REQUIRED = set(REQUIRED)

HEX64 = re.compile(r"^[0-9a-f]{64}$")

RESIDUAL_KEYS = (
    "operator_unitarity_frobenius",
    "density_trace_absolute_error",
    "density_hermiticity_frobenius",
    "density_psd_residual",
    "state_norm_absolute_error",
    "state_evolution_l2_residual",
    "pure_state_density_frobenius",
)

FINITE_CHECK_KEYS = (
    "operator_finite",
    "initial_state_finite",
    "final_state_finite",
    "density_matrix_finite",
)

INDEPENDENT_CHECK_KEYS = (
    "operator_agreement_frobenius",
    "saved_operator_matches_production",
    "constructive_gate_reconstruction",
    "state_difference_l2",
    "state_fidelity_error",
    "saved_final_state_matches_production",
    "big_endian_qubit0_leftmost",
    "big_endian_qubit3_rightmost",
    "c3x_truth_table_controls_0_1_2_target_3",
)

INDEPENDENT_METRIC_KEYS = (
    "operator_difference_frobenius",
    "state_difference_l2",
    "state_fidelity_error",
)

TEST_LOG_CHECK_KEYS = (
    "pytest_exit_code_zero",
    "pytest_tests_nonzero",
    "pytest_failures_zero",
    "pytest_errors_zero",
    "pytest_skipped_zero",
    "junit_counters_reconciled",
    "residuals",
    "independent_agreement",
)


def fail(message: str, errors: list[str]) -> None:
    """Record a validation failure without stopping subsequent checks."""
    errors.append(message)


def is_valid_numeric(value: object) -> bool:
    """Accept finite int/float values, but never bool."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def is_valid_integer(value: object) -> bool:
    """Accept integers but reject bool, which is an int subclass in Python."""
    return isinstance(value, int) and not isinstance(value, bool)


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


def rebuild_eligible_inventory_independently(root: Path) -> set[str]:
    """Rebuild the eligible file set without importing the manifest producer.

    This deliberately uses os.walk rather than compute_checksums.inventory_files,
    while independently applying the repository inventory inclusion/exclusion
    rules to P1 and .github/workflows.
    """
    excluded_names = {"MANIFEST.txt", "SHA256SUMS.txt"}
    excluded_directories = {"__pycache__", ".pytest_cache", ".mypy_cache"}
    scan_roots = (root / "P1", root / ".github" / "workflows")
    eligible: set[str] = set()

    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        if scan_root.is_symlink() or not scan_root.is_dir():
            continue

        for current, directory_names, file_names in os.walk(
            scan_root,
            topdown=True,
            followlinks=False,
        ):
            current_path = Path(current)
            directory_names[:] = [
                name
                for name in directory_names
                if name not in excluded_directories
                and not (current_path / name).is_symlink()
            ]

            for name in file_names:
                candidate = current_path / name
                if name in excluded_names or candidate.suffix == ".pyc":
                    continue
                if candidate.is_symlink() or not candidate.is_file():
                    continue
                eligible.add(candidate.relative_to(root).as_posix())

    return eligible


def validate_inventory(errors: list[str]):
    """Validate both inventories against the independently rebuilt file set."""
    manifest_path = P1 / "MANIFEST.txt"
    checksum_path = P1 / "SHA256SUMS.txt"

    manifest: list[str] = []
    checksum_map: dict[str, str] = {}

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

    for rel in sorted(MANIFEST_REQUIRED):
        if rel not in manifest:
            fail(f"required file absent from manifest: {rel}", errors)

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

    for rel in INVENTORY_FILES:
        if rel in checksum_map:
            fail(
                f"self-referential inventory file listed in SHA-256 inventory: {rel}",
                errors,
            )

    manifest_paths = set(manifest)
    checksum_paths = set(checksum_map)

    if manifest_paths != checksum_paths:
        missing_from_checksums = sorted(manifest_paths - checksum_paths)
        missing_from_manifest = sorted(checksum_paths - manifest_paths)
        fail(
            "manifest and checksum path sets differ "
            f"(missing from checksums: {missing_from_checksums}; "
            f"missing from manifest: {missing_from_manifest})",
            errors,
        )

    try:
        eligible_files = rebuild_eligible_inventory_independently(ROOT)
    except Exception as exc:
        fail(
            "independent inventory reconstruction failed: "
            f"{type(exc).__name__}: {exc}",
            errors,
        )
        eligible_files = set()

    if eligible_files != manifest_paths:
        missing_from_manifest = sorted(eligible_files - manifest_paths)
        extra_in_manifest = sorted(manifest_paths - eligible_files)
        fail(
            "manifest does not match independently reconstructed inventory "
            f"(missing: {missing_from_manifest}; "
            f"extra: {extra_in_manifest})",
            errors,
        )

    if eligible_files != checksum_paths:
        missing_from_checksums = sorted(eligible_files - checksum_paths)
        extra_in_checksums = sorted(checksum_paths - eligible_files)
        fail(
            "SHA-256 inventory does not match independently reconstructed inventory "
            f"(missing: {missing_from_checksums}; "
            f"extra: {extra_in_checksums})",
            errors,
        )

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
    if gate_sequence != GATE_SEQUENCE:
        fail("gate sequence mismatch with canonical GATE_SEQUENCE", errors)

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


def validate_residual_report(
    residuals: dict[str, Any],
    errors: list[str],
) -> None:
    if residuals.get("status") != "PASS":
        fail("residual report status is not PASS", errors)

    if residuals.get("all_checks_pass") is not True:
        fail("residual report all_checks_pass is not true", errors)

    tolerance = residuals.get("numerical_tolerance")
    if (
        not is_valid_numeric(tolerance)
        or tolerance != NUMERICAL_TOLERANCE
    ):
        fail("residual tolerance invalid or mismatched", errors)

    finite_checks = residuals.get("finite_checks")
    if not isinstance(finite_checks, dict):
        fail("residual finite_checks must be an object", errors)
        finite_checks = {}
    elif set(finite_checks) != set(FINITE_CHECK_KEYS):
        fail("residual finite_checks schema mismatch", errors)

    for key in FINITE_CHECK_KEYS:
        value = finite_checks.get(key)
        if value is not True:
            fail(f"residual finite check missing or false: {key}", errors)

    for key in RESIDUAL_KEYS:
        value = residuals.get(key)
        if not is_valid_numeric(value):
            fail(f"residual metric invalid or non-finite: {key}", errors)
        elif value < 0 or value > NUMERICAL_TOLERANCE:
            fail(f"residual metric outside tolerance: {key}", errors)

    checks = residuals.get("checks")
    if not isinstance(checks, dict) or not checks:
        fail("residual report checks missing or invalid", errors)
    else:
        expected_keys = set(FINITE_CHECK_KEYS) | set(RESIDUAL_KEYS)
        if set(checks) != expected_keys:
            fail("residual report checks schema mismatch", errors)

        for key, value in checks.items():
            if value is not True:
                fail(f"residual report check missing, invalid, or false: {key}", errors)


def validate_independent_report(
    independent: dict[str, Any],
    errors: list[str],
) -> None:
    if independent.get("status") != "PASS":
        fail("independent agreement is not PASS", errors)

    if independent.get("all_checks_pass") is not True:
        fail("independent agreement all_checks_pass is not true", errors)

    tolerance = independent.get("numerical_tolerance")
    if (
        not is_valid_numeric(tolerance)
        or tolerance != NUMERICAL_TOLERANCE
    ):
        fail("independent tolerance invalid or mismatched", errors)

    checks = independent.get("checks")
    if not isinstance(checks, dict):
        fail("independent agreement checks missing or invalid", errors)
    else:
        if set(checks) != set(INDEPENDENT_CHECK_KEYS):
            fail("independent agreement checks schema mismatch", errors)
        for key, value in checks.items():
            if value is not True:
                fail(
                    f"independent agreement check missing, invalid, or false: {key}",
                    errors,
                )

    for key in INDEPENDENT_METRIC_KEYS:
        value = independent.get(key)
        if not is_valid_numeric(value):
            fail(f"independent metric invalid or non-finite: {key}", errors)
        elif value < 0 or value > NUMERICAL_TOLERANCE:
            fail(
                f"independent metric outside tolerance: {key}",
                errors,
            )


def validate_test_log(
    test_log: dict[str, Any],
    errors: list[str],
) -> None:
    if test_log.get("verdict") != "P1_PENDING_PACKAGE_INTEGRITY":
        fail(
            "test log is rejected or not pending package integrity",
            errors,
        )

    tolerance = test_log.get("numerical_tolerance")
    if (
        not is_valid_numeric(tolerance)
        or tolerance != NUMERICAL_TOLERANCE
    ):
        fail("test-log numerical tolerance invalid or mismatched", errors)

    checks = test_log.get("checks")
    if not isinstance(checks, dict) or not checks:
        fail("test-log checks missing or invalid", errors)
    else:
        missing_checks = sorted(set(TEST_LOG_CHECK_KEYS) - set(checks))
        if missing_checks:
            fail(
                "test-log required checks missing: "
                + ", ".join(missing_checks),
                errors,
            )

        for key, value in checks.items():
            if value is not True:
                fail(
                    f"one or more aggregated test-log checks failed: {key}",
                    errors,
                )

    pytest = test_log.get("pytest")
    if not isinstance(pytest, dict):
        fail("pytest section missing or invalid", errors)
        return

    exit_code = pytest.get("exit_code")
    tests = pytest.get("tests")
    failures = pytest.get("failures")
    test_errors = pytest.get("errors")
    skipped = pytest.get("skipped")

    if not is_valid_integer(exit_code) or exit_code != 0:
        fail("pytest exit code invalid or nonzero", errors)

    if not is_valid_integer(tests) or tests <= 0:
        fail("pytest test count invalid or zero", errors)

    for key, value in (
        ("failures", failures),
        ("errors", test_errors),
        ("skipped", skipped),
    ):
        if not is_valid_integer(value) or value != 0:
            fail(f"pytest {key} must be integer zero", errors)

    test_cases = pytest.get("test_cases")
    if (
        not isinstance(test_cases, list)
        or not all(isinstance(item, str) for item in test_cases)
    ):
        fail("pytest test_cases must be a list of strings", errors)
        observed_cases: set[str] = set()
    else:
        observed_cases = set(test_cases)

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
        "test_inventory_is_sorted_and_contains_no_duplicates",
        "test_inventory_excludes_self_referential_files",
        "test_inventory_excludes_bytecode_and_cache_directories",
        "test_preflight_source_modules_and_report_generator_exist",
        "test_initial_state_is_the_canonical_zero_basis_vector",
    }

    observed_names = {
        entry.rsplit("::", 1)[-1]
        for entry in observed_cases
    }

    missing_cases = sorted(required_case_suffixes - observed_names)
    if missing_cases:
        fail(
            "required acceptance test cases missing: "
            + ", ".join(missing_cases),
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
            validate_residual_report(residuals, errors)

    if independent is not None:
        if not isinstance(independent, dict):
            fail(
                "independent agreement report root must be a JSON object",
                errors,
            )
        else:
            validate_independent_report(independent, errors)

    if test_log is not None:
        if not isinstance(test_log, dict):
            fail("test log root must be a JSON object", errors)
        else:
            validate_test_log(test_log, errors)


def main() -> None:
    errors: list[str] = []

    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            fail(f"missing required file: {rel}", errors)

    manifest, checksum_map = validate_inventory(errors)

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
