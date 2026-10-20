"""Reproducible numerical-operation benchmark for QFLPN P2."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pennylane as qml

P2_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = P2_ROOT.parent
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

CONFIG_PATH = P2_ROOT / "benchmarks" / "benchmark_config.json"
DEFAULT_OUTPUT = P2_ROOT / "benchmarks" / "results"


def load_config(path: Path) -> dict:
    """Load and validate the benchmark configuration."""

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError("Benchmark configuration must be an object.")

    if data.get("schema_version") != 1:
        raise ValueError("Unsupported benchmark schema.")

    if data.get("qubits") != 4:
        raise ValueError("P2 benchmark requires four qubits.")

    if data.get("hilbert_dimension") != 16:
        raise ValueError("P2 benchmark dimension must be 16.")

    if data.get("basis_order") != "big-endian":
        raise ValueError("Unsupported basis order.")

    if data.get("operator_order") != "U = C3X @ U_rot":
        raise ValueError("Unexpected operator order.")

    activations = data.get("activation_vector")

    if activations != list(DEFAULT_ACTIVATIONS):
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

    return data


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
    """Build the PennyLane circuit corresponding to the P2 convention."""

    device = qml.device(
        "default.qubit",
        wires=4,
    )

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


def matrix_error(actual: np.ndarray, expected: np.ndarray) -> float:
    """Return a finite Frobenius-norm comparison error."""

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
    function,
    expected: np.ndarray,
    warmups: int,
    repetitions: int,
    tolerance: float,
) -> dict:
    """Warm up, validate, and measure one numerical operation."""

    for _ in range(warmups):
        function()

    reference_result = function()
    error = matrix_error(
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

        if not np.all(np.isfinite(np.asarray(result))):
            passed = False

    return {
        "operation": name,
        "warmups": warmups,
        "repetitions": repetitions,
        "minimum_ns": min(durations),
        "median_ns": float(statistics.median(durations)),
        "mean_ns": float(statistics.mean(durations)),
        "maximum_ns": max(durations),
        "standard_deviation_ns": float(
            statistics.pstdev(durations)
        ),
        "numerical_error": error,
        "numerical_tolerance": tolerance,
        "passed": passed,
    }


def build_operations(activations: tuple[float, ...]) -> list[tuple]:
    """Build operation callables and independent expected results."""

    u_rot = rotation_operator(activations)
    c3x = c3x_operator()
    operator = transition_operator(activations)

    state = reference_state(activations)
    rho = density_matrix(state)

    rho_q4 = reduced_density_q4(state)
    rho_q123 = reduced_density_q123(state)

    pennylane_circuit = make_pennylane_circuit()

    pennylane_state = np.asarray(
        pennylane_circuit(activations),
        dtype=np.complex128,
    )

    return [
        (
            "rotation_operator",
            lambda: rotation_operator(activations),
            u_rot,
        ),
        (
            "c3x_operator",
            c3x_operator,
            c3x,
        ),
        (
            "transition_operator",
            lambda: transition_operator(activations),
            operator,
        ),
        (
            "state_evolution",
            lambda: transition_operator(activations)
            @ initial_state(),
            state,
        ),
        (
            "density_matrix",
            lambda: density_matrix(state),
            rho,
        ),
        (
            "reduced_density_q4",
            lambda: reduced_density_q4(state),
            rho_q4,
        ),
        (
            "reduced_density_q123",
            lambda: reduced_density_q123(state),
            rho_q123,
        ),
        (
            "pennylane_execution",
            lambda: np.asarray(
                pennylane_circuit(activations),
                dtype=np.complex128,
            ),
            state,
        ),
    ], pennylane_state


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("No benchmark rows were produced.")

    fieldnames = list(rows[0])

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def run_benchmark(
    config: dict,
    output_dir: Path,
) -> dict:
    """Run the configured P2 benchmark and write evidence."""

    activations = tuple(
        float(value)
        for value in config["activation_vector"]
    )

    warmups = config["warmups"]
    repetitions = config["repetitions"]
    tolerance = float(config["numerical_tolerance"])

    operations, pennylane_state = build_operations(activations)

    canonical_state = reference_state(activations)
    parity_error = matrix_error(
        pennylane_state,
        canonical_state,
    )

    rows = [
        time_operation(
            name,
            function,
            expected,
            warmups,
            repetitions,
            tolerance,
        )
        for name, function, expected in operations
    ]

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = output_dir / config["csv_filename"]
    json_path = output_dir / config["json_filename"]

    write_csv(csv_path, rows)

    all_passed = all(
        row["passed"]
        for row in rows
    )

    report = {
        "schema_version": 1,
        "project": "QFLPN P2",
        "qubits": 4,
        "hilbert_dimension": 16,
        "basis_order": "big-endian",
        "activation_vector": list(activations),
        "operator_order": "U = C3X @ U_rot",
        "warmups": warmups,
        "repetitions": repetitions,
        "timer": "time.perf_counter_ns",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pennylane": qml.__version__,
        },
        "pennylane_numpy_maximum_difference": parity_error,
        "numerical_tolerance": tolerance,
        "operations": rows,
        "all_checks_pass": bool(
            all_passed and parity_error <= tolerance
        ),
        "status": (
            "PASS"
            if all_passed and parity_error <= tolerance
            else "FAIL"
        ),
    }

    json_path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the canonical P2 numerical benchmark."
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
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
    ) as exc:
        print("FAIL:", exc)
        return 2

    print("Benchmark output:", args.output.resolve())
    print("Operations:", len(report["operations"]))
    print("Warmups:", report["warmups"])
    print("Repetitions:", report["repetitions"])
    print(
        "PennyLane / NumPy difference:",
        f"{report['pennylane_numpy_maximum_difference']:.3e}",
    )
    print("Status:", report["status"])

    if report["status"] != "PASS":
        print("VERDICT: BENCHMARK_REJECTED")
        return 1

    print("VERDICT: BENCHMARK_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
