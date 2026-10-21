"""Single source of truth for the P2 benchmark configuration and artifacts.

This module deliberately contains configuration and path-contract logic only.
It does not implement benchmark execution, timing, report generation, or
evidence validation.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


P2_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = P2_ROOT / "benchmarks"
DEFAULT_CONFIG_PATH = BENCHMARK_DIR / "benchmark_config.json"

EXPECTED_SCHEMA_VERSION = 1
EXPECTED_PROJECT = "QFLPN P2"
EXPECTED_QUBITS = 4
EXPECTED_HILBERT_DIMENSION = 16
EXPECTED_BASIS_ORDER = "big-endian"
EXPECTED_OPERATOR_ORDER = "U = C3X @ U_rot"
EXPECTED_TIMER = "time.perf_counter_ns"

EXPECTED_ACTIVATION_VECTOR = (0.85, 0.90, 0.45, 0.70)

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

REQUIRED_CONFIG_KEYS = frozenset(
    {
        "schema_version",
        "project",
        "description",
        "qubits",
        "hilbert_dimension",
        "basis_order",
        "activation_vector",
        "operator_order",
        "warmups",
        "repetitions",
        "numerical_tolerance",
        "timer",
        "operations",
        "output_directory",
        "artifacts",
    }
)

REQUIRED_ARTIFACT_KEYS = frozenset(
    {
        "json",
        "csv",
        "markdown",
        "environment",
    }
)


@dataclass(frozen=True)
class BenchmarkContract:
    """Validated, resolved benchmark configuration.

    `config` contains the validated declarative configuration.
    `output_directory` is always an absolute, resolved path.
    `artifacts` maps the four artifact types to their configured filenames.
    `artifact_paths` maps the same types to absolute output paths.
    """

    config_path: Path
    p2_root: Path
    config: dict[str, Any]
    output_directory: Path
    artifacts: dict[str, str]
    artifact_paths: dict[str, Path]

    @property
    def json_path(self) -> Path:
        return self.artifact_paths["json"]

    @property
    def csv_path(self) -> Path:
        return self.artifact_paths["csv"]

    @property
    def markdown_path(self) -> Path:
        return self.artifact_paths["markdown"]

    @property
    def environment_path(self) -> Path:
        return self.artifact_paths["environment"]


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Invalid benchmark configuration: '{field}' "
            "must be a non-empty string."
        )

    if value != value.strip():
        raise ValueError(
            f"Invalid benchmark configuration: '{field}' "
            "must not contain leading or trailing whitespace."
        )

    return value


def _validate_output_directory(value: Any) -> str:
    raw_value = _require_nonempty_string(value, "output_directory")
    candidate = Path(raw_value)

    if candidate.is_absolute():
        raise ValueError(
            "Invalid benchmark configuration: 'output_directory' "
            "must be relative to P2_ROOT."
        )

    if any(part == ".." for part in candidate.parts):
        raise ValueError(
            "Invalid benchmark configuration: 'output_directory' "
            "must not contain parent-directory traversal."
        )

    if raw_value in {".", ".."}:
        raise ValueError(
            "Invalid benchmark configuration: 'output_directory' "
            "must identify a dedicated output directory."
        )

    return raw_value


def _validate_artifact_filename(value: Any, artifact_type: str) -> str:
    filename = _require_nonempty_string(
        value,
        f"artifacts.{artifact_type}",
    )

    candidate = Path(filename)

    if (
        candidate.is_absolute()
        or len(candidate.parts) != 1
        or filename in {".", ".."}
        or "/" in filename
        or "\\" in filename
    ):
        raise ValueError(
            f"Invalid benchmark configuration: "
            f"'artifacts.{artifact_type}' must be a filename, "
            "not a path."
        )

    return filename


def _validate_artifacts(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(
            "Invalid benchmark configuration: 'artifacts' "
            "must be a JSON object."
        )

    actual_keys = set(value)

    missing = REQUIRED_ARTIFACT_KEYS - actual_keys
    unexpected = actual_keys - REQUIRED_ARTIFACT_KEYS

    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(
            "Invalid benchmark configuration: missing artifact keys: "
            f"{names}."
        )

    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise ValueError(
            "Invalid benchmark configuration: unexpected artifact keys: "
            f"{names}."
        )

    artifacts = {
        artifact_type: _validate_artifact_filename(
            value[artifact_type],
            artifact_type,
        )
        for artifact_type in sorted(REQUIRED_ARTIFACT_KEYS)
    }

    normalized_names = [
        filename.casefold()
        for filename in artifacts.values()
    ]

    if len(normalized_names) != len(set(normalized_names)):
        raise ValueError(
            "Invalid benchmark configuration: artifact filenames "
            "must be unique."
        )

    # Preserve the public, documented artifact key order.
    return {
        "json": artifacts["json"],
        "csv": artifacts["csv"],
        "markdown": artifacts["markdown"],
        "environment": artifacts["environment"],
    }


def validate_config_data(data: Any) -> dict[str, Any]:
    """Validate the complete P2 benchmark configuration.

    This function is the only implementation of the configuration schema.
    It returns the original dictionary after successful validation.
    """

    if not isinstance(data, dict):
        raise ValueError(
            "Benchmark configuration must be a JSON object."
        )

    actual_keys = set(data)
    missing = REQUIRED_CONFIG_KEYS - actual_keys
    unexpected = actual_keys - REQUIRED_CONFIG_KEYS

    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(
            "Invalid benchmark configuration: missing keys: "
            f"{names}."
        )

    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise ValueError(
            "Invalid benchmark configuration: unexpected keys: "
            f"{names}."
        )

    if (
        type(data["schema_version"]) is not int
        or data["schema_version"] != EXPECTED_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported benchmark configuration schema."
        )

    if data["project"] != EXPECTED_PROJECT:
        raise ValueError("Unexpected benchmark project.")

    _require_nonempty_string(data["description"], "description")

    if (
        type(data["qubits"]) is not int
        or data["qubits"] != EXPECTED_QUBITS
    ):
        raise ValueError("P2 benchmark requires four qubits.")

    if (
        type(data["hilbert_dimension"]) is not int
        or data["hilbert_dimension"] != EXPECTED_HILBERT_DIMENSION
    ):
        raise ValueError("P2 benchmark dimension must be 16.")

    if data["basis_order"] != EXPECTED_BASIS_ORDER:
        raise ValueError("Unsupported basis ordering.")

    if data["operator_order"] != EXPECTED_OPERATOR_ORDER:
        raise ValueError("Unexpected operator ordering.")

    activations = data["activation_vector"]

    if (
        not isinstance(activations, list)
        or len(activations) != len(EXPECTED_ACTIVATION_VECTOR)
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in activations
        )
        or tuple(float(value) for value in activations)
        != EXPECTED_ACTIVATION_VECTOR
    ):
        raise ValueError(
            "Benchmark activations differ from the canonical P2 model."
        )

    warmups = data["warmups"]

    if type(warmups) is not int or warmups < 5:
        raise ValueError(
            "At least five warm-up iterations are required."
        )

    repetitions = data["repetitions"]

    if type(repetitions) is not int or repetitions < 30:
        raise ValueError(
            "At least 30 measured repetitions are required."
        )

    tolerance = data["numerical_tolerance"]

    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not math.isfinite(tolerance)
        or tolerance <= 0
    ):
        raise ValueError("Invalid numerical tolerance.")

    if data["operations"] != list(EXPECTED_OPERATIONS):
        raise ValueError(
            "Configured benchmark operations do not match "
            "the required P2 operation set."
        )

    if data["timer"] != EXPECTED_TIMER:
        raise ValueError("Unsupported benchmark timer.")

    _validate_output_directory(data["output_directory"])
    _validate_artifacts(data["artifacts"])

    return data


def load_benchmark_contract(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    p2_root: str | Path = P2_ROOT,
) -> BenchmarkContract:
    """Load, validate, and resolve the canonical benchmark contract.

    Relative output directories are always resolved against `p2_root`.
    The process working directory never determines the artifact location.
    """

    root = Path(p2_root).expanduser().resolve()
    source = Path(config_path).expanduser()

    if not source.is_absolute():
        source = source.resolve()

    source = source.resolve()

    try:
        raw_text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"Cannot read benchmark configuration: {source}"
        ) from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Benchmark configuration is not valid JSON "
            f"(line {exc.lineno}, column {exc.colno})."
        ) from exc

    validated = validate_config_data(data)

    output_relative = _validate_output_directory(
        validated["output_directory"]
    )
    output_directory = (root / output_relative).resolve()

    try:
        output_directory.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            "Resolved benchmark output directory must remain "
            "inside P2_ROOT."
        ) from exc

    artifacts = _validate_artifacts(validated["artifacts"])

    artifact_paths = {
        artifact_type: output_directory / filename
        for artifact_type, filename in artifacts.items()
    }

    return BenchmarkContract(
        config_path=source,
        p2_root=root,
        config=validated,
        output_directory=output_directory,
        artifacts=artifacts,
        artifact_paths=artifact_paths,
    )


def assert_cli_output_directory(
    cli_directory: str | Path | None,
    contract: BenchmarkContract,
    *,
    option_name: str,
) -> Path:
    """Treat a CLI directory as a consistency assertion, never an override.

    A relative CLI path is interpreted relative to the current process
    directory, matching normal command-line path semantics. It must resolve
    to exactly the directory selected by the canonical configuration.
    """

    if option_name not in {"--output", "--results"}:
        raise ValueError(
            "Unsupported benchmark directory option."
        )

    if cli_directory is None:
        return contract.output_directory

    raw_value = str(cli_directory)

    if not raw_value.strip():
        raise ValueError(
            f"{option_name} must not be empty."
        )

    supplied = Path(cli_directory).expanduser().resolve()
    expected = contract.output_directory.resolve()

    if supplied != expected:
        raise ValueError(
            f"{option_name} directory does not match the "
            "configured output_directory: "
            f"expected '{expected}', received '{supplied}'."
        )

    return expected
