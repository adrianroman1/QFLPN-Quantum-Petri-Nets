"""Reproducible numerical-operation benchmark for QFLPN P2.

The benchmark measures the canonical four-qubit P2 operations.
Expected numerical results are constructed independently from the
production functions used by the timed callables.

Generated files, all in P2/benchmarks:
    BENCHMARK_RESULTS.md
    benchmark_report.json
    benchmark_results.csv
    environment.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pennylane as qml

P2_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = P2_ROOT.parent
BENCHMARK_DIR = P2_ROOT / "benchmarks"
CODE_DIR = P2_ROOT / "code"

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

CONFIG_PATH = BENCHMARK_DIR / "benchmark_config.json"

JSON_FILENAME = "benchmark_report.json"
CSV_FILENAME = "benchmark_results.csv"
MARKDOWN_FILENAME = "BENCHMARK_RESULTS.md"
ENVIRONMENT_FILENAME = "environment.txt"

EXPECTED_OPERATIONS = (
    "rotation_operator",
    "c3x_operator",
    "transition_operator",
    "state_evolution",
    "density_matrix",
    "reduced_density_q4",
    "reduced_density_q123",
    "pennylane_execution",
)


def utc_now() -> str:
    """Return an offset-aware UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def command_output(command: list[str]) -> str:
    """Return diagnostic output without making the benchmark depend on it."""

    try:
        result = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"UNAVAILABLE: {exc}"

    output = (result.stdout + result.stderr).strip()

    if not output:
        return f"NO OUTPUT (exit={result.returncode})"

    return output


def git_metadata() -> dict:
    """Collect Git metadata when the benchmark runs inside a checkout."""

    return {
        "commit": command_output(
            ["git", "rev-parse", "HEAD"]
        ),
        "branch": os.environ.get(
            "GITHUB_REF_NAME",
            command_output(
                ["git", "branch", "--show-current"]
            ),
        ),
        "worktree_status": command_output(
            ["git", "status", "--short"]
        ),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get(
            "GITHUB_RUN_ATTEMPT"
        ),
        "github_workflow": os.environ.get(
            "GITHUB_WORKFLOW"
        ),
    }


def collect_environment() -> dict:
    """Capture the execution environment used for the measurements."""

    try:
        import importlib.metadata

        scipy_version = importlib.metadata.version("scipy")
    except importlib.metadata.PackageNotFoundError:
        scipy_version = None

    try:
        import psutil

        physical_memory = int(
            psutil.virtual_memory().total
        )
        logical_cpus = int(
            psutil.cpu_count(logical=True) or 0
        )
        physical_cpus = psutil.cpu_count(logical=False)
    except ImportError:
        physical_memory = None
        logical_cpus = os.cpu_count() or 0
        physical_cpus = None

    cpu_model = platform.processor() or "UNAVAILABLE"

    return {
        "captured_at_utc": utc_now(),
        "repository_root": str(REPOSITORY_ROOT),
        "git": git_metadata(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "numpy_version": np.__version__,
        "pennylane_version": qml.__version__,
        "scipy_version": scipy_version,
        "operating_system": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_model": cpu_model,
        "logical_cpu_count": logical_cpus,
        "physical_cpu_count": physical_cpus,
        "physical_memory_bytes": physical_memory,
        "benchmark_timer": "time.perf_counter_ns",
        "qubit_count": 4,
        "hilbert_dimension": 16,
        "canonical_memberships": list(DEFAULT_ACTIVATIONS),
        "numerical_equivalence_tolerance": 1e-12,
    }


def environment_text(environment: dict) -> str:
    """Format the captured environment as a readable text file."""

    lines = [
        "P2 BENCHMARK ENVIRONMENT",
        "=" * 72,
    ]

    for key, value in environment.items():
        if isinstance(value, (dict, list)):
            rendered = json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
            )
        else:
            rendered = json.dumps(
                value,
                ensure_ascii=False,
            )

        lines.append(f"{key}: {rendered}")

    return "\n".join(lines) + "\n"


def load_config(path: Path) -> dict:
    """Load and validate the canonical P2 benchmark configuration."""

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            "Benchmark configuration must be a JSON object."
        )

    if data.get("schema_version") != 1:
        raise ValueError(
            "Unsupported benchmark configuration schema."
        )

    if data.get("project") != "QFLPN P2":
        raise ValueError(
            "Unexpected benchmark project."
        )

    if data.get("qubits") != 4:
        raise ValueError(
            "P2 benchmark requires four qubits."
        )

    if data.get("hilbert_dimension") != 16:
        raise ValueError(
            "P2 benchmark dimension must be 16."
        )

    if data.get("basis_order") != "big-endian":
        raise ValueError(
            "Unsupported basis ordering."
        )

    if data.get("operator_order") != "U = C3X @ U_rot":
        raise ValueError(
            "Unexpected operator ordering."
        )

    activations = data.get("activation_vector")

    if activations != list(DEFAULT_ACTIVATIONS):
        raise ValueError(
            "Benchmark activations differ from the canonical P2 model."
        )

    warmups = data.get("warmups")
    repetitions = data.get("repetitions")
    tolerance = data.get("numerical_tolerance")

    if type(warmups) is not int or warmups < 5:
        raise ValueError(
            "At least five warm-up iterations are required."
        )

    if type(repetitions) is not int or repetitions < 30:
        raise ValueError(
            "At least 30 measured repetitions are required."
        )

    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not np.isfinite(tolerance)
        or tolerance <= 0
    ):
        raise ValueError(
            "Invalid numerical tolerance."
        )

    configured_operations = data.get("operations")

    if configured_operations != list(EXPECTED_OPERATIONS):
        raise ValueError(
            "Configured benchmark operations do not match "
            "the required P2 operation set."
        )

    if data.get("timer") != "time.perf_counter_ns":
        raise ValueError(
            "Unsupported benchmark timer."
        )

    return data


def independent_rotation_operator(
    activations: tuple[float, ...],
) -> np.ndarray:
    """Construct the tensor-product RY operator independently."""

    result = np.array(
        [[1.0 + 0.0j]],
        dtype=np.complex128,
    )

    for activation in activations:
        theta = 2.0 * np.arcsin(
            np.sqrt(activation)
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

        result = np.kron(result, ry)

    return result


def independent_c3x_operator() -> np.ndarray:
    """Construct the C3X permutation independently."""

    result = np.eye(
        16,
        dtype=np.complex128,
    )

    result[14, 14] = 0.0
    result[15, 15] = 0.0
    result[14, 15] = 1.0
    result[15, 14] = 1.0

    return result


def independent_density_matrix(
    state: np.ndarray,
) -> np.ndarray:
    """Construct the pure-state density matrix independently."""

    vector = np.asarray(
        state,
        dtype=np.complex128,
    )

    return np.outer(
        vector,
        np.conjugate(vector),
    )


def independent_reduced_states(
    state: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute both partial traces using an independent tensor reshape."""

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


def independent_reference(
    activations: tuple[float, ...],
) -> dict[str, np.ndarray]:
    """Build independent expected outputs for every timed operation."""

    rotation = independent_rotation_operator(
        activations
    )

    gate = independent_c3x_operator()

    complete_operator = gate @ rotation

    initial = np.zeros(
        16,
        dtype=np.complex128,
    )
    initial[0] = 1.0

    state = complete_operator @ initial

    rho = independent_density_matrix(state)

    rho_q4, rho_q123 = independent_reduced_states(
        state
    )

    return {
        "rotation_operator": rotation,
        "c3x_operator": gate,
        "transition_operator": complete_operator,
        "state_evolution": state,
        "density_matrix": rho,
        "reduced_density_q4": rho_q4,
        "reduced_density_q123": rho_q123,
        "pennylane_execution": state,
    }


def reduced_density_q4(
    state: np.ndarray,
) -> np.ndarray:
    """Production benchmark operation: trace out q1, q2 and q3."""

    tensor = np.asarray(
        state,
        dtype=np.complex128,
    ).reshape(8, 2)

    return tensor.conj().T @ tensor


def reduced_density_q123(
    state: np.ndarray,
) -> np.ndarray:
    """Production benchmark operation: trace out q4."""

    tensor = np.asarray(
        state,
        dtype=np.complex128,
    ).reshape(8, 2)

    return tensor @ tensor.conj().T


def make_pennylane_circuit():
    """Build the four-qubit PennyLane circuit matching P2 conventions."""

    device = qml.device(
        "default.qubit",
        wires=4,
    )

    @qml.qnode(device)
    def circuit(activations):
        for wire, activation in enumerate(activations):
            theta = 2.0 * np.arcsin(
                np.sqrt(activation)
            )
            qml.RY(theta, wires=wire)

        controlled_x = qml.ctrl(
            qml.PauliX,
            control=[0, 1, 2],
        )

        controlled_x(wires=3)

        return qml.state()

    return circuit


def numerical_error(
    actual: np.ndarray,
    expected: np.ndarray,
) -> float:
    """Return a finite Frobenius/vector norm difference."""

    actual_array = np.asarray(actual)
    expected_array = np.asarray(expected)

    if actual_array.shape != expected_array.shape:
        return float("inf")

    if not np.all(np.isfinite(actual_array)):
        return float("inf")

    if not np.all(np.isfinite(expected_array)):
        return float("inf")

    return float(
        np.linalg.norm(
            actual_array - expected_array
        )
    )


def time_operation(
    name: str,
    function: Callable[[], np.ndarray],
    expected: np.ndarray,
    warmups: int,
    repetitions: int,
    tolerance: float,
) -> dict:
    """Warm up, independently validate, and measure one operation."""

    for _ in range(warmups):
        function()

    reference_result = np.asarray(
        function()
    )

    error = numerical_error(
        reference_result,
        expected,
    )

    passed = bool(
        np.isfinite(error)
        and error <= tolerance
    )

    durations: list[int] = []

    for _ in range(repetitions):
        start = time.perf_counter_ns()
        result = function()
        elapsed = time.perf_counter_ns() - start

        durations.append(int(elapsed))

        result_array = np.asarray(result)

        if not np.all(np.isfinite(result_array)):
            passed = False

        if result_array.shape != expected.shape:
            passed = False

    return {
        "operation": name,
        "warmups": warmups,
        "repetitions": repetitions,
        "minimum_ns": min(durations),
        "median_ns": float(
            statistics.median(durations)
        ),
        "mean_ns": float(
            statistics.mean(durations)
        ),
        "maximum_ns": max(durations),
        "standard_deviation_ns": float(
            statistics.pstdev(durations)
        ),
        "numerical_error": error,
        "numerical_tolerance": tolerance,
        "passed": passed,
    }


def build_operations(
    activations: tuple[float, ...],
    expected: dict[str, np.ndarray],
) -> tuple[list[tuple], np.ndarray]:
    """Pair timed production operations with independent references."""

    state = reference_state(activations)

    pennylane_circuit = make_pennylane_circuit()

    pennylane_state = np.asarray(
        pennylane_circuit(activations),
        dtype=np.complex128,
    )

    operations = [
        (
            "rotation_operator",
            lambda: rotation_operator(activations),
            expected["rotation_operator"],
        ),
        (
            "c3x_operator",
            c3x_operator,
            expected["c3x_operator"],
        ),
        (
            "transition_operator",
            lambda: transition_operator(activations),
            expected["transition_operator"],
        ),
        (
            "state_evolution",
            lambda: transition_operator(activations)
            @ initial_state(),
            expected["state_evolution"],
        ),
        (
            "density_matrix",
            lambda: density_matrix(state),
            expected["density_matrix"],
        ),
        (
            "reduced_density_q4",
            lambda: reduced_density_q4(state),
            expected["reduced_density_q4"],
        ),
        (
            "reduced_density_q123",
            lambda: reduced_density_q123(state),
            expected["reduced_density_q123"],
        ),
        (
            "pennylane_execution",
            lambda: np.asarray(
                pennylane_circuit(activations),
                dtype=np.complex128,
            ),
            expected["pennylane_execution"],
        ),
    ]

    return operations, pennylane_state


def write_csv(
    path: Path,
    rows: list[dict],
) -> None:
    """Write raw operation-level benchmark results."""

    if not rows:
        raise ValueError(
            "No benchmark rows were produced."
        )

    fieldnames = [
        "operation",
        "warmups",
        "repetitions",
        "minimum_ns",
        "median_ns",
        "mean_ns",
        "maximum_ns",
        "standard_deviation_ns",
        "numerical_error",
        "numerical_tolerance",
        "passed",
    ]

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


def markdown_report(report: dict) -> str:
    """Render a readable report from the measured JSON data."""

    lines = [
        "# QFLPN P2 — Benchmark Results",
        "",
        f"- Generated (UTC): `{report['timestamp_utc']}`",
        f"- Status: **{report['status']}**",
        f"- Qubits: `{report['qubits']}`",
        f"- Hilbert dimension: `{report['hilbert_dimension']}`",
        f"- Basis order: `{report['basis_order']}`",
        f"- Operator order: `{report['operator_order']}`",
        f"- Warmups per operation: `{report['warmups']}`",
        f"- Measured repetitions: `{report['repetitions']}`",
        f"- Timer: `{report['timer']}`",
        f"- Numerical tolerance: `{report['numerical_tolerance']:.3e}`",
        "",
        "## Numerical parity",
        "",
        (
            "PennyLane / independent NumPy state difference: "
            f"`{report['pennylane_numpy_maximum_difference']:.6e}`"
        ),
        "",
        "## Operation measurements",
        "",
        "| Operation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Error | Check |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for row in report["operations"]:
        lines.append(
            "| "
            + str(row["operation"])
            + f" | {row['minimum_ns']}"
            + f" | {row['median_ns']:.2f}"
            + f" | {row['mean_ns']:.2f}"
            + f" | {row['maximum_ns']}"
            + f" | {row['standard_deviation_ns']:.2f}"
            + f" | {row['numerical_error']:.3e}"
            + f" | {'PASS' if row['passed'] else 'FAIL'} |"
        )

    lines.extend(
        [
            "",
            "## Methodology",
            "",
            "- Five or more warm-up iterations are performed per operation.",
            "- At least 30 measured repetitions are collected per operation.",
            "- Timing uses `time.perf_counter_ns()`.",
            "- Numerical references are constructed independently of the timed production callables.",
            "- PennyLane state evolution is compared with the independent NumPy state.",
            "- All numerical comparisons use the configured absolute norm tolerance.",
            "",
            "## Interpretation and limitations",
            "",
            "These measurements describe the canonical four-qubit P2 workload only.",
            "They do not establish asymptotic scalability or performance for larger quantum systems.",
            "Execution times depend on the processor, operating system, Python runtime, installed packages and virtual-machine load.",
            "Benchmark timings are supplementary performance evidence and do not independently establish mathematical acceptance.",
            "",
            "## Generated evidence",
            "",
            "- `benchmark_report.json` — structured measurements and metadata.",
            "- `benchmark_results.csv` — operation-level measurements.",
            "- `environment.txt` — execution environment.",
            "",
            f"**Overall numerical status: {report['status']}**",
            "",
        ]
    )

    return "\n".join(lines)


def run_benchmark(
    config: dict,
    output_dir: Path,
) -> dict:
    """Execute P2 measurements and write the four agreed output files."""

    activations = tuple(
        float(value)
        for value in config["activation_vector"]
    )

    warmups = config["warmups"]
    repetitions = config["repetitions"]
    tolerance = float(
        config["numerical_tolerance"]
    )

    environment = collect_environment()

    independent = independent_reference(
        activations
    )

    operations, pennylane_state = build_operations(
        activations,
        independent,
    )

    parity_error = numerical_error(
        pennylane_state,
        independent["state_evolution"],
    )

    rows = []

    for (
        name,
        function,
        expected,
    ) in operations:
        rows.append(
            time_operation(
                name,
                function,
                expected,
                warmups,
                repetitions,
                tolerance,
            )
        )

    all_operations_passed = (
        len(rows) == len(EXPECTED_OPERATIONS)
        and all(row["passed"] for row in rows)
    )

    parity_passed = bool(
        np.isfinite(parity_error)
        and parity_error <= tolerance
    )

    all_passed = bool(
        all_operations_passed
        and parity_passed
    )

    report = {
        "schema_version": 1,
        "benchmark_id": "P2-CANONICAL-4Q-NUMERICAL-OPERATIONS",
        "project": "QFLPN P2",
        "timestamp_utc": utc_now(),
        "qubits": 4,
        "hilbert_dimension": 16,
        "basis_order": "big-endian",
        "activation_vector": list(activations),
        "operator_order": "U = C3X @ U_rot",
        "warmups": warmups,
        "repetitions": repetitions,
        "timer": "time.perf_counter_ns",
        "numerical_tolerance": tolerance,
        "environment": environment,
        "independent_reference": {
            "method": (
                "Independent Kronecker RY construction, "
                "independent C3X permutation, direct state evolution, "
                "outer-product density matrix and tensor partial traces."
            ),
            "used_for_timed_operation_checks": True,
        },
        "pennylane_numpy_maximum_difference": parity_error,
        "operations": rows,
        "all_checks_pass": all_passed,
        "status": "PASS" if all_passed else "FAIL",
        "limitations": [
            "Only the canonical four-qubit P2 instance is measured.",
            "The results do not establish asymptotic scalability.",
            "The results do not establish million-qubit or HPC performance.",
            "Execution times depend on the measured environment and system load.",
            "Benchmark results are supplementary evidence, not a substitute for mathematical validation.",
        ],
    }

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = output_dir / JSON_FILENAME
    csv_path = output_dir / CSV_FILENAME
    markdown_path = output_dir / MARKDOWN_FILENAME
    environment_path = output_dir / ENVIRONMENT_FILENAME

    write_csv(
        csv_path,
        rows,
    )

    json_path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    markdown_path.write_text(
        markdown_report(report),
        encoding="utf-8",
    )

    environment_path.write_text(
        environment_text(environment),
        encoding="utf-8",
    )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the canonical QFLPN P2 benchmark."
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=BENCHMARK_DIR,
        help="Directory for the five agreed benchmark files.",
    )

    args = parser.parse_args()

    try:
        config = load_config(
            args.config.resolve(strict=True)
        )

        report = run_benchmark(
            config,
            args.output.resolve(),
        )

    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        ImportError,
        ArithmeticError,
    ) as exc:
        print("FAIL:", exc)
        return 2

    print("Benchmark output:", args.output.resolve())
    print("Operations:", len(report["operations"]))
    print("Warmups:", report["warmups"])
    print("Repetitions:", report["repetitions"])
    print(
        "PennyLane / independent NumPy difference:",
        f"{report['pennylane_numpy_maximum_difference']:.6e}",
    )
    print("Status:", report["status"])

    for filename in (
        MARKDOWN_FILENAME,
        JSON_FILENAME,
        CSV_FILENAME,
        ENVIRONMENT_FILENAME,
    ):
        print(
            "Generated:",
            args.output.resolve() / filename,
        )

    if report["status"] != "PASS":
        print("VERDICT: BENCHMARK_REJECTED")
        return 1

    print("VERDICT: BENCHMARK_COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
