#!/usr/bin/env python3
"""
P2-BENCH-CONFIG-01
Independent Numeric Equivalence Audit.

Compares the eight production numerical operations exposed by:
- the original benchmark_runner.py Git blob;
- the current benchmark_runner.py source.

The independent mathematical reference is implemented in this file.
It does not use the runner's independent_reference() as its oracle.

Comparison:
1. baseline production output vs independent mathematical reference;
2. migrated production output vs independent mathematical reference;
3. baseline production output vs migrated production output.

Metric:
- Frobenius norm of the difference;
- maximum absolute element-wise difference.

Acceptance tolerance:
1e-12

Report:
audit/numeric_equivalence.json

This audit does not compare execution timings.
"""

from __future__ import annotations

import argparse
import ast
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


# =========================================================
# PATHS AND BASELINE
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_DIR = ROOT / "P2" / "benchmarks"

RUNNER_PATH = (
    BENCHMARK_DIR / "benchmark_runner.py"
)

CONTRACT_PATH = (
    BENCHMARK_DIR / "benchmark_contract.py"
)

DEFAULT_CONFIG = (
    BENCHMARK_DIR / "benchmark_config.json"
)

REPORT_PATH = (
    ROOT / "audit" / "numeric_equivalence.json"
)

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

REQUIRED_TOLERANCE = 1e-12


# =========================================================
# REPORT HELPERS
# =========================================================

def utc_now() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def sha256_bytes(data: bytes) -> str:

    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:

    return sha256_bytes(path.read_bytes())


def git_blob(blob_sha: str) -> bytes:
    """
    Retrieve a Git blob by its exact object ID.

    A missing baseline is NOT VERIFIED, never silently replaced
    by the current source.
    """

    object_type = subprocess.run(
        [
            "git",
            "cat-file",
            "-t",
            blob_sha,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    if object_type != "blob":

        raise ValueError(
            f"Baseline object {blob_sha} is not a Git blob"
        )

    return subprocess.run(
        [
            "git",
            "cat-file",
            "blob",
            blob_sha,
        ],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout


def write_report(report: dict) -> None:

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


# =========================================================
# MODULE LOADING
# =========================================================

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

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[module_name] = module

    spec.loader.exec_module(module)

    return module


def load_runner_from_source(
    source: bytes,
    module_name: str,
    temporary_directory: Path,
) -> ModuleType:
    """
    Load a runner source under an isolated module name.

    The original benchmark directory remains available for:
    benchmark_contract.py and qflpn_reference.py imports.
    """

    runner_directory = (
        temporary_directory / module_name
    )

    runner_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    runner_file = (
        runner_directory / "benchmark_runner.py"
    )

    runner_file.write_bytes(source)

    ast.parse(
        source.decode("utf-8"),
        filename=str(runner_file),
    )

    if str(BENCHMARK_DIR) not in sys.path:

        sys.path.insert(
            0,
            str(BENCHMARK_DIR),
        )

    return load_python_module(
        runner_file,
        module_name,
    )


# =========================================================
# CONTRACT AND CONFIGURATION
# =========================================================

def load_contract(
    config_path: Path,
):

    if not CONTRACT_PATH.is_file():

        raise FileNotFoundError(
            f"Benchmark contract is missing: {CONTRACT_PATH}"
        )

    if str(BENCHMARK_DIR) not in sys.path:

        sys.path.insert(
            0,
            str(BENCHMARK_DIR),
        )

    contract_module = load_python_module(
        CONTRACT_PATH,
        "p2_numeric_audit_contract",
    )

    contract = (
        contract_module.load_benchmark_contract(
            config_path
        )
    )

    return contract


def validate_numeric_configuration(
    contract,
) -> tuple[tuple[float, ...], float]:

    config = contract.config

    activations = config.get(
        "activation_vector"
    )

    if not isinstance(activations, list):

        raise ValueError(
            "Configuration activation_vector must be a list"
        )

    if len(activations) != 4:

        raise ValueError(
            "P2 numeric audit requires exactly four activations"
        )

    normalized_activations = []

    for index, value in enumerate(activations):

        if isinstance(value, bool):

            raise ValueError(
                f"Activation {index} must be numeric"
            )

        if not isinstance(value, (int, float)):

            raise ValueError(
                f"Activation {index} must be numeric"
            )

        if not math.isfinite(float(value)):

            raise ValueError(
                f"Activation {index} must be finite"
            )

        if not 0.0 <= float(value) <= 1.0:

            raise ValueError(
                f"Activation {index} must be between 0 and 1"
            )

        normalized_activations.append(
            float(value)
        )

    tolerance = config.get(
        "numerical_tolerance"
    )

    if isinstance(tolerance, bool):

        raise ValueError(
            "Numerical tolerance must be numeric"
        )

    if not isinstance(tolerance, (int, float)):

        raise ValueError(
            "Numerical tolerance must be numeric"
        )

    tolerance = float(tolerance)

    if not math.isfinite(tolerance) or tolerance <= 0:

        raise ValueError(
            "Numerical tolerance must be positive and finite"
        )

    if tolerance != REQUIRED_TOLERANCE:

        raise ValueError(
            "P2 numeric audit requires tolerance exactly "
            f"{REQUIRED_TOLERANCE!r}; configured value is "
            f"{tolerance!r}"
        )

    configured_operations = config.get(
        "operations"
    )

    if configured_operations != list(REQUIRED_OPERATIONS):

        raise ValueError(
            "Configured operation list differs from "
            "the required eight-operation P2 contract"
        )

    return (
        tuple(normalized_activations),
        tolerance,
    )


# =========================================================
# INDEPENDENT MATHEMATICAL REFERENCE
# =========================================================

def reference_rotation_operator(
    activations: tuple[float, ...],
) -> np.ndarray:

    result = np.array(
        [[1.0 + 0.0j]],
        dtype=np.complex128,
    )

    for activation in activations:

        theta = (
            2.0
            * np.arcsin(
                np.sqrt(activation)
            )
        )

        cosine = np.cos(theta / 2.0)

        sine = np.sin(theta / 2.0)

        ry = np.array(
            [
                [cosine, -sine],
                [sine, cosine],
            ],
            dtype=np.complex128,
        )

        result = np.kron(
            result,
            ry,
        )

    return result


def reference_c3x_operator() -> np.ndarray:

    result = np.eye(
        16,
        dtype=np.complex128,
    )

    result[14, 14] = 0.0
    result[15, 15] = 0.0

    result[14, 15] = 1.0
    result[15, 14] = 1.0

    return result


def reference_transition_operator(
    activations: tuple[float, ...],
) -> np.ndarray:

    rotation = reference_rotation_operator(
        activations
    )

    c3x = reference_c3x_operator()

    return c3x @ rotation


def reference_state_evolution(
    activations: tuple[float, ...],
) -> np.ndarray:

    initial = np.zeros(
        16,
        dtype=np.complex128,
    )

    initial[0] = 1.0

    transition = reference_transition_operator(
        activations
    )

    return transition @ initial


def reference_density_matrix(
    state: np.ndarray,
) -> np.ndarray:

    vector = np.asarray(
        state,
        dtype=np.complex128,
    )

    return np.outer(
        vector,
        np.conjugate(vector),
    )


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

    rotation = reference_rotation_operator(
        activations
    )

    c3x = reference_c3x_operator()

    transition = reference_transition_operator(
        activations
    )

    state = reference_state_evolution(
        activations
    )

    density = reference_density_matrix(
        state
    )

    rho_q4, rho_q123 = (
        reference_reduced_density_matrices(
            state
        )
    )

    return {
        "rotation_operator": rotation,
        "c3x_operator": c3x,
        "transition_operator": transition,
        "state_evolution": state,
        "density_matrix": density,
        "reduced_density_q4": rho_q4,
        "reduced_density_q123": rho_q123,
        "pennylane_execution": state.copy(),
    }


# =========================================================
# RUNNER OPERATION EXTRACTION
# =========================================================

def extract_production_operations(
    runner: ModuleType,
    activations: tuple[float, ...],
    expected: dict[str, np.ndarray],
) -> dict[str, Any]:
    """
    Uses the runner's actual build_operations() function.

    The second tuple element is the production callable.
    The independent callable supplied by the runner is deliberately
    not used as the numeric oracle.
    """

    required_functions = (
        "build_operations",
        "EXPECTED_OPERATIONS",
    )

    for name in required_functions:

        if not hasattr(runner, name):

            raise AttributeError(
                f"Runner does not expose required member: {name}"
            )

    runner_operations = tuple(
        runner.EXPECTED_OPERATIONS
    )

    if runner_operations != REQUIRED_OPERATIONS:

        raise ValueError(
            "Runner EXPECTED_OPERATIONS differs from the "
            "required P2 operation set"
        )

    operations, _pennylane_state = (
        runner.build_operations(
            activations,
            expected,
        )
    )

    extracted = {}

    for item in operations:

        if not isinstance(item, tuple) or len(item) != 4:

            raise TypeError(
                "build_operations() must return four-element "
                "operation tuples"
            )

        name, production_function, _independent_function, _expected = item

        if name in extracted:

            raise ValueError(
                f"Duplicate operation returned by runner: {name}"
            )

        if not callable(production_function):

            raise TypeError(
                f"Production implementation is not callable: {name}"
            )

        extracted[name] = production_function

    if set(extracted) != set(REQUIRED_OPERATIONS):

        missing = sorted(
            set(REQUIRED_OPERATIONS) - set(extracted)
        )

        unexpected = sorted(
            set(extracted) - set(REQUIRED_OPERATIONS)
        )

        raise ValueError(
            "Runner operation mismatch. "
            f"Missing={missing}; unexpected={unexpected}"
        )

    return extracted


# =========================================================
# NUMERIC COMPARISON
# =========================================================

def validate_array(
    value: Any,
    operation: str,
) -> np.ndarray:

    array = np.asarray(value)

    if array.dtype.kind not in {"i", "u", "f", "c"}:

        raise TypeError(
            f"{operation}: output is not a numeric array"
        )

    if not np.all(np.isfinite(array)):

        raise ValueError(
            f"{operation}: output contains NaN or infinity"
        )

    return array


def compare_arrays(
    actual: Any,
    expected: Any,
    tolerance: float,
) -> dict:

    actual_array = validate_array(
        actual,
        "actual",
    )

    expected_array = validate_array(
        expected,
        "expected",
    )

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
        -
        expected_array.astype(np.complex128, copy=False)
    )

    frobenius_error = float(
        np.linalg.norm(difference)
    )

    max_absolute_error = float(
        np.max(
            np.abs(difference)
        )
    )

    passed = bool(
        np.isfinite(frobenius_error)
        and np.isfinite(max_absolute_error)
        and frobenius_error <= tolerance
        and max_absolute_error <= tolerance
    )

    return {
        "status": "PASS" if passed else "FAIL",
        "shape_match": True,
        "actual_shape": list(actual_array.shape),
        "expected_shape": list(expected_array.shape),
        "frobenius_norm_error": frobenius_error,
        "max_absolute_error": max_absolute_error,
        "tolerance": tolerance,
    }


def evaluate_runner(
    runner: ModuleType,
    activations: tuple[float, ...],
    expected: dict[str, np.ndarray],
    tolerance: float,
) -> dict:

    production_operations = extract_production_operations(
        runner,
        activations,
        expected,
    )

    results = {}

    for operation in REQUIRED_OPERATIONS:

        output = production_operations[operation]()

        results[operation] = validate_array(
            output,
            operation,
        )

    return results


# =========================================================
# MAIN AUDIT
# =========================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "P2-BENCH-CONFIG-01 independent numeric equivalence audit"
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Canonical benchmark configuration JSON.",
    )

    args = parser.parse_args()

    report = {
        "audit": "numeric_equivalence",
        "audit_id": "P2-BENCH-CONFIG-01",
        "timestamp_utc": utc_now(),
        "status": "NOT VERIFIED",
        "tolerance": REQUIRED_TOLERANCE,
        "metric": {
            "primary": "frobenius_norm",
            "secondary": "maximum_absolute_element_error",
            "acceptance_rule": (
                "Both metrics must be finite and <= tolerance."
            ),
        },
        "baseline": {
            "blob": BASELINE_RUNNER_BLOB,
            "sha256": None,
        },
        "migrated": {
            "path": str(RUNNER_PATH),
            "sha256": None,
        },
        "operations": {},
        "issues": [],
    }

    try:

        if not RUNNER_PATH.is_file():

            raise FileNotFoundError(
                f"Migrated runner is missing: {RUNNER_PATH}"
            )

        if not args.config.is_file():

            raise FileNotFoundError(
                f"Configuration is missing: {args.config}"
            )

        contract = load_contract(
            args.config
        )

        activations, tolerance = (
            validate_numeric_configuration(
                contract
            )
        )

        report["tolerance"] = tolerance

        report["configuration"] = {
            "path": str(contract.config_path),
            "activation_vector": list(activations),
            "operations": list(REQUIRED_OPERATIONS),
            "tolerance": tolerance,
        }

        baseline_source = git_blob(
            BASELINE_RUNNER_BLOB
        )

        migrated_source = RUNNER_PATH.read_bytes()

        report["baseline"]["sha256"] = (
            sha256_bytes(baseline_source)
        )

        report["migrated"]["sha256"] = (
            sha256_bytes(migrated_source)
        )

        expected = build_independent_reference(
            activations
        )

        if set(expected) != set(REQUIRED_OPERATIONS):

            raise ValueError(
                "Independent reference does not contain "
                "exactly the eight required operations"
            )

        with tempfile.TemporaryDirectory(
            prefix="p2_numeric_equivalence_"
        ) as temporary_name:

            temporary_directory = Path(
                temporary_name
            )

            baseline_runner = load_runner_from_source(
                baseline_source,
                "p2_numeric_baseline_runner",
                temporary_directory,
            )

            migrated_runner = load_runner_from_source(
                migrated_source,
                "p2_numeric_migrated_runner",
                temporary_directory,
            )

            baseline_outputs = evaluate_runner(
                baseline_runner,
                activations,
                expected,
                tolerance,
            )

            migrated_outputs = evaluate_runner(
                migrated_runner,
                activations,
                expected,
                tolerance,
            )

        # -------------------------------------------------
        # Compare each runner with the independent oracle
        # and compare baseline directly with migrated output.
        # -------------------------------------------------

        all_operation_statuses = []

        for operation in REQUIRED_OPERATIONS:

            baseline_vs_reference = compare_arrays(
                baseline_outputs[operation],
                expected[operation],
                tolerance,
            )

            migrated_vs_reference = compare_arrays(
                migrated_outputs[operation],
                expected[operation],
                tolerance,
            )

            baseline_vs_migrated = compare_arrays(
                baseline_outputs[operation],
                migrated_outputs[operation],
                tolerance,
            )

            operation_passed = all(
                result["status"] == "PASS"
                for result in (
                    baseline_vs_reference,
                    migrated_vs_reference,
                    baseline_vs_migrated,
                )
            )

            report["operations"][operation] = {
                "status": (
                    "PASS"
                    if operation_passed
                    else "FAIL"
                ),
                "baseline_vs_independent_reference": (
                    baseline_vs_reference
                ),
                "migrated_vs_independent_reference": (
                    migrated_vs_reference
                ),
                "baseline_vs_migrated": (
                    baseline_vs_migrated
                ),
            }

            all_operation_statuses.append(
                "PASS"
                if operation_passed
                else "FAIL"
            )

        report["execution"] = {
            "mode": (
                "In-process execution of the actual production "
                "operation callables exposed by each runner's "
                "build_operations() function."
            ),
            "baseline_runner_executed": True,
            "migrated_runner_executed": True,
            "independent_reference_executed": True,
            "benchmark_timing_comparison": (
                "Not part of this audit."
            ),
        }

        if all(
            status == "PASS"
            for status in all_operation_statuses
        ):

            report["status"] = "PASS"

        else:

            report["status"] = "FAIL"

    except Exception as exc:

        report["status"] = "NOT VERIFIED"

        report["issues"].append(
            f"{type(exc).__name__}: {exc}"
        )

        report["traceback"] = traceback.format_exc()

    write_report(report)

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    if report["status"] == "FAIL":

        return 1

    if report["status"] == "NOT VERIFIED":

        return 2

    return 0


if __name__ == "__main__":

    raise SystemExit(main())
