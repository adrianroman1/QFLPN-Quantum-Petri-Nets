"""Reproducible paired numerical-operation benchmark for QFLPN P2."""

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

RUNTIME_SCOPE = (
    "Elapsed wall-clock time from benchmark CLI start, before configuration "
    "loading, through the first complete generation of the four evidence "
    "files. Final JSON and Markdown persistence of the measured duration "
    "is excluded to avoid a self-referential timing measurement."
)

WORLD_RECORD_STATUS = "NO_DIRECTLY_COMPARABLE_RECORD"

WORLD_RECORD_DISPLAY = (
    "N/A — no verified directly comparable record"
)

LITERATURE_BENCHMARKS = [
    {
        "id": "BENCHPRESS-2025",
        "title": (
            "Benchmarking the performance of quantum computing software "
            "for quantum circuit creation, manipulation and compilation"
        ),
        "authors": [
            "Paul D. Nation",
            "Abdullah Ash Saki",
            "Sebastian Brandhofer",
            "Luciano Bello",
            "Shelly Garion",
            "Matthew Treinish",
            "Ali Javadi-Abhari",
        ],
        "venue": "Nature Computational Science",
        "year": 2025,
        "doi": "10.1038/s43588-025-00792-y",
        "url": "https://doi.org/10.1038/s43588-025-00792-y",
        "scope": (
            "Benchpress suite with more than 1000 tests and circuits "
            "up to 930 qubits."
        ),
        "p2_comparability": (
            "Methodological reference only. Not an equivalent four-qubit "
            "operation-level timing record."
        ),
    },
    {
        "id": "STATEVECTOR-HPC-2026",
        "title": (
            "Benchmarking quantum computing statevector simulators "
            "on high-performance computing"
        ),
        "authors": [
            "Jesús Cerrudo-Herrera",
            "Daniel Talaván-Vega",
            "Paloma Rodríguez-Oliver",
            "Ahmed Ziabat-Ziabat",
            "Juan Antonio Rico-Gallego",
        ],
        "venue": "Simulation",
        "year": 2026,
        "doi": "10.1177/00375497261438515",
        "url": "https://doi.org/10.1177/00375497261438515",
        "scope": (
            "Seven statevector simulators, circuits from 3 to 30 qubits, "
            "runtime, memory and multicore scalability."
        ),
        "p2_comparability": (
            "External simulator landscape. Hardware, circuits and "
            "measurement scope are not identical to P2."
        ),
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def command_output(command: list[str]) -> str:
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


def detect_cpu_model() -> str:
    """Return a CPU model string, never a numeric processor index."""

    cpuinfo = Path("/proc/cpuinfo")

    if cpuinfo.is_file():
        try:
            lines = cpuinfo.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()

            preferred_keys = ("model name", "hardware", "processor")

            for key in preferred_keys:
                for line in lines:
                    field, separator, value = line.partition(":")

                    if (
                        separator
                        and field.strip().lower() == key
                        and value.strip()
                    ):
                        candidate = value.strip()

                        if not candidate.isdigit():
                            return candidate

        except OSError:
            pass

    processor = platform.processor().strip()

    if processor and not processor.isdigit():
        return processor

    return "UNAVAILABLE"


def git_metadata() -> dict:
    return {
        "commit": command_output(["git", "rev-parse", "HEAD"]),
        "branch": os.environ.get(
            "GITHUB_REF_NAME",
            command_output(["git", "branch", "--show-current"]),
        ),
        "worktree_status": command_output(["git", "status", "--short"]),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_workflow": os.environ.get("GITHUB_WORKFLOW"),
    }


def collect_environment() -> dict:
    try:
        import importlib.metadata

        scipy_version = importlib.metadata.version("scipy")
    except importlib.metadata.PackageNotFoundError:
        scipy_version = None

    try:
        import psutil

        physical_memory = int(psutil.virtual_memory().total)
        logical_cpus = int(psutil.cpu_count(logical=True) or 0)
        physical_cpus = psutil.cpu_count(logical=False)

    except ImportError:
        physical_memory = None
        logical_cpus = os.cpu_count() or 0
        physical_cpus = None

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
        "cpu_model": detect_cpu_model(),
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
    lines = ["P2 BENCHMARK ENVIRONMENT", "=" * 72]

    for key, value in environment.items():
        if isinstance(value, (dict, list)):
            rendered = json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
            )
        else:
            rendered = json.dumps(value, ensure_ascii=False)

        lines.append(f"{key}: {rendered}")

    return "\n".join(lines) + "\n"


def load_config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("Benchmark configuration must be a JSON object.")

    if data.get("schema_version") != 1:
        raise ValueError("Unsupported benchmark configuration schema.")

    if data.get("project") != "QFLPN P2":
        raise ValueError("Unexpected benchmark project.")

    if data.get("qubits") != 4:
        raise ValueError("P2 benchmark requires four qubits.")

    if data.get("hilbert_dimension") != 16:
        raise ValueError("P2 benchmark dimension must be 16.")

    if data.get("basis_order") != "big-endian":
        raise ValueError("Unsupported basis ordering.")

    if data.get("operator_order") != "U = C3X @ U_rot":
        raise ValueError("Unexpected operator ordering.")

    if data.get("activation_vector") != list(DEFAULT_ACTIVATIONS):
        raise ValueError(
            "Benchmark activations differ from the canonical P2 model."
        )

    warmups = data.get("warmups")
    repetitions = data.get("repetitions")
    tolerance = data.get("numerical_tolerance")

    if type(warmups) is not int or warmups < 5:
        raise ValueError("At least five warm-up iterations are required.")

    if type(repetitions) is not int or repetitions < 30:
        raise ValueError("At least 30 measured repetitions are required.")

    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not np.isfinite(tolerance)
        or tolerance <= 0
    ):
        raise ValueError("Invalid numerical tolerance.")

    if data.get("operations") != list(EXPECTED_OPERATIONS):
        raise ValueError(
            "Configured benchmark operations do not match "
            "the required P2 operation set."
        )

    if data.get("timer") != "time.perf_counter_ns":
        raise ValueError("Unsupported benchmark timer.")

    return data


# ---------------------------------------------------------------------
# Independent reference implementations
# ---------------------------------------------------------------------

def independent_rotation_operator(
    activations: tuple[float, ...],
) -> np.ndarray:
    result = np.array([[1.0 + 0.0j]], dtype=np.complex128)

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


def independent_c3x_operator() -> np.ndarray:
    result = np.eye(16, dtype=np.complex128)

    result[14, 14] = 0.0
    result[15, 15] = 0.0
    result[14, 15] = 1.0
    result[15, 14] = 1.0

    return result


def independent_density_matrix(state: np.ndarray) -> np.ndarray:
    vector = np.asarray(state, dtype=np.complex128)
    return np.outer(vector, np.conjugate(vector))


def independent_reduced_states(
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


def independent_reference(
    activations: tuple[float, ...],
) -> dict[str, np.ndarray]:
    rotation = independent_rotation_operator(activations)
    gate = independent_c3x_operator()
    complete_operator = gate @ rotation

    initial = np.zeros(16, dtype=np.complex128)
    initial[0] = 1.0

    state = complete_operator @ initial

    rho = independent_density_matrix(state)
    rho_q4, rho_q123 = independent_reduced_states(state)

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


# ---------------------------------------------------------------------
# Production-side operations
# ---------------------------------------------------------------------

def reduced_density_q4(state: np.ndarray) -> np.ndarray:
    tensor = np.asarray(
        state,
        dtype=np.complex128,
    ).reshape(8, 2)

    return tensor.conj().T @ tensor


def reduced_density_q123(state: np.ndarray) -> np.ndarray:
    tensor = np.asarray(
        state,
        dtype=np.complex128,
    ).reshape(8, 2)

    return tensor @ tensor.conj().T


def make_pennylane_circuit():
    device = qml.device("default.qubit", wires=4)

    @qml.qnode(device)
    def circuit(activations):
        for wire, activation in enumerate(activations):
            theta = 2.0 * np.arcsin(np.sqrt(activation))
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
    actual_array = np.asarray(actual)
    expected_array = np.asarray(expected)

    if actual_array.shape != expected_array.shape:
        return float("inf")

    if not np.all(np.isfinite(actual_array)):
        return float("inf")

    if not np.all(np.isfinite(expected_array)):
        return float("inf")

    return float(np.linalg.norm(actual_array - expected_array))


def build_operations(
    activations: tuple[float, ...],
    expected: dict[str, np.ndarray],
) -> tuple[list[tuple], np.ndarray]:
    production_state = reference_state(activations)
    independent_state = expected["state_evolution"]

    pennylane_circuit = make_pennylane_circuit()

    pennylane_state = np.asarray(
        pennylane_circuit(activations),
        dtype=np.complex128,
    )

    def independent_transition():
        return (
            independent_c3x_operator()
            @ independent_rotation_operator(activations)
        )

    def independent_state_evolution():
        initial = np.zeros(16, dtype=np.complex128)
        initial[0] = 1.0
        return independent_transition() @ initial

    def independent_pennylane_reference():
        return independent_state_evolution()

    operations = [
        (
            "rotation_operator",
            lambda: rotation_operator(activations),
            lambda: independent_rotation_operator(activations),
            expected["rotation_operator"],
        ),
        (
            "c3x_operator",
            c3x_operator,
            independent_c3x_operator,
            expected["c3x_operator"],
        ),
        (
            "transition_operator",
            lambda: transition_operator(activations),
            independent_transition,
            expected["transition_operator"],
        ),
        (
            "state_evolution",
            lambda: transition_operator(activations) @ initial_state(),
            independent_state_evolution,
            expected["state_evolution"],
        ),
        (
            "density_matrix",
            lambda: density_matrix(production_state),
            lambda: independent_density_matrix(independent_state),
            expected["density_matrix"],
        ),
        (
            "reduced_density_q4",
            lambda: reduced_density_q4(production_state),
            lambda: independent_reduced_states(independent_state)[0],
            expected["reduced_density_q4"],
        ),
        (
            "reduced_density_q123",
            lambda: reduced_density_q123(production_state),
            lambda: independent_reduced_states(independent_state)[1],
            expected["reduced_density_q123"],
        ),
        (
            "pennylane_execution",
            lambda: np.asarray(
                pennylane_circuit(activations),
                dtype=np.complex128,
            ),
            independent_pennylane_reference,
            expected["pennylane_execution"],
        ),
    ]

    return operations, pennylane_state


# ---------------------------------------------------------------------
# Paired timing
# ---------------------------------------------------------------------

def statistics_for(durations: list[int]) -> dict:
    if not durations:
        raise ValueError("Cannot summarize an empty timing sample.")

    median_ns = float(statistics.median(durations))

    if median_ns <= 0:
        raise ArithmeticError("Median timing must be positive.")

    return {
        "minimum_ns": int(min(durations)),
        "median_ns": median_ns,
        "mean_ns": float(statistics.mean(durations)),
        "maximum_ns": int(max(durations)),
        "standard_deviation_ns": float(
            statistics.pstdev(durations)
        ),
        "samples": len(durations),
        "operations_per_second": 1_000_000_000.0 / median_ns,
    }


def timed_call(function: Callable[[], np.ndarray]) -> tuple[np.ndarray, int]:
    start = time.perf_counter_ns()
    result = function()
    elapsed = time.perf_counter_ns() - start

    if elapsed <= 0:
        raise ArithmeticError("A measured duration was not positive.")

    return np.asarray(result), int(elapsed)


def time_paired_operation(
    name: str,
    production_function: Callable[[], np.ndarray],
    independent_function: Callable[[], np.ndarray],
    expected: np.ndarray,
    warmups: int,
    repetitions: int,
    tolerance: float,
) -> dict:
    # Warm-up both implementations before collecting measurements.
    for _ in range(warmups):
        production_function()
        independent_function()

    production_durations: list[int] = []
    independent_durations: list[int] = []
    paired_samples: list[dict] = []

    production_error = 0.0
    independent_error = 0.0

    production_passed = True
    independent_passed = True

    for sample_index in range(repetitions):
        # Alternate execution order to reduce systematic order bias.
        if sample_index % 2 == 0:
            first = "production"
        else:
            first = "independent"

        if first == "production":
            production_result, production_ns = timed_call(
                production_function
            )
            independent_result, independent_ns = timed_call(
                independent_function
            )
        else:
            independent_result, independent_ns = timed_call(
                independent_function
            )
            production_result, production_ns = timed_call(
                production_function
            )

        current_production_error = numerical_error(
            production_result,
            expected,
        )

        current_independent_error = numerical_error(
            independent_result,
            expected,
        )

        production_error = max(
            production_error,
            current_production_error,
        )

        independent_error = max(
            independent_error,
            current_independent_error,
        )

        if (
            not np.isfinite(current_production_error)
            or current_production_error > tolerance
        ):
            production_passed = False

        if (
            not np.isfinite(current_independent_error)
            or current_independent_error > tolerance
        ):
            independent_passed = False

        production_durations.append(production_ns)
        independent_durations.append(independent_ns)

        paired_samples.append({
            "sample_index": sample_index + 1,
            "first_execution": first,
            "production_ns": production_ns,
            "independent_ns": independent_ns,
            "difference_independent_minus_production_ns": (
                independent_ns - production_ns
            ),
        })

    production_stats = statistics_for(production_durations)
    independent_stats = statistics_for(independent_durations)

    paired_differences = [
        sample["difference_independent_minus_production_ns"]
        for sample in paired_samples
    ]

    production_wins = sum(
        production_ns < independent_ns
        for production_ns, independent_ns in zip(
            production_durations,
            independent_durations,
        )
    )

    ties = sum(
        production_ns == independent_ns
        for production_ns, independent_ns in zip(
            production_durations,
            independent_durations,
        )
    )

    reference_median = independent_stats["median_ns"]
    production_median = production_stats["median_ns"]

    ratio = reference_median / production_median

    if reference_median > 0:
        production_reduction_percent = (
            (reference_median - production_median)
            / reference_median
            * 100.0
        )
    else:
        production_reduction_percent = 0.0

    passed = bool(
        production_passed
        and independent_passed
    )

    return {
        "operation": name,
        "warmups": warmups,
        "repetitions": repetitions,

        # Existing production fields retained for CSV compatibility.
        "minimum_ns": production_stats["minimum_ns"],
        "median_ns": production_stats["median_ns"],
        "mean_ns": production_stats["mean_ns"],
        "maximum_ns": production_stats["maximum_ns"],
        "standard_deviation_ns": (
            production_stats["standard_deviation_ns"]
        ),
        "operations_per_second": (
            production_stats["operations_per_second"]
        ),
        "numerical_error": production_error,
        "numerical_tolerance": tolerance,
        "passed": passed,

        "production": production_stats,
        "independent": independent_stats,

        "paired_comparison": {
            "median_difference_independent_minus_production_ns": (
                float(statistics.median(paired_differences))
            ),
            "production_win_count": production_wins,
            "tie_count": ties,
            "production_win_rate_percent": (
                production_wins / repetitions * 100.0
            ),
            "independent_over_production_median_ratio": ratio,
            "production_reduction_percent_vs_independent": (
                production_reduction_percent
            ),
        },

        "independent_numerical_error": independent_error,
        "independent_passed": independent_passed,
        "paired_samples": paired_samples,

        "world_record": {
            "display": WORLD_RECORD_DISPLAY,
            "status": WORLD_RECORD_STATUS,
            "verified_value_ns": None,
            "source": None,
            "reason": (
                "No verified published measurement was found for the "
                "same operation, four-qubit configuration, numerical "
                "semantics, hardware and timing protocol."
            ),
        },
    }


# ---------------------------------------------------------------------
# Evidence generation
# ---------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("No benchmark rows were produced.")

    fieldnames = [
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

    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            extrasaction="raise",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow({
                key: row[key]
                for key in fieldnames
            })


def markdown_report(report: dict) -> str:
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
        (
            "- Total benchmark runtime: "
            f"**{report['total_runtime_seconds']:.6f} seconds**"
        ),
        (
            "- Total production execution time: "
            f"**{report['production_total_execution_seconds']:.9f} seconds**"
        ),
        (
            "- Total independent execution time: "
            f"**{report['independent_total_execution_seconds']:.9f} seconds**"
        ),
        (
            "- Total timed execution time (both implementations): "
            f"**{report['combined_timed_execution_seconds']:.9f} seconds**"
        ),
        (
            "- Initial evidence-generation time: "
            f"**{report['initial_evidence_generation_seconds']:.6f} seconds**"
        ),
        f"- Runtime measurement scope: {report['runtime_measurement_scope']}",
        "",
        "## Numerical parity",
        "",
        (
            "PennyLane / independent NumPy state difference: "
            f"`{report['pennylane_numpy_maximum_difference']:.6e}`"
        ),
        "",
        "## Paired operation measurements",
        "",
        (
            "| Operation | Production median (ns) | Independent median (ns) "
            "| Production reduction (%) | Paired median difference (ns) "
            "| Production wins (%) | World record |"
        ),
        "|---|---:|---:|---:|---:|---:|---|",
    ]

    for row in report["operations"]:
        paired = row["paired_comparison"]

        lines.append(
            f"| {row['operation']}"
            f" | {row['production']['median_ns']:.2f}"
            f" | {row['independent']['median_ns']:.2f}"
            f" | {paired['production_reduction_percent_vs_independent']:.3f}"
            f" | {paired['median_difference_independent_minus_production_ns']:.2f}"
            f" | {paired['production_win_rate_percent']:.2f}"
            f" | {row['world_record']['display']} |"
        )

    lines.extend([
        "",
        "## Full timing statistics",
        "",
        (
            "| Operation | Implementation | Min (ns) | Median (ns) "
            "| Mean (ns) | Max (ns) | Std. dev. (ns) | Samples |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ])

    for row in report["operations"]:
        for implementation in ("production", "independent"):
            stats = row[implementation]

            lines.append(
                f"| {row['operation']}"
                f" | {implementation}"
                f" | {stats['minimum_ns']}"
                f" | {stats['median_ns']:.2f}"
                f" | {stats['mean_ns']:.2f}"
                f" | {stats['maximum_ns']}"
                f" | {stats['standard_deviation_ns']:.2f}"
                f" | {stats['samples']} |"
            )

    lines.extend([
        "",
        "## Paired comparison interpretation",
        "",
        "- Positive median difference means the independent implementation took longer.",
        "- Production win rate is the fraction of paired samples where production was faster.",
        "- Ties are reported separately and are not counted as production wins.",
        "- The median ratio is independent median divided by production median.",
        "- Production reduction is measured relative to the independent median.",
        "- Execution order alternates between paired samples.",
        "- Numerical validation is performed after each timed call.",
        "- Both implementations must pass the configured absolute norm tolerance.",
        "",
        "## World-record and literature comparison",
        "",
        (
            "No universal world-record registry exists for the exact P2 "
            "operation-level workload."
        ),
        (
            "A published timing is accepted as a directly comparable record "
            "only when operation semantics, qubit count, numerical precision, "
            "hardware, software and measurement boundaries match."
        ),
        "",
        "| Literature source | Published scope | P2 status |",
        "|---|---|---|",
    ])

    for source in report["literature_benchmarks"]:
        lines.append(
            f"| [{source['id']}]({source['url']})"
            f" | {source['scope']}"
            f" | {source['p2_comparability']} |"
        )

    lines.extend([
        "",
        "## Methodology",
        "",
        "- At least five warm-up iterations per implementation and operation.",
        "- At least 30 paired measured repetitions per operation.",
        "- Timing uses `time.perf_counter_ns()`.",
        "- Execution order alternates within each pair.",
        "- Production and independent outputs are checked against the independent reference.",
        "- Both implementations must pass the configured absolute norm tolerance.",
        "- Production and independent statistics are computed separately.",
        "- Total operation execution times are sums of measured call durations.",
        "- Total benchmark runtime is measured separately and includes setup and initial evidence generation.",
        "- The final persistence of the runtime field is excluded from the runtime interval.",
        "",
        "## Interpretation and limitations",
        "",
        "These measurements describe the canonical four-qubit P2 workload only.",
        "The Hilbert-space dimension is 16.",
        "They do not establish asymptotic scalability or performance for larger quantum systems.",
        "They do not establish million-qubit, distributed or HPC performance.",
        "A faster result in this benchmark is not evidence of quantum speedup.",
        "Execution times depend on the processor, operating system, Python runtime, installed packages and system load.",
        "Literature studies with different circuits and hardware are contextual references, not equivalent records.",
        "",
        "## Generated evidence",
        "",
        "- `benchmark_report.json` — structured paired measurements and metadata.",
        "- `benchmark_results.csv` — production operation summary.",
        "- `environment.txt` — execution environment.",
        "",
        f"**Overall numerical status: {report['status']}**",
        "",
    ])

    return "\n".join(lines)


def write_json(path: Path, report: dict) -> None:
    path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )


def run_benchmark(
    config: dict,
    output_dir: Path,
    started_ns: int | None = None,
) -> dict:
    if started_ns is None:
        started_ns = time.perf_counter_ns()

    activations = tuple(
        float(value) for value in config["activation_vector"]
    )

    warmups = config["warmups"]
    repetitions = config["repetitions"]
    tolerance = float(config["numerical_tolerance"])

    environment = collect_environment()

    independent = independent_reference(activations)

    operations, pennylane_state = build_operations(
        activations,
        independent,
    )

    parity_error = numerical_error(
        pennylane_state,
        independent["state_evolution"],
    )

    rows = []

    for name, production_function, independent_function, expected in operations:
        rows.append(
            time_paired_operation(
                name,
                production_function,
                independent_function,
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

    production_total_ns = sum(
        sample["production_ns"]
        for row in rows
        for sample in row["paired_samples"]
    )

    independent_total_ns = sum(
        sample["independent_ns"]
        for row in rows
        for sample in row["paired_samples"]
    )

    report = {
        "schema_version": 1,
        "benchmark_id": "P2-CANONICAL-4Q-PAIRED-OPERATIONS",
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

        "total_runtime_seconds": 0.0,
        "runtime_measurement_scope": RUNTIME_SCOPE,

        "production_total_execution_seconds": (
            production_total_ns / 1_000_000_000.0
        ),
        "independent_total_execution_seconds": (
            independent_total_ns / 1_000_000_000.0
        ),
        "combined_timed_execution_seconds": (
            (production_total_ns + independent_total_ns)
            / 1_000_000_000.0
        ),
        "initial_evidence_generation_seconds": 0.0,

        "environment": environment,

        "independent_reference": {
            "method": (
                "Independent Kronecker RY construction, independent "
                "C3X permutation, direct state evolution, outer-product "
                "density matrix and tensor partial traces."
            ),
            "used_for_timed_operation_checks": True,
            "paired_measurement": True,
            "execution_order": "Alternating production-first and independent-first.",
        },

        "pennylane_numpy_maximum_difference": parity_error,
        "literature_benchmarks": LITERATURE_BENCHMARKS,
        "world_record_policy": (
            "A world-record value is populated only for an independently "
            "verified, directly comparable published measurement. "
            "No such measurement is currently established for the exact "
            "P2 operation-level workload."
        ),

        "operations": rows,
        "all_checks_pass": all_passed,
        "status": "PASS" if all_passed else "FAIL",

        "limitations": [
            "Only the canonical four-qubit P2 instance is measured.",
            "The Hilbert-space dimension is 16.",
            "The results do not establish asymptotic scalability.",
            "The results do not establish million-qubit or HPC performance.",
            "The paired comparison is limited to the declared implementations.",
            "Published results with different circuits or hardware are not equivalent records.",
            "Benchmark results are supplementary evidence, not a substitute for mathematical validation.",
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / JSON_FILENAME
    csv_path = output_dir / CSV_FILENAME
    markdown_path = output_dir / MARKDOWN_FILENAME
    environment_path = output_dir / ENVIRONMENT_FILENAME

    # Measure the first evidence-generation pass separately.
    evidence_start_ns = time.perf_counter_ns()

    write_csv(csv_path, rows)
    write_json(json_path, report)

    environment_path.write_text(
        environment_text(environment),
        encoding="utf-8",
    )

    evidence_elapsed_ns = (
        time.perf_counter_ns() - evidence_start_ns
    )

    report["initial_evidence_generation_seconds"] = (
        evidence_elapsed_ns / 1_000_000_000.0
    )

    markdown_path.write_text(
        markdown_report(report),
        encoding="utf-8",
    )

    elapsed_ns = time.perf_counter_ns() - started_ns

    report["total_runtime_seconds"] = (
        elapsed_ns / 1_000_000_000.0
    )

    if (
        not np.isfinite(report["total_runtime_seconds"])
        or report["total_runtime_seconds"] <= 0
    ):
        raise ArithmeticError(
            "Total benchmark runtime is not positive."
        )

    # Final JSON and Markdown persistence is excluded from the measured
    # total runtime to avoid a self-referential timing interval.
    write_json(json_path, report)

    markdown_path.write_text(
        markdown_report(report),
        encoding="utf-8",
    )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the canonical QFLPN P2 paired benchmark."
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
        help="Directory for the four benchmark evidence files.",
    )

    args = parser.parse_args()

    started_ns = time.perf_counter_ns()

    try:
        config = load_config(
            args.config.resolve(strict=True)
        )

        report = run_benchmark(
            config,
            args.output.resolve(),
            started_ns=started_ns,
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

    print(
        "Production total execution time: "
        f"{report['production_total_execution_seconds']:.9f} seconds"
    )

    print(
        "Independent total execution time: "
        f"{report['independent_total_execution_seconds']:.9f} seconds"
    )

    print(
        "Combined timed execution time: "
        f"{report['combined_timed_execution_seconds']:.9f} seconds"
    )

    print(
        "Total benchmark runtime: "
        f"{report['total_runtime_seconds']:.6f} seconds"
    )

    print(
        "VERDICT:",
        (
            "BENCHMARK_COMPLETED"
            if report["status"] == "PASS"
            else "BENCHMARK_FAILED"
        ),
    )

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
