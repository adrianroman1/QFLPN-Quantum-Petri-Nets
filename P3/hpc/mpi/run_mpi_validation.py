#!/usr/bin/env python3
"""Fail-closed MPI validation for P3 distributed CSR SpMV.

This is a multi-process correctness smoke test. It is not evidence of
multi-node scaling or HPC performance.

The JSON report preserves the original v1 fields and adds explicit process
outcome, command, launcher metadata, duration, and comparison-execution
evidence. A process exit status is never confused with a signal number.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA = "qflqn-p3-mpi-validation-v1"
REPOSITORY = "adrianroman1/QFLPN-Quantum-Petri-Nets"

SOURCE_RELATIVE = Path("P3/hpc/mpi/native/p3_mpi_spmv.c")
EXECUTABLE_RELATIVE = Path("P3/target/mpi/p3_mpi_spmv")
REQUEST_RELATIVE = Path("P3/target/mpi/mpi-smoke-request.p3mpi")
RESPONSE_RELATIVE = Path("P3/target/mpi/mpi-smoke-response.p3mpi")

REPORT_RELATIVE = Path("P3/reports/mpi-validation.json")
STDOUT_RELATIVE = Path("P3/reports/mpi-stdout.log")
STDERR_RELATIVE = Path("P3/reports/mpi-stderr.log")
BUILD_LOG_RELATIVE = Path("P3/reports/mpi-build.log")

INPUT_MAGIC = b"P3SPMV01"
OUTPUT_MAGIC = b"P3OUT001"

ABSOLUTE_TOLERANCE = 1.0e-12
RELATIVE_TOLERANCE = 1.0e-10

DEFAULT_ROWS = 128
DEFAULT_COLUMNS = 128
DEFAULT_TIMEOUT_SECONDS = 180


class ValidationError(RuntimeError):
    """A mandatory MPI validation condition was not satisfied."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def validate_provenance(
    run_id: str,
    source_commit: str,
    workflow_run_id: str,
    workflow_run_attempt: str = "1",
) -> None:
    require(
        isinstance(run_id, str)
        and bool(run_id.strip())
        and run_id == run_id.strip()
        and all(c.isalnum() or c in "._-" for c in run_id),
        "P3_RUN_ID is missing or invalid.",
    )
    require(
        isinstance(source_commit, str)
        and len(source_commit) == 40
        and all(c in "0123456789abcdef" for c in source_commit),
        "Source commit must be a 40-character lowercase hexadecimal SHA.",
    )
    require(
        isinstance(workflow_run_id, str) and workflow_run_id.isdigit(),
        "GITHUB_RUN_ID must contain decimal digits only.",
    )
    require(
        isinstance(workflow_run_attempt, str)
        and workflow_run_attempt.isdigit()
        and int(workflow_run_attempt) >= 1,
        "GITHUB_RUN_ATTEMPT must be a positive integer.",
    )


def build_test_matrix(
    rows: int,
    columns: int,
) -> tuple[list[int], list[int], list[float], list[float]]:
    require(rows >= 2, "Smoke matrix must contain at least two rows.")
    require(columns >= 3, "Smoke matrix must contain at least three columns.")

    row_ptr = [0]
    column_indices: list[int] = []
    values: list[float] = []
    vector = [((i % 17) - 8) / 8.0 for i in range(columns)]

    for row in range(rows):
        candidates = sorted({
            row % columns,
            (row + 1) % columns,
            (row + 7) % columns,
        })
        for position, column in enumerate(candidates):
            column_indices.append(column)
            numerator = ((row * 5 + position * 3) % 19) - 9
            values.append(numerator / 16.0)
        row_ptr.append(len(column_indices))

    require(row_ptr[0] == 0, "CSR row_ptr must start at zero.")
    require(row_ptr[-1] == len(column_indices), "CSR NNZ endpoint mismatch.")
    require(
        all(a <= b for a, b in zip(row_ptr, row_ptr[1:])),
        "CSR row_ptr is not monotonic.",
    )
    require(
        all(0 <= col < columns for col in column_indices),
        "CSR column index is out of range.",
    )
    require(
        all(math.isfinite(x) for x in values + vector),
        "Generated input contains non-finite values.",
    )
    return row_ptr, column_indices, values, vector


def validate_csr(
    rows: int,
    columns: int,
    row_ptr: list[int],
    column_indices: list[int],
    values: list[float],
    vector: list[float],
) -> None:
    nnz = len(column_indices)
    require(rows >= 1 and columns >= 1, "CSR dimensions must be positive.")
    require(len(row_ptr) == rows + 1, "CSR row_ptr length mismatch.")
    require(len(values) == nnz, "CSR values and indices length mismatch.")
    require(len(vector) == columns, "Input vector length mismatch.")
    require(row_ptr[0] == 0 and row_ptr[-1] == nnz, "CSR endpoints invalid.")
    require(
        all(a <= b for a, b in zip(row_ptr, row_ptr[1:])),
        "CSR row_ptr must be monotonic.",
    )
    require(
        all(0 <= col < columns for col in column_indices),
        "CSR column index out of range.",
    )
    require(
        all(math.isfinite(x) for x in values + vector),
        "CSR input contains non-finite values.",
    )


def encode_request(
    rows: int,
    columns: int,
    row_ptr: list[int],
    column_indices: list[int],
    values: list[float],
    vector: list[float],
) -> bytes:
    validate_csr(rows, columns, row_ptr, column_indices, values, vector)
    nnz = len(column_indices)
    header = struct.pack(
        "<8s6Q", INPUT_MAGIC, rows, columns, nnz, len(vector), 0, 0
    )
    return b"".join((
        header,
        struct.pack(f"<{len(row_ptr)}Q", *row_ptr),
        struct.pack(f"<{nnz}Q", *column_indices) if nnz else b"",
        struct.pack(f"<{nnz}d", *values) if nnz else b"",
        struct.pack(f"<{columns}d", *vector),
    ))


def decode_response(path: Path, expected_rows: int) -> list[float]:
    require(
        path.is_file() and not path.is_symlink(),
        "MPI response file is missing or unsafe.",
    )
    payload = path.read_bytes()
    require(len(payload) >= 32, "MPI response header is truncated.")

    magic, rows, status, reserved = struct.unpack("<8s3Q", payload[:32])
    require(magic == OUTPUT_MAGIC, "MPI response magic is invalid.")
    require(rows == expected_rows, "MPI response row count mismatch.")
    require(status == 0, "MPI response reports a non-zero status.")
    require(reserved == 0, "MPI response reserved field is non-zero.")

    expected_length = 32 + expected_rows * 8
    require(
        len(payload) == expected_length,
        "MPI response payload length is invalid.",
    )
    result = (
        list(struct.unpack(f"<{expected_rows}d", payload[32:]))
        if expected_rows else []
    )
    require(
        all(math.isfinite(value) for value in result),
        "MPI response contains non-finite values.",
    )
    return result


def sequential_csr_reference(
    rows: int,
    row_ptr: list[int],
    column_indices: list[int],
    values: list[float],
    vector: list[float],
) -> list[float]:
    require(len(row_ptr) == rows + 1, "Reference row_ptr length mismatch.")
    require(len(column_indices) == len(values), "Reference NNZ mismatch.")
    result: list[float] = []

    for row in range(rows):
        total = 0.0
        for index in range(row_ptr[row], row_ptr[row + 1]):
            total += values[index] * vector[column_indices[index]]
        require(math.isfinite(total), "Sequential reference is non-finite.")
        result.append(total)
    return result


def compare_results(
    actual: list[float],
    reference: list[float],
) -> dict[str, float]:
    """Return measured errors, raising only for invalid/non-finite inputs.

    A tolerance mismatch is represented by comparison_passed=False by the
    caller; measured error values are retained in the report.
    """
    require(len(actual) == len(reference), "Result vector lengths differ.")

    max_abs = 0.0
    max_rel = 0.0
    max_reference = 0.0

    for observed, expected in zip(actual, reference):
        require(
            math.isfinite(observed) and math.isfinite(expected),
            "Numerical comparison contains a non-finite value.",
        )
        absolute_error = abs(observed - expected)
        magnitude = abs(expected)
        relative_error = absolute_error / max(
            magnitude, ABSOLUTE_TOLERANCE
        )
        max_abs = max(max_abs, absolute_error)
        max_rel = max(max_rel, relative_error)
        max_reference = max(max_reference, magnitude)

    require(math.isfinite(max_rel), "Relative error is not finite.")
    return {
        "max_absolute_error": max_abs,
        "max_relative_error": max_rel,
        "max_reference_magnitude": max_reference,
    }


def comparison_passes(metrics: dict[str, float]) -> bool:
    """Check the mixed absolute/relative tolerance using measured errors.

    max_relative_error is diagnostic. Acceptance is evaluated componentwise
    in compare_results_with_status(), which retains the error metrics.
    """
    return bool(metrics.get("comparison_passed", False))


def compare_results_with_status(
    actual: list[float],
    reference: list[float],
) -> tuple[dict[str, float], bool]:
    metrics = compare_results(actual, reference)
    passed = len(actual) == len(reference)

    for observed, expected in zip(actual, reference):
        allowed = ABSOLUTE_TOLERANCE + RELATIVE_TOLERANCE * abs(expected)
        if abs(observed - expected) > allowed:
            passed = False

    return metrics, passed


def resolve_tool(value: str, label: str) -> str:
    found = shutil.which(value)
    require(found is not None, f"{label} not found on PATH: {value}")
    return str(Path(found).resolve())


def run_command(
    command: list[str],
    timeout_seconds: int,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        env=environment,
    )


def command_version(command: list[str], environment: dict[str, str]) -> str:
    try:
        result = run_command(command, 20, environment)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValidationError(
            f"Could not obtain version for {shlex.join(command)}: {exc}"
        ) from exc

    output = (result.stdout + "\n" + result.stderr).strip()
    require(
        result.returncode == 0 and bool(output),
        f"Version command failed: {shlex.join(command)}",
    )
    return output[:4000]


def _signal_name(number: int | None) -> str | None:
    if number is None:
        return None
    try:
        return signal.Signals(number).name
    except ValueError:
        return f"SIG{number}"


def _process_outcome(
    returncode: int | None,
    timed_out: bool,
    launch_error: str | None,
    not_run: bool = False,
) -> dict[str, Any]:
    if not_run:
        return {
            "type": "NOT_RUN",
            "exit_code": None,
            "signal": None,
            "signal_name": None,
            "returncode": None,
        }
    if timed_out:
        return {
            "type": "TIMEOUT",
            "exit_code": None,
            "signal": None,
            "signal_name": None,
            "returncode": returncode,
        }
    if launch_error is not None:
        return {
            "type": "LAUNCH_ERROR",
            "exit_code": None,
            "signal": None,
            "signal_name": None,
            "returncode": None,
        }
    if returncode is None:
        return {
            "type": "NOT_RUN",
            "exit_code": None,
            "signal": None,
            "signal_name": None,
            "returncode": None,
        }
    if returncode < 0:
        number = -returncode
        return {
            "type": "SIGNAL",
            "exit_code": None,
            "signal": number,
            "signal_name": _signal_name(number),
            "returncode": returncode,
        }
    return {
        "type": "EXIT_CODE",
        "exit_code": returncode,
        "signal": None,
        "signal_name": None,
        "returncode": returncode,
    }


def _launcher_metadata(
    launcher_tokens: list[str],
    environment: dict[str, str],
) -> dict[str, Any]:
    path = launcher_tokens[0] if launcher_tokens else None
    version = None
    version_error = None
    if path:
        try:
            version = command_version([path, "--version"], environment)
        except (ValidationError, OSError, subprocess.TimeoutExpired) as exc:
            version_error = f"{type(exc).__name__}: {exc}"
    return {
        "configured": shlex.join(launcher_tokens) if launcher_tokens else None,
        "path": path,
        "version": version,
        "version_error": version_error,
    }


def make_report(
    *,
    run_id: str,
    source_commit: str,
    workflow_run_id: str,
    compiler: str,
    compiler_version: str,
    executable: str,
    executable_sha256: str,
    build_exit_code: int,
    launcher: str,
    process_count: int,
    execution_exit_code: int,
    skipped: bool,
    timed_out: bool,
    rows: int,
    columns: int,
    nnz: int,
    comparison: dict[str, Any],
    validation: str,
    workflow_run_attempt: str = "1",
    execution_outcome: dict[str, Any] | None = None,
    execution_command: list[str] | None = None,
    execution_duration_seconds: float | None = None,
    launcher_metadata: dict[str, Any] | None = None,
    comparison_executed: bool | None = None,
    comparison_passed: bool | None = None,
    launch_error: str | None = None,
) -> dict[str, Any]:
    """Build the stable report contract consumed by verify_final_package.py."""
    build_ok = build_exit_code == 0 and bool(executable_sha256)
    if execution_outcome is None:
        execution_outcome = _process_outcome(
            execution_exit_code, timed_out, launch_error
        )
    if comparison_executed is None:
        comparison_executed = bool(comparison)
    if comparison_passed is None:
        comparison_passed = (
            validation == "PASS" and comparison_executed
        )

    outcome_type = execution_outcome["type"]
    execution_ok = (
        outcome_type == "EXIT_CODE"
        and execution_outcome.get("exit_code") == 0
        and not skipped
        and process_count >= 2
    )
    numerical_ok = (
        validation == "PASS"
        and execution_ok
        and build_ok
        and comparison_executed
        and comparison_passed
    )

    def metric(name: str) -> float | None:
        if not comparison_executed:
            return None
        value = comparison.get(name)
        return float(value) if value is not None else None

    return {
        "schema": SCHEMA,
        "validation": "PASS" if numerical_ok else "FAIL",
        "run_id": run_id,
        "source_commit": source_commit,
        "workflow_run_id": workflow_run_id,
        "workflow_run_attempt": (
            int(workflow_run_attempt)
            if workflow_run_attempt.isdigit() else 0
        ),
        "repository": REPOSITORY,
        "native_build": {
            "status": "PASS" if build_ok else "FAIL",
            "compiler": "mpicc",
            "compiler_path": compiler or None,
            "compiler_version": compiler_version or None,
            "source_file": SOURCE_RELATIVE.as_posix(),
            "executable": executable,
            "executable_sha256": executable_sha256 or None,
            "exit_code": build_exit_code,
        },
        "execution": {
            "status": "PASS" if execution_ok else "FAIL",
            "launcher": launcher or None,
            "process_count": process_count,
            # Retain legacy exit_code; use null for signal/timeout/launch error.
            "exit_code": execution_outcome.get("exit_code"),
            "returncode": execution_outcome.get("returncode"),
            "outcome_type": outcome_type,
            "signal": execution_outcome.get("signal"),
            "signal_name": execution_outcome.get("signal_name"),
            "skipped": skipped,
            "timeout": timed_out,
            "duration_seconds": execution_duration_seconds,
            "command": execution_command,
            "launcher_metadata": launcher_metadata or {},
            "launch_error": launch_error,
            "stdout_file": STDOUT_RELATIVE.as_posix(),
            "stderr_file": STDERR_RELATIVE.as_posix(),
            "build_log_file": BUILD_LOG_RELATIVE.as_posix(),
        },
        "numerical_validation": {
            "status": "PASS" if numerical_ok else "FAIL",
            "reference": "sequential_csr",
            "rows": rows,
            "columns": columns,
            "nnz": nnz,
            "comparison_executed": comparison_executed,
            "comparison": (
                "PASS" if comparison_executed and comparison_passed
                else "FAIL" if comparison_executed
                else "NOT_RUN"
            ),
            "max_absolute_error": metric("max_absolute_error"),
            "max_relative_error": metric("max_relative_error"),
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "relative_tolerance": RELATIVE_TOLERANCE,
            "max_reference_magnitude": metric("max_reference_magnitude"),
        },
        "provenance": {
            "commit_verified": (
                len(source_commit) == 40
                and all(c in "0123456789abcdef" for c in source_commit)
            ),
            "run_id_verified": bool(run_id.strip()),
            "workflow_run_id_verified": workflow_run_id.isdigit(),
        },
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile and run the P3 native MPI SpMV validation."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--processes", type=int, default=2)
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    parser.add_argument("--columns", type=int, default=DEFAULT_COLUMNS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    root = Path(args.root).resolve()

    run_id = os.environ.get("P3_RUN_ID", "")
    source_commit = (
        os.environ.get("P3_SOURCE_COMMIT") or os.environ.get("GITHUB_SHA", "")
    )
    workflow_run_id = (
        os.environ.get("P3_WORKFLOW_RUN_ID")
        or os.environ.get("GITHUB_RUN_ID", "")
    )
    workflow_run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")

    report_path = root / REPORT_RELATIVE
    stdout_path = root / STDOUT_RELATIVE
    stderr_path = root / STDERR_RELATIVE
    build_log_path = root / BUILD_LOG_RELATIVE
    source_path = root / SOURCE_RELATIVE
    executable_path = root / EXECUTABLE_RELATIVE
    request_path = root / REQUEST_RELATIVE
    response_path = root / RESPONSE_RELATIVE

    compiler_path = ""
    compiler_version = ""
    launcher_tokens: list[str] = []
    launcher_display = ""
    launcher_metadata: dict[str, Any] = {}
    executable_digest = ""
    build_exit_code = 1
    execution_returncode: int | None = None
    execution_outcome = _process_outcome(None, False, None, not_run=True)
    execution_command: list[str] | None = None
    execution_duration: float | None = None
    launch_error: str | None = None
    skipped = False
    build_timed_out = False
    execution_timed_out = False

    rows = args.rows
    columns = args.columns
    nnz = 0
    comparison: dict[str, float] = {}
    comparison_executed = False
    comparison_passed = False
    build_output = ""
    execution_stdout = ""
    execution_stderr = ""
    validation = "FAIL"
    environment = os.environ.copy()
    environment.setdefault("OMPI_ALLOW_RUN_AS_ROOT", "1")
    environment.setdefault("OMPI_ALLOW_RUN_AS_ROOT_CONFIRM", "1")

    try:
        require(root.is_dir(), f"Repository root does not exist: {root}")
        require(args.processes >= 2, "--processes must be at least 2.")
        require(args.timeout > 0, "--timeout must be positive.")
        require(rows >= 2 and columns >= 3, "Invalid smoke matrix dimensions.")
        validate_provenance(
            run_id, source_commit, workflow_run_id, workflow_run_attempt
        )
        require(
            source_path.is_file() and not source_path.is_symlink(),
            f"Native MPI source is missing or unsafe: {SOURCE_RELATIVE}",
        )

        compiler_path = resolve_tool(
            os.environ.get("MPICC", "mpicc"), "MPI C compiler"
        )
        compiler_version = command_version(
            [compiler_path, "--version"], environment
        )

        launcher_tokens = shlex.split(
            os.environ.get("P3_MPI_LAUNCHER", "mpirun")
        )
        require(bool(launcher_tokens), "P3_MPI_LAUNCHER is empty.")
        launcher_tokens[0] = resolve_tool(
            launcher_tokens[0], "MPI launcher"
        )
        launcher_display = shlex.join(launcher_tokens)
        launcher_metadata = _launcher_metadata(launcher_tokens, environment)

        executable_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.parent.mkdir(parents=True, exist_ok=True)
        response_path.parent.mkdir(parents=True, exist_ok=True)

        compile_command = [
            compiler_path, "-std=c11", "-O2", "-Wall", "-Wextra",
            "-Wpedantic", "-Wconversion", "-Wshadow",
            str(source_path), "-o", str(executable_path), "-lm",
        ]
        try:
            result = run_command(compile_command, args.timeout, environment)
            build_exit_code = result.returncode
            build_output = (
                "$ " + shlex.join(compile_command)
                + "\nSTDOUT:\n" + result.stdout
                + "\nSTDERR:\n" + result.stderr
                + f"\nRETURN_CODE={result.returncode}\n"
            )
        except subprocess.TimeoutExpired as exc:
            build_timed_out = True
            build_output = (
                "$ " + shlex.join(compile_command)
                + "\nBUILD_TIMEOUT\n"
                + f"STDOUT={exc.stdout!r}\nSTDERR={exc.stderr!r}\n"
            )
            raise ValidationError("Native MPI compilation timed out.") from exc
        except OSError as exc:
            build_output = f"BUILD_LAUNCH_ERROR: {exc}\n"
            raise ValidationError(f"Could not launch mpicc: {exc}") from exc

        write_text(build_log_path, build_output)
        require(
            build_exit_code == 0,
            f"MPI compilation failed with exit code {build_exit_code}.",
        )
        require(
            executable_path.is_file()
            and not executable_path.is_symlink()
            and os.access(executable_path, os.X_OK),
            "MPI compiler did not produce a safe executable file.",
        )
        executable_digest = sha256_file(executable_path)

        row_ptr, column_indices, values, vector = build_test_matrix(
            rows, columns
        )
        nnz = len(column_indices)
        write_bytes_atomic(
            request_path,
            encode_request(
                rows, columns, row_ptr, column_indices, values, vector
            ),
        )

        if response_path.exists() or response_path.is_symlink():
            require(
                not response_path.is_symlink(),
                "Refusing to replace a symlinked MPI response.",
            )
            response_path.unlink()

        execution_command = [
            *launcher_tokens, "-np", str(args.processes),
            str(executable_path), str(request_path), str(response_path),
        ]

        start = time.monotonic()
        try:
            result = run_command(
                execution_command, args.timeout, environment
            )
            execution_duration = time.monotonic() - start
            execution_returncode = result.returncode
            execution_stdout = result.stdout or ""
            execution_stderr = result.stderr or ""
            execution_outcome = _process_outcome(
                execution_returncode, False, None
            )
        except subprocess.TimeoutExpired as exc:
            execution_duration = time.monotonic() - start
            execution_timed_out = True
            execution_stdout = _decode_captured(exc.stdout)
            execution_stderr = (
                _decode_captured(exc.stderr) + "\nMPI_EXECUTION_TIMEOUT\n"
            )
            execution_outcome = _process_outcome(None, True, None)
            raise ValidationError(
                f"MPI execution timed out after {args.timeout} seconds."
            ) from exc
        except OSError as exc:
            execution_duration = time.monotonic() - start
            launch_error = f"{type(exc).__name__}: {exc}"
            execution_stderr = f"MPI_LAUNCH_ERROR: {launch_error}\n"
            execution_outcome = _process_outcome(
                None, False, launch_error
            )
            raise ValidationError(
                f"Could not launch MPI command: {launch_error}"
            ) from exc

        if execution_returncode != 0:
            if execution_returncode is not None and execution_returncode < 0:
                number = -execution_returncode
                detail = (
                    f"terminated by signal {number} "
                    f"({_signal_name(number)})"
                )
            else:
                detail = f"exited normally with status {execution_returncode}"
            raise ValidationError(f"MPI launcher {detail}.")

        actual = decode_response(response_path, rows)
        reference = sequential_csr_reference(
            rows, row_ptr, column_indices, values, vector
        )
        comparison, comparison_passed = compare_results_with_status(
            actual, reference
        )
        comparison_executed = True
        if not comparison_passed:
            raise ValidationError(
                "MPI numerical mismatch: measured errors exceed the "
                "configured mixed absolute/relative tolerance."
            )
        validation = "PASS"

    except (
        ValidationError, OSError, ValueError, struct.error, OverflowError
    ) as exc:
        validation = "FAIL"
        execution_stderr += (
            ("\n" if execution_stderr else "")
            + f"P3_MPI_VALIDATION_ERROR: {type(exc).__name__}: {exc}\n"
        )
        print(f"P3_MPI_VALIDATION_FAILED: {exc}", file=sys.stderr)

    finally:
        if not build_output:
            build_output = "BUILD_NOT_COMPLETED\n"
        if not execution_stdout:
            execution_stdout = "NO_STDOUT_CAPTURED\n"
        if not execution_stderr:
            execution_stderr = "NO_STDERR_CAPTURED\n"

        if execution_outcome["type"] == "NOT_RUN" and execution_timed_out:
            execution_outcome = _process_outcome(None, True, None)
        elif launch_error is not None:
            execution_outcome = _process_outcome(
                None, False, launch_error
            )

        write_text(build_log_path, build_output)
        write_text(stdout_path, execution_stdout)
        write_text(stderr_path, execution_stderr)

        report = make_report(
            run_id=run_id,
            source_commit=source_commit,
            workflow_run_id=workflow_run_id,
            workflow_run_attempt=workflow_run_attempt,
            compiler=compiler_path,
            compiler_version=compiler_version,
            executable=EXECUTABLE_RELATIVE.as_posix(),
            executable_sha256=executable_digest,
            build_exit_code=build_exit_code,
            launcher=launcher_display,
            process_count=args.processes,
            execution_exit_code=(
                execution_returncode
                if execution_returncode is not None else 1
            ),
            skipped=skipped,
            timed_out=execution_timed_out or build_timed_out,
            rows=rows,
            columns=columns,
            nnz=nnz,
            comparison=comparison,
            validation=validation,
            execution_outcome=execution_outcome,
            execution_command=execution_command,
            execution_duration_seconds=execution_duration,
            launcher_metadata=launcher_metadata,
            comparison_executed=comparison_executed,
            comparison_passed=comparison_passed,
            launch_error=launch_error,
        )
        write_json_atomic(report_path, report)

    if validation != "PASS":
        return 1

    print("P3_MPI_VALIDATION: PASS")
    print(f"RUN_ID: {run_id}")
    print(f"SOURCE_COMMIT: {source_commit}")
    print(f"WORKFLOW_RUN_ID: {workflow_run_id}")
    print(f"WORKFLOW_RUN_ATTEMPT: {workflow_run_attempt}")
    print(f"MPI_PROCESSES: {args.processes}")
    print(f"MATRIX: rows={rows}, columns={columns}, nnz={nnz}")
    print(
        "MAX_ABSOLUTE_ERROR: "
        f"{comparison['max_absolute_error']:.17g}"
    )
    print(f"EXECUTABLE_SHA256: {executable_digest}")
    print(f"REPORT: {REPORT_RELATIVE.as_posix()}")
    return 0


def _decode_captured(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
