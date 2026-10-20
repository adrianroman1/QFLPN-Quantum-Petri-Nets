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
    """Return a CPU model string where the host exposes one."""

    cpuinfo = Path("/proc/cpuinfo")

    if cpuinfo.is_file():
        try:
            for line in cpuinfo.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines():
                if line.lower().startswith(
                    ("model name", "hardware", "processor")
                ):
                    _, separator, value = line.partition(":")
                    if separator and value.strip():
                        return value.strip()
        except OSError:
            pass

    processor = platform.processor().strip()

    if processor:
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
