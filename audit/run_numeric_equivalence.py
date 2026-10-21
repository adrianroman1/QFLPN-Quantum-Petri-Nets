#!/usr/bin/env python3
"""
P2-BENCH-CONFIG-01
Independent Numeric Equivalence Audit.

Exit codes:
    0 = PASS
    1 = FAIL
    2 = NOT VERIFIED

The audit compares:
    1. Historical Git-blob production operations.
    2. Current migrated production operations.
    3. An independent NumPy mathematical reference.

PennyLane execution is obtained from the actual production QNode
exposed by benchmark_runner.build_operations().

The audit also validates the four configured benchmark artifacts:
    JSON
    CSV
    Markdown
    Environment

No benchmark artifacts are generated or silently substituted here.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import traceback

from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np


# ============================================================
# CONSTANTS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

P2_ROOT = ROOT / "P2"
BENCHMARK_DIR = P2_ROOT / "benchmarks"
CODE_DIR = P2_ROOT / "code"

RUNNER_PATH = BENCHMARK_DIR / "benchmark_runner.py"
CONTRACT_PATH = BENCHMARK_DIR / "benchmark_contract.py"
DEFAULT_CONFIG = BENCHMARK_DIR / "benchmark_config.json"

REPORT_PATH = ROOT / "audit" / "numeric_equivalence.json"

BASELINE_RUNNER_BLOB = (
    "03a63fec41a099944017d9c95d53c3b8656359a3"
)

REQUIRED_OPERATIONS = (
    "rotation_operator",
    "c3x_operator",
    "transition_operator",
    "state_evolution",
    "density_matrix",
    "reduced_density_q4",
    "reduced_density_q123",
    "pennylane_execution",
)

REQUIRED_ARTIFACTS = (
    "json",
    "csv",
    "markdown",
    "environment",
)

REQUIRED_TOLERANCE = 1e-12

VALID_STATUSES = {
    "PASS",
    "FAIL",
    "NOT VERIFIED",
}

CSV_COLUMNS = [
    "operation",
    "warmups",
    "repetitions",
    "minimum_ns",
    "median_ns",
    "mean_ns",
    "maximum_ns",
    "standard_deviation_ns",
    "operations_per_second",
    "numerical_error",
    "numerical_tolerance",
    "passed",
]


# ============================================================
# PURE STATUS FUNCTIONS
# ============================================================

def aggregate_operation_statuses(
    operations: dict[str, dict],
) -> str:
    """
    Aggregate operation statuses.

    Priority:
        FAIL > NOT VERIFIED > PASS

    An empty or malformed collection is NOT VERIFIED.
    """

    if not isinstance(operations, dict) or not operations:
        return "NOT VERIFIED"

    statuses = []

    for name, payload in operations.items():

        if not isinstance(payload, dict):
            return "NOT VERIFIED"

        status = payload.get("status")

        if status not in VALID_STATUSES:
            return "NOT VERIFIED"

        statuses.append(status)

    if "FAIL" in statuses:
        return "FAIL"

    if "NOT VERIFIED" in statuses:
        return "NOT VERIFIED"

    return "PASS"


def aggregate_artifact_statuses(
    artifacts: dict[str, dict],
) -> str:

    if not isinstance(artifacts, dict):
        return "NOT VERIFIED"

    if set(artifacts) != set(REQUIRED_ARTIFACTS):
        return "NOT VERIFIED"

    statuses = []

    for name in REQUIRED_ARTIFACTS:

        payload = artifacts[name]

        if not isinstance(payload, dict):
            return "NOT VERIFIED"

        status = payload.get("status")

        if status not in VALID_STATUSES:
            return "NOT VERIFIED"

        statuses.append(status)

    if "FAIL" in statuses:
        return "FAIL"

    if "NOT VERIFIED" in statuses:
        return "NOT VERIFIED"

    return "PASS"


# ============================================================
# REPORT VALIDATION
# ============================================================

def _finite_nonnegative_number(value: Any) -> bool:

    if isinstance(value, bool):
        return False

    if not isinstance(value, (int, float)):
        return False

    return math.isfinite(float(value)) and value >= 0


def validate_numeric_report(
    report: dict,
) -> dict:
    """
    Validate report structure and numeric consistency.

    Missing evidence:
        NOT VERIFIED

    Demonstrated contradiction:
        FAIL

    Complete and coherent report:
        PASS
    """

    if not isinstance(report, dict):

        return {
            "status": "NOT VERIFIED",
            "errors": ["Report root must be a dictionary."],
        }

    required_fields = {
        "audit",
        "audit_id",
        "timestamp_utc",
        "status",
        "tolerance",
        "baseline",
        "migrated",
        "artifacts",
        "operations",
        "issues",
    }

    missing = required_fields - set(report)

    if missing:

        return {
            "status": "NOT VERIFIED",
            "errors": [
                f"Missing report field: {name}"
                for name in sorted(missing)
            ],
        }

    errors = []
    incomplete = []

    if report["audit"] != "numeric_equivalence":
        errors.append("Invalid audit identifier.")

    if report["audit_id"] != "P2-BENCH-CONFIG-01":
        errors.append("Invalid audit_id.")

    if report["status"] not in VALID_STATUSES:
        errors.append("Invalid global report status.")

    tolerance = report["tolerance"]

    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not math.isfinite(float(tolerance))
        or float(tolerance) != REQUIRED_TOLERANCE
    ):
        errors.append("Invalid or unsupported numerical tolerance.")

    for name in ("baseline", "migrated"):

        if not isinstance(report[name], dict):
            incomplete.append(f"{name} metadata is missing.")

    operations = report["operations"]

    if not isinstance(operations, dict):

        incomplete.append("Operations must be a dictionary.")

    else:

        missing_operations = (
            set(REQUIRED_OPERATIONS) - set(operations)
        )

        unexpected_operations = (
            set(operations) - set(REQUIRED_OPERATIONS)
        )

        for name in sorted(missing_operations):
            incomplete.append(f"Missing operation: {name}")

        for name in sorted(unexpected_operations):
            errors.append(f"Unexpected operation: {name}")

        for name in REQUIRED_OPERATIONS:

            if name not in operations:
                continue

            payload = operations[name]

            if not isinstance(payload, dict):
                incomplete.append(
                    f"{name}: operation payload is missing."
                )
                continue

            operation_status = payload.get("status")

            if operation_status not in VALID_STATUSES:
                errors.append(
                    f"{name}: invalid operation status."
                )
                continue

            comparisons = (
                "baseline_vs_reference",
                "migrated_vs_reference",
                "baseline_vs_migrated",
            )

            for comparison_name in comparisons:

                if comparison_name not in payload:

                    incomplete.append(
                        f"{name}: missing {comparison_name}."
                    )
                    continue

                comparison = payload[comparison_name]

                if not isinstance(comparison, dict):

                    incomplete.append(
                        f"{name}: invalid {comparison_name}."
                    )
                    continue

                comparison_status = comparison.get("status")

                if comparison_status not in VALID_STATUSES:

                    errors.append(
                        f"{name}/{comparison_name}: invalid status."
                    )
                    continue

                if "shape_match" not in comparison:

                    incomplete.append(
                        f"{name}/{comparison_name}: missing shape_match."
                    )
                    continue

                if comparison["shape_match"] is False:

                    if comparison_status != "FAIL":
                        errors.append(
                            f"{name}/{comparison_name}: shape mismatch "
                            "must be FAIL."
                        )

                elif comparison["shape_match"] is not True:

                    errors.append(
                        f"{name}/{comparison_name}: invalid shape_match."
                    )

                error_fields = (
                    "frobenius_norm_error",
                    "max_absolute_error",
                )

                for field in error_fields:

                    if field not in comparison:

                        incomplete.append(
                            f"{name}/{comparison_name}: missing {field}."
                        )
                        continue

                    value = comparison[field]

                    if value is None:

                        if comparison_status == "PASS":

                            errors.append(
                                f"{name}/{comparison_name}: "
                                f"PASS with missing {field}."
                            )

                        continue

                    if not _finite_nonnegative_number(value):

                        errors.append(
                            f"{name}/{comparison_name}: "
                            f"invalid numeric value for {field}."
                        )
                        continue

                comparison_tolerance = comparison.get("tolerance")

                if (
                    isinstance(comparison_tolerance, bool)
                    or not isinstance(comparison_tolerance, (int, float))
                    or not math.isfinite(float(comparison_tolerance))
                ):

                    incomplete.append(
                        f"{name}/{comparison_name}: invalid tolerance."
                    )
                    continue

                if float(comparison_tolerance) != REQUIRED_TOLERANCE:

                    errors.append(
                        f"{name}/{comparison_name}: "
                        "comparison tolerance mismatch."
                    )

                max_error = comparison.get("max_absolute_error")
                frobenius_error = comparison.get("frobenius_norm_error")

                if (
                    _finite_nonnegative_number(max_error)
                    and _finite_nonnegative_number(frobenius_error)
                ):

                    exceeded = (
                        max_error > REQUIRED_TOLERANCE
                        or frobenius_error > REQUIRED_TOLERANCE
                    )

                    if exceeded and comparison_status == "PASS":

                        errors.append(
                            f"{name}/{comparison_name}: "
                            "PASS despite tolerance violation."
                        )

                    if not exceeded and comparison_status == "FAIL":

                        # FAIL may also represent a demonstrated
                        # shape mismatch or another explicit defect.
                        if comparison.get("shape_match") is True:

                            errors.append(
                                f"{name}/{comparison_name}: "
                                "FAIL without a demonstrated numeric mismatch."
                            )

            comparison_statuses = []

            for comparison_name in comparisons:

                comparison = payload.get(comparison_name)

                if isinstance(comparison, dict):

                    status = comparison.get("status")

                    if status in VALID_STATUSES:
                        comparison_statuses.append(status)

            if len(comparison_statuses) == 3:

                expected_status = aggregate_operation_statuses({
                    str(index): {"status": status}
                    for index, status in enumerate(
                        comparison_statuses
                    )
                })

                if payload["status"] != expected_status:

                    errors.append(
                        f"{name}: operation status contradicts "
                        "comparison statuses."
                    )

    artifacts = report["artifacts"]

    if not isinstance(artifacts, dict):

        incomplete.append("Artifact metadata is missing.")

    else:

        for name in REQUIRED_ARTIFACTS:

            if name not in artifacts:

                incomplete.append(
                    f"Missing artifact: {name}"
                )
                continue

            payload = artifacts[name]

            if not isinstance(payload, dict):

                incomplete.append(
                    f"Invalid artifact payload: {name}"
                )
                continue

            if payload.get("status") not in VALID_STATUSES:

                incomplete.append(
                    f"Invalid artifact status: {name}"
                )

    if not isinstance(report["issues"], list):
        errors.append("Report issues must be a list.")

    if errors:

        return {
            "status": "FAIL",
            "errors": errors + incomplete,
        }

    if incomplete:

        return {
            "status": "NOT VERIFIED",
            "errors": incomplete,
        }

    operation_status = aggregate_operation_statuses(
        operations
    )

    artifact_status = aggregate_artifact_statuses(
        artifacts
    )

    expected_global = aggregate_operation_statuses({
        "operations": {"status": operation_status},
        "artifacts": {"status": artifact_status},
    })

    if report["status"] != expected_global:

        return {
            "status": "FAIL",
            "errors": [
                "Global report status contradicts "
                "operation/artifact statuses."
            ],
        }

    return {
        "status": "PASS",
        "errors": [],
    }


# ============================================================
# HASH AND GIT HELPERS
# ============================================================

def utc_now() -> str:

    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:

    return hashlib.sha256(data).hexdigest()


def git_blob(blob_sha: str) -> bytes:

    object_type = subprocess.run(
        ["git", "cat-file", "-t", blob_sha],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    if object_type != "blob":

        raise ValueError(
            f"Baseline object {blob_sha} is not a Git blob."
        )

    return subprocess.run(
        ["git", "cat-file", "blob", blob_sha],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout


# ============================================================
# MODULE LOADING
# ============================================================

def load_python_module(
    path: Path,
    module_name: str,
) -> ModuleType:

    if not path.is_file():

        raise FileNotFoundError(
            f"Python source does not exist: {path}"
        )

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:

        raise ImportError(
            f"Cannot load Python module: {path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[module_name] = module

    spec.loader.exec_module(module)

    return module


def load_runner_from_source(
    source: bytes,
    module_name: str,
    temporary_directory: Path,
) -> ModuleType:

    runner_directory = temporary_directory / module_name

    runner_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    runner_file = runner_directory / "benchmark_runner.py"

    runner_file.write_bytes(source)

    ast.parse(
        source.decode("utf-8"),
        filename=str(runner_file),
    )

    for directory in (BENCHMARK_DIR, CODE_DIR):

        if str(directory) not in sys.path:

            sys.path.insert(0, str(directory))

    return load_python_module(
        runner_file,
        module_name,
    )


# ============================================================
# CONTRACT
# ============================================================

def load_contract(config_path: Path):

    if not CONTRACT_PATH.is_file():

        raise FileNotFoundError(
            f"Benchmark contract is missing: {CONTRACT_PATH}"
        )

    if str(BENCHMARK_DIR) not in sys.path:

        sys.path.insert(0, str(BENCHMARK_DIR))

    contract_module = load_python_module(
        CONTRACT_PATH,
        "p2_numeric_audit_contract",
    )

    return contract_module.load_benchmark_contract(
        config_path
    )


def validate_numeric_configuration(
    contract,
) -> tuple[tuple[float, ...], float]:

    config = contract.config

    activations = config.get("activation_vector")

    if not isinstance(activations, list) or len(activations) != 4:

        raise ValueError(
            "Exactly four activations are required."
        )

    normalized = []

    for index, value in enumerate(activations):

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or not 0.0 <= float(value) <= 1.0
        ):

            raise ValueError(
                f"Invalid activation at index {index}."
            )

        normalized.append(float(value))

    tolerance = config.get("numerical_tolerance")

    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not math.isfinite(float(tolerance))
        or float(tolerance) != REQUIRED_TOLERANCE
    ):

        raise ValueError(
            "Configuration must use tolerance 1e-12."
        )

    if tuple(config.get("operations", ())) != REQUIRED_OPERATIONS:

        raise ValueError(
            "Configuration operation list is inconsistent."
        )

    return tuple(normalized), float(tolerance)


# ============================================================
# INDEPENDENT NUMPY REFERENCE
# ============================================================

def reference_rotation_operator(
    activations: tuple[float, ...],
) -> np.ndarray:

    result = np.array(
        [[1.0 + 0.0j]],
        dtype=np.complex128,
    )

    for activation in activations:

        theta = 2.0 * np.arcsin(np.sqrt(activation))

        cosine = np.cos(theta / 2.0)
        sine = np.sin(theta / 2.0)

        ry = np.array(
            [
                [cosine, -sine],
                [sine, cosine],
            ],
            dtype=np.complex128,
        )

        result = np.kron(result, ry)

    return result


def reference_c3x_operator() -> np.ndarray:

    result = np.eye(16, dtype=np.complex128)

    result[14, 14] = 0.0
    result[15, 15] = 0.0

    result[14, 15] = 1.0
    result[15, 14] = 1.0

    return result


def reference_transition_operator(
    activations: tuple[float, ...],
) -> np.ndarray:

    return (
        reference_c3x_operator()
        @ reference_rotation_operator(activations)
    )


def reference_state_evolution(
    activations: tuple[float, ...],
) -> np.ndarray:

    initial = np.zeros(16, dtype=np.complex128)
    initial[0] = 1.0

    return (
        reference_transition_operator(activations)
        @ initial
    )


def reference_density_matrix(
    state: np.ndarray,
) -> np.ndarray:

    vector = np.asarray(state, dtype=np.complex128)

    return np.outer(vector, vector.conj())


def reference_reduced_density_matrices(
    state: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:

    tensor = np.asarray(
        state,
        dtype=np.complex128,
    ).reshape(8, 2)

    rho_q4 = np.einsum(
        "ai,aj->ij",
        tensor.conj(),
        tensor,
    )

    rho_q123 = np.einsum(
        "ai,bi->ab",
        tensor,
        tensor.conj(),
    )

    return rho_q4, rho_q123


def build_independent_reference(
    activations: tuple[float, ...],
) -> dict[str, np.ndarray]:

    rotation = reference_rotation_operator(activations)
    c3x = reference_c3x_operator()
    transition = c3x @ rotation

    state = reference_state_evolution(activations)

    density = reference_density_matrix(state)

    rho_q4, rho_q123 = (
        reference_reduced_density_matrices(state)
    )

    return {
        "rotation_operator": rotation,
        "c3x_operator": c3x,
        "transition_operator": transition,
        "state_evolution": state,
        "density_matrix": density,
        "reduced_density_q4": rho_q4,
        "reduced_density_q123": rho_q123,

        # This is the independent mathematical oracle.
        # It is NOT claimed to be a PennyLane execution.
        "pennylane_execution": state,
    }


# ============================================================
# PRODUCTION OPERATIONS
# ============================================================

def extract_production_operations(
    runner: ModuleType,
    activations: tuple[float, ...],
    expected: dict[str, np.ndarray],
) -> tuple[dict[str, Any], np.ndarray]:

    if not hasattr(runner, "build_operations"):

        raise AttributeError(
            "Runner does not expose build_operations()."
        )

    if tuple(runner.EXPECTED_OPERATIONS) != REQUIRED_OPERATIONS:

        raise ValueError(
            "Runner operation contract mismatch."
        )

    operations, pennylane_state = runner.build_operations(
        activations,
        expected,
    )

    extracted = {}

    for item in operations:

        if not isinstance(item, tuple) or len(item) != 4:

            raise TypeError(
                "Invalid production operation tuple."
            )

        name, production_function, _, _ = item

        if name in extracted:

            raise ValueError(
                f"Duplicate operation: {name}"
            )

        if not callable(production_function):

            raise TypeError(
                f"Operation {name} is not callable."
            )

        extracted[name] = production_function

    if set(extracted) != set(REQUIRED_OPERATIONS):

        raise ValueError(
            "Runner did not expose exactly the required operations."
        )

    return (
        extracted,
        validate_array(
            pennylane_state,
            "pennylane_state",
        ),
    )


# ============================================================
# NUMERIC COMPARISON
# ============================================================

def validate_array(
    value: Any,
    operation: str,
) -> np.ndarray:

    array = np.asarray(value)

    if array.dtype.kind not in {"i", "u", "f", "c"}:

        raise TypeError(
            f"{operation}: non-numeric output."
        )

    if not np.all(np.isfinite(array)):

        raise ValueError(
            f"{operation}: NaN or infinity detected."
        )

    return array


def compare_arrays(
    actual: Any,
    expected: Any,
    tolerance: float,
) -> dict:

    actual_array = validate_array(actual, "actual")
    expected_array = validate_array(expected, "expected")

    if actual_array.shape != expected_array.shape:

        return {
            "status": "FAIL",
            "shape_match": False,
            "actual_shape": list(actual_array.shape),
            "expected_shape": list(expected_array.shape),
            "frobenius_norm_error": None,
            "max_absolute_error": None,
            "tolerance": tolerance,
        }

    difference = (
        actual_array.astype(np.complex128, copy=False)
        - expected_array.astype(np.complex128, copy=False)
    )

    frobenius_error = float(np.linalg.norm(difference))

    max_error = float(np.max(np.abs(difference)))

    passed = (
        math.isfinite(frobenius_error)
        and math.isfinite(max_error)
        and frobenius_error <= tolerance
        and max_error <= tolerance
    )

    return {
        "status": "PASS" if passed else "FAIL",
        "shape_match": True,
        "actual_shape": list(actual_array.shape),
        "expected_shape": list(expected_array.shape),
        "frobenius_norm_error": frobenius_error,
        "max_absolute_error": max_error,
        "tolerance": tolerance,
    }


def evaluate_runner(
    runner: ModuleType,
    activations: tuple[float, ...],
    expected: dict[str, np.ndarray],
) -> tuple[dict[str, np.ndarray], np.ndarray]:

    functions, pennylane_state = extract_production_operations(
        runner,
        activations,
        expected,
    )

    outputs = {}

    for operation in REQUIRED_OPERATIONS:

        outputs[operation] = validate_array(
            functions[operation](),
            operation,
        )

    return outputs, pennylane_state


# ============================================================
# ARTIFACT VALIDATION
# ============================================================

def artifact_result(
    status: str,
    **metadata,
) -> dict:

    return {
        "status": status,
        **metadata,
    }


def validate_json_artifact(path: Path) -> dict:

    if not path.is_file():

        return artifact_result(
            "NOT VERIFIED",
            exists=False,
        )

    try:

        raw = path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))

    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:

        return artifact_result(
            "FAIL",
            exists=True,
            error=str(exc),
        )

    if not isinstance(parsed, dict):

        return artifact_result(
            "FAIL",
            exists=True,
            error="JSON root must be an object.",
        )

    required = {
        "schema_version",
        "benchmark_id",
        "timestamp_utc",
        "operations",
        "status",
        "environment",
    }

    missing = sorted(required - set(parsed))

    if missing:

        return artifact_result(
            "FAIL",
            exists=True,
            sha256=sha256_bytes(raw),
            keys=sorted(parsed),
            error=f"Missing JSON keys: {missing}",
        )

    if not isinstance(parsed["operations"], list):

        return artifact_result(
            "FAIL",
            exists=True,
            sha256=sha256_bytes(raw),
            keys=sorted(parsed),
            error="JSON operations must be a list.",
        )

    operation_names = [
        item.get("operation")
        for item in parsed["operations"]
        if isinstance(item, dict)
    ]

    if tuple(operation_names) != REQUIRED_OPERATIONS:

        return artifact_result(
            "FAIL",
            exists=True,
            sha256=sha256_bytes(raw),
            keys=sorted(parsed),
            error="JSON operation sequence is inconsistent.",
        )

    return artifact_result(
        "PASS",
        exists=True,
        sha256=sha256_bytes(raw),
        keys=sorted(parsed),
    )


def validate_csv_artifact(path: Path) -> dict:

    if not path.is_file():

        return artifact_result(
            "NOT VERIFIED",
            exists=False,
        )

    try:

        with path.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as stream:

            reader = csv.DictReader(stream)

            columns = reader.fieldnames

            if columns != CSV_COLUMNS:

                return artifact_result(
                    "FAIL",
                    exists=True,
                    columns=columns or [],
                    row_count=0,
                    error="CSV columns or their order are incorrect.",
                )

            rows = list(reader)

    except (OSError, UnicodeDecodeError, csv.Error) as exc:

        return artifact_result(
            "FAIL",
            exists=True,
            error=str(exc),
        )

    names = [row.get("operation") for row in rows]

    if names != list(REQUIRED_OPERATIONS):

        return artifact_result(
            "FAIL",
            exists=True,
            columns=columns,
            row_count=len(rows),
            error="CSV operation rows are incomplete or unordered.",
        )

    return artifact_result(
        "PASS",
        exists=True,
        columns=columns,
        row_count=len(rows),
    )


def validate_markdown_artifact(
    path: Path,
    artifacts: dict[str, str],
) -> dict:

    if not path.is_file():

        return artifact_result(
            "NOT VERIFIED",
            exists=False,
        )

    try:

        content = path.read_text(encoding="utf-8")

    except (OSError, UnicodeDecodeError) as exc:

        return artifact_result(
            "FAIL",
            exists=True,
            error=str(exc),
        )

    generated_evidence_present = (
        "## Generated evidence" in content
    )

    missing_names = [
        filename
        for filename in artifacts.values()
        if filename not in content
    ]

    if not generated_evidence_present or missing_names:

        return artifact_result(
            "FAIL",
            exists=True,
            generated_evidence_present=generated_evidence_present,
            missing_artifacts=missing_names,
        )

    return artifact_result(
        "PASS",
        exists=True,
        generated_evidence_present=True,
        missing_artifacts=[],
    )


def validate_environment_artifact(path: Path) -> dict:

    if not path.is_file():

        return artifact_result(
            "NOT VERIFIED",
            exists=False,
        )

    try:

        content = path.read_text(encoding="utf-8")

    except (OSError, UnicodeDecodeError) as exc:

        return artifact_result(
            "FAIL",
            exists=True,
            error=str(exc),
        )

    if not content.strip():

        return artifact_result(
            "FAIL",
            exists=True,
            format="text",
            size_bytes=0,
            error="Environment artifact is empty.",
        )

    lines = content.splitlines()

    if not lines or lines[0] != "P2 BENCHMARK ENVIRONMENT":

        return artifact_result(
            "FAIL",
            exists=True,
            format="text",
            size_bytes=len(content.encode("utf-8")),
            error="Invalid environment artifact header.",
        )

    fields = [
        line.partition(":")[0]
        for line in lines
        if ":" in line
    ]

    if not fields:

        return artifact_result(
            "FAIL",
            exists=True,
            format="text",
            size_bytes=len(content.encode("utf-8")),
            error="No environment fields found.",
        )

    return artifact_result(
        "PASS",
        exists=True,
        format="text",
        size_bytes=len(content.encode("utf-8")),
        field_count=len(fields),
    )


def validate_artifacts(contract) -> dict:

    return {
        "json": validate_json_artifact(
            Path(contract.json_path)
        ),
        "csv": validate_csv_artifact(
            Path(contract.csv_path)
        ),
        "markdown": validate_markdown_artifact(
            Path(contract.markdown_path),
            contract.artifacts,
        ),
        "environment": validate_environment_artifact(
            Path(contract.environment_path)
        ),
    }


# ============================================================
# MAIN AUDIT
# ============================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "P2-BENCH-CONFIG-01 numeric equivalence audit."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    args = parser.parse_args()

    report = {
        "audit": "numeric_equivalence",
        "audit_id": "P2-BENCH-CONFIG-01",
        "timestamp_utc": utc_now(),
        "status": "NOT VERIFIED",
        "tolerance": REQUIRED_TOLERANCE,
        "baseline": {
            "blob": BASELINE_RUNNER_BLOB,
            "sha256": None,
        },
        "migrated": {
            "path": str(RUNNER_PATH),
            "sha256": None,
        },
        "artifacts": {
            name: {
                "status": "NOT VERIFIED",
                "exists": False,
            }
            for name in REQUIRED_ARTIFACTS
        },
        "operations": {},
        "issues": [],
    }

    try:

        if not RUNNER_PATH.is_file():

            raise FileNotFoundError(
                f"Migrated runner missing: {RUNNER_PATH}"
            )

        contract = load_contract(args.config)

        activations, tolerance = validate_numeric_configuration(
            contract
        )

        baseline_source = git_blob(
            BASELINE_RUNNER_BLOB
        )

        migrated_source = RUNNER_PATH.read_bytes()

        report["baseline"]["sha256"] = sha256_bytes(
            baseline_source
        )

        report["migrated"]["sha256"] = sha256_bytes(
            migrated_source
        )

        report["baseline"]["matches_migrated_blob"] = (
            report["baseline"]["sha256"]
            == report["migrated"]["sha256"]
        )

        report["tolerance"] = tolerance

        report["configuration"] = {
            "activation_vector": list(activations),
            "operations": list(REQUIRED_OPERATIONS),
            "tolerance": tolerance,
            "artifact_paths": {
                name: str(path)
                for name, path in contract.artifact_paths.items()
            },
        }

        expected = build_independent_reference(
            activations
        )

        if set(expected) != set(REQUIRED_OPERATIONS):

            raise ValueError(
                "Independent reference operation set mismatch."
            )

        with tempfile.TemporaryDirectory(
            prefix="p2_numeric_equivalence_"
        ) as temporary_name:

            temporary_directory = Path(temporary_name)

            baseline_runner = load_runner_from_source(
                baseline_source,
                "p2_numeric_baseline",
                temporary_directory,
            )

            migrated_runner = load_runner_from_source(
                migrated_source,
                "p2_numeric_migrated",
                temporary_directory,
            )

            baseline_outputs, baseline_pl_state = evaluate_runner(
                baseline_runner,
                activations,
                expected,
            )

            migrated_outputs, migrated_pl_state = evaluate_runner(
                migrated_runner,
                activations,
                expected,
            )

        for operation in REQUIRED_OPERATIONS:

            baseline_value = baseline_outputs[operation]
            migrated_value = migrated_outputs[operation]

            if operation == "pennylane_execution":

                # Confirm that the separately returned QNode state
                # agrees with the actual operation callable output.
                baseline_qnode_check = compare_arrays(
                    baseline_pl_state,
                    baseline_value,
                    tolerance,
                )

                migrated_qnode_check = compare_arrays(
                    migrated_pl_state,
                    migrated_value,
                    tolerance,
                )

                report.setdefault(
                    "pennylane_execution_checks",
                    {},
                )

                report["pennylane_execution_checks"] = {
                    "baseline_qnode_vs_callable": baseline_qnode_check,
                    "migrated_qnode_vs_callable": migrated_qnode_check,
                    "baseline_qnode_vs_reference": compare_arrays(
                        baseline_pl_state,
                        expected["state_evolution"],
                        tolerance,
                    ),
                    "migrated_qnode_vs_reference": compare_arrays(
                        migrated_pl_state,
                        expected["state_evolution"],
                        tolerance,
                    ),
                }

            baseline_vs_reference = compare_arrays(
                baseline_value,
                expected[operation],
                tolerance,
            )

            migrated_vs_reference = compare_arrays(
                migrated_value,
                expected[operation],
                tolerance,
            )

            baseline_vs_migrated = compare_arrays(
                baseline_value,
                migrated_value,
                tolerance,
            )

            comparisons = (
                baseline_vs_reference,
                migrated_vs_reference,
                baseline_vs_migrated,
            )

            operation_status = aggregate_operation_statuses({
                str(index): {
                    "status": item["status"]
                }
                for index, item in enumerate(comparisons)
            })

            report["operations"][operation] = {
                "status": operation_status,
                "baseline_vs_reference": baseline_vs_reference,
                "migrated_vs_reference": migrated_vs_reference,
                "baseline_vs_migrated": baseline_vs_migrated,
            }

        report["execution"] = {
            "baseline_runner_executed": True,
            "migrated_runner_executed": True,
            "independent_numpy_reference_executed": True,
            "pennylane_qnode_executed": True,
            "timing_comparison": False,
        }

    except Exception as exc:

        report["status"] = "NOT VERIFIED"

        report["issues"].append(
            f"{type(exc).__name__}: {exc}"
        )

        report["traceback"] = traceback.format_exc()

    # Artifact checks are independent of numerical execution.
    try:

        if "contract" in locals():

            report["artifacts"] = validate_artifacts(contract)

    except Exception as exc:

        report["issues"].append(
            f"Artifact validation: {type(exc).__name__}: {exc}"
        )

    operation_status = aggregate_operation_statuses(
        report["operations"]
    )

    artifact_status = aggregate_artifact_statuses(
        report["artifacts"]
    )

    report["status"] = aggregate_operation_statuses({
        "operations": {
            "status": operation_status
        },
        "artifacts": {
            "status": artifact_status
        },
    })

    if report["issues"] and report["status"] == "PASS":
        report["status"] = "NOT VERIFIED"

    validation = validate_numeric_report(report)

    report["report_validation"] = validation

    if validation["status"] == "FAIL":

        report["status"] = "FAIL"

        report["issues"].extend(
            validation["errors"]
        )

    elif (
        validation["status"] == "NOT VERIFIED"
        and report["status"] == "PASS"
    ):

        report["status"] = "NOT VERIFIED"

        report["issues"].extend(
            validation["errors"]
        )

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    if report["status"] == "PASS":
        return 0

    if report["status"] == "FAIL":
        return 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
