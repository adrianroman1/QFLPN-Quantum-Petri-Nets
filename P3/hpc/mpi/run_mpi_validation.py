#!/usr/bin/env python3
"""Fail-closed native MPI validation for P3 distributed CSR SpMV.

This runner:
1. validates the required repository/run provenance;
2. compiles the committed native MPI C backend with mpicc;
3. creates a deterministic CSR test case using the documented P3SPMV01
   little-endian protocol;
4. launches at least two real MPI processes;
5. checks the P3OUT001 response against an independent sequential CSR
   reference;
6. records compiler, executable digest, launcher, logs, dimensions,
   numerical tolerances and provenance in mpi-validation.json.

This is an MPI multi-process smoke test. A successful local CI run does
not demonstrate multi-node cluster scaling or HPC performance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shlex
import shutil
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
    """Raised when a mandatory MPI validation condition is not met."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")

    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def validate_provenance(
    run_id: str,
    source_commit: str,
    workflow_run_id: str,
) -> None:
    require(
        bool(run_id.strip()),
        "P3_RUN_ID is missing.",
    )
    require(
        len(source_commit) == 40
        and all(character in "0123456789abcdef" for character in source_commit),
        "GITHUB_SHA must be a 40-character lowercase hexadecimal commit.",
    )
    require(
        workflow_run_id.isdigit(),
        "GITHUB_RUN_ID must contain decimal digits only.",
    )


def build_test_matrix(
    rows: int,
    columns: int,
) -> tuple[list[int], list[int], list[float], list[float]]:
    """Build deterministic CSR with exactly three entries per row."""
    require(rows >= 2, "Smoke matrix must contain at least two rows.")
    require(columns >= 3, "Smoke matrix must contain at least three columns.")

    row_ptr = [0]
    column_indices: list[int] = []
    values: list[float] = []
    vector = [
        ((index % 17) - 8) / 8.0
        for index in range(columns)
    ]

    for row in range(rows):
        # Distinct, deterministic columns. The modulo construction also
        # remains valid when rows and columns are not equal.
        candidates = (
            row % columns,
            (row + 1) % columns,
            (row + 7) % columns,
        )
        selected = sorted(set(candidates))

        for position, column in enumerate(selected):
            column_indices.append(column)
            # Exactly representable binary fractions simplify independent
            # comparison while still exercising signed values.
            numerator = ((row * 5 + position * 3) % 19) - 9
            values.append(numerator / 16.0)

        row_ptr.append(len(column_indices))

    require(
        row_ptr[0] == 0 and row_ptr[-1] == len(column_indices),
        "Generated CSR row pointer endpoints are invalid.",
    )
    require(
        all(left <= right for left, right in zip(row_ptr, row_ptr[1:])),
        "Generated CSR row pointers are not monotonic.",
    )
    require(
        all(0 <= column < columns for column in column_indices),
        "Generated CSR column index is out of range.",
    )
    require(
        all(math.isfinite(value) for value in values + vector),
        "Generated matrix contains non-finite values.",
    )

    return row_ptr, column_indices, values, vector


def encode_request(
    rows: int,
    columns: int,
    row_ptr: list[int],
    column_indices: list[int],
    values: list[float],
    vector: list[float],
) -> bytes:
    nnz = len(column_indices)

    require(len(row_ptr) == rows + 1, "CSR row pointer length mismatch.")
    require(len(values) == nnz, "CSR values length mismatch.")
    require(len(vector) == columns, "Input vector length mismatch.")

    header = struct.pack(
        "<8s6Q",
        INPUT_MAGIC,
        rows,
        columns,
        nnz,
        len(vector),
        0,  # flags: currently no optional protocol flags
        0,  # reserved
    )

    row_payload = struct.pack(f"<{len(row_ptr)}Q", *row_ptr)
    column_payload = (
        struct.pack(f"<{nnz}Q", *column_indices)
        if nnz
        else b""
    )
    value_payload = (
        struct.pack(f"<{nnz}d", *values)
        if nnz
        else b""
    )
    vector_payload = (
        struct.pack(f"<{columns}d", *vector)
        if columns
        else b""
    )

    return (
        header
        + row_payload
        + column_payload
        + value_payload
        + vector_payload
    )


def decode_response(
    path: Path,
    expected_rows: int,
) -> list[float]:
    payload = path.read_bytes()

    require(
        len(payload) >= 32,
        "MPI response is shorter than its 32-byte header.",
    )

    magic, rows, status, reserved = struct.unpack("<8s3Q", payload[:32])

    require(magic == OUTPUT_MAGIC, "MPI response magic is invalid.")
    require(rows == expected_rows, "MPI response row count mismatch.")
    require(status == 0, "MPI response reports a non-zero status.")
    require(reserved == 0, "MPI response reserved field is non-zero.")

    expected_length = 32 + expected_rows * 8
    require(
        len(payload) == expected_length,
        "MPI response length does not match its declared row count.",
    )

    if expected_rows == 0:
        return []

    result = list(
        struct.unpack(
            f"<{expected_rows}d",
            payload[32:],
        )
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
    """Independent scalar CSR SpMV reference in Python."""
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
    require(
        len(actual) == len(reference),
        "MPI result and sequential reference lengths differ.",
    )

    maximum_absolute_error = 0.0
    maximum_relative_error = 0.0
    maximum_reference_magnitude = 0.0

    for observed, expected in zip(actual, reference):
        require(
            math.isfinite(observed) and math.isfinite(expected),
            "Numerical comparison encountered a non-finite value.",
        )

        absolute_error = abs(observed - expected)
        reference_magnitude = abs(expected)

        allowed_error = (
            ABSOLUTE_TOLERANCE
            + RELATIVE_TOLERANCE * reference_magnitude
        )

        require(
            absolute_error <= allowed_error,
            (
                "MPI numerical mismatch: "
                f"actual={observed!r}, reference={expected!r}, "
                f"absolute_error={absolute_error!r}, "
                f"allowed_error={allowed_error!r}"
            ),
        )

        relative_error = (
            absolute_error / reference_magnitude
            if reference_magnitude > 0.0
            else (0.0 if absolute_error == 0.0 else math.inf)
        )

        maximum_absolute_error = max(
            maximum_absolute_error,
            absolute_error,
        )
        maximum_relative_error = max(
            maximum_relative_error,
            relative_error,
        )
        maximum_reference_magnitude = max(
            maximum_reference_magnitude,
            reference_magnitude,
        )

    require(
        math.isfinite(maximum_relative_error),
        "Relative numerical error is not finite.",
    )

    return {
        "max_absolute_error": maximum_absolute_error,
        "max_relative_error": maximum_relative_error,
        "max_reference_magnitude": maximum_reference_magnitude,
    }


def run_command(
    command: list[str],
    *,
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


def command_version(
    command: list[str],
    environment: dict[str, str],
) -> str:
    try:
        result = run_command(
            command,
            timeout_seconds=20,
            environment=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValidationError(
            f"Could not obtain tool version for {command!r}: {exc}"
        ) from exc

    output = (result.stdout + "\n" + result.stderr).strip()
    require(
        result.returncode == 0 and bool(output),
        f"Version command failed: {command!r}",
    )

    return output[:4000]


def resolve_tool(value: str, label: str) -> str:
    resolved = shutil.which(value)

    require(
        resolved is not None,
        f"{label} was not found on PATH: {value}",
    )

    return str(Path(resolved).resolve())


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
    comparison: dict[str, float],
    validation: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "validation": validation,
        "run_id": run_id,
        "source_commit": source_commit,
        "workflow_run_id": workflow_run_id,
        "repository": REPOSITORY,
        "native_build": {
            "status": "PASS" if build_exit_code == 0 else "FAIL",
            "compiler": "mpicc",
            "compiler_path": compiler,
            "compiler_version": compiler_version,
            "source_file": SOURCE_RELATIVE.as_posix(),
            "executable": executable,
            "executable_sha256": executable_sha256,
            "exit_code": build_exit_code,
        },
        "execution": {
            "status": (
                "PASS"
                if execution_exit_code == 0 and not skipped and not timed_out
                else "FAIL"
            ),
            "launcher": launcher,
            "process_count": process_count,
            "exit_code": execution_exit_code,
            "skipped": skipped,
            "timeout": timed_out,
            "stdout_file": STDOUT_RELATIVE.as_posix(),
            "stderr_file": STDERR_RELATIVE.as_posix(),
        },
        "numerical_validation": {
            "status": validation,
            "reference": "sequential_csr",
            "rows": rows,
            "columns": columns,
            "nnz": nnz,
            "max_absolute_error": comparison["max_absolute_error"],
            "max_relative_error": comparison["max_relative_error"],
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "relative_tolerance": RELATIVE_TOLERANCE,
            "max_reference_magnitude": comparison[
                "max_reference_magnitude"
            ],
            "comparison": validation,
        },
        "provenance": {
            "commit_verified": True,
            "run_id_verified": True,
            "workflow_run_id_verified": True,
        },
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and execute the P3 native MPI validation."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "--processes",
        type=int,
        default=2,
        help="MPI process count; must be at least 2 (default: 2).",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=DEFAULT_ROWS,
        help=f"Smoke matrix rows (default: {DEFAULT_ROWS}).",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=DEFAULT_COLUMNS,
        help=f"Smoke matrix columns (default: {DEFAULT_COLUMNS}).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Build/launch timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    root = Path(args.root).resolve()

    run_id = os.environ.get("P3_RUN_ID", "")
    source_commit = os.environ.get("P3_SOURCE_COMMIT") or os.environ.get(
        "GITHUB_SHA", ""
    )
    workflow_run_id = os.environ.get("P3_WORKFLOW_RUN_ID") or os.environ.get(
        "GITHUB_RUN_ID", ""
    )
    workflow_run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")

    report_path = root / REPORT_RELATIVE
    stdout_path = root / STDOUT_RELATIVE
    stderr_path = root / STDERR_RELATIVE
    build_log_path = root / BUILD_LOG_RELATIVE

    executable_path = root / EXECUTABLE_RELATIVE
    request_path = root / REQUEST_RELATIVE
    response_path = root / RESPONSE_RELATIVE
    source_path = root / SOURCE_RELATIVE

    compiler_path = ""
    compiler_version = ""
    launcher_display = ""
    executable_digest = ""
    build_exit_code = 1
    execution_exit_code = 1
    skipped = False
    timed_out = False
    rows = args.rows
    columns = args.columns
    nnz = 0
    comparison = {
        "max_absolute_error": 0.0,
        "max_relative_error": 0.0,
        "max_reference_magnitude": 0.0,
    }

    build_output = ""
    execution_stdout = ""
    execution_stderr = ""
    validation = "FAIL"

    try:
        require(root.is_dir(), f"Repository root does not exist: {root}")
        require(args.processes >= 2, "--processes must be at least 2.")
        require(args.timeout > 0, "--timeout must be positive.")
        require(rows >= 2, "--rows must be at least 2.")
        require(columns >= 3, "--columns must be at least 3.")

        validate_provenance(run_id, source_commit, workflow_run_id)

        require(
            source_path.is_file() and not source_path.is_symlink(),
            f"Native MPI source is missing or unsafe: {SOURCE_RELATIVE}",
        )

        compiler_name = os.environ.get("MPICC", "mpicc")
        compiler_path = resolve_tool(compiler_name, "MPI C compiler")
        compiler_version = command_version(
            [compiler_path, "--version"],
            os.environ.copy(),
        )

        launcher_tokens = shlex.split(
            os.environ.get("P3_MPI_LAUNCHER", "mpirun")
        )
        require(bool(launcher_tokens), "P3_MPI_LAUNCHER is empty.")

        launcher_path = resolve_tool(launcher_tokens[0], "MPI launcher")
        launcher_tokens[0] = launcher_path
        launcher_display = shlex.join(launcher_tokens)

        environment = os.environ.copy()

        # Permit execution in a root-owned GitHub Actions container/runner
        # when using Open MPI. Other MPI implementations ignore these vars.
        environment.setdefault("OMPI_ALLOW_RUN_AS_ROOT", "1")
        environment.setdefault("OMPI_ALLOW_RUN_AS_ROOT_CONFIRM", "1")

        executable_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.parent.mkdir(parents=True, exist_ok=True)
        response_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        compile_command = [
            compiler_path,
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Wconversion",
            "-Wshadow",
            str(source_path),
            "-o",
            str(executable_path),
            "-lm",
        ]

        try:
            build_result = run_command(
                compile_command,
                timeout_seconds=args.timeout,
                environment=environment,
            )
            build_exit_code = build_result.returncode
            build_output = (
                "$ " + shlex.join(compile_command) + "\n"
                + "STDOUT:\n" + build_result.stdout
                + "\nSTDERR:\n" + build_result.stderr
                + f"\nEXIT_CODE={build_exit_code}\n"
            )
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            build_output = (
                "$ " + shlex.join(compile_command)
                + "\nBUILD_TIMEOUT\n"
                + str(exc)
            )
            raise ValidationError("Native MPI compilation timed out.") from exc
        except OSError as exc:
            build_output = f"BUILD_LAUNCH_ERROR: {exc}\n"
            raise ValidationError(
                f"Could not launch mpicc: {exc}"
            ) from exc

        write_text(build_log_path, build_output)

        require(
            build_exit_code == 0,
            f"Native MPI compilation failed with exit code {build_exit_code}.",
        )
        require(
            executable_path.is_file() and not executable_path.is_symlink(),
            "MPI compiler returned success but executable is missing.",
        )

        executable_digest = sha256_file(executable_path)

        row_ptr, column_indices, values, vector = build_test_matrix(
            rows,
            columns,
        )
        nnz = len(column_indices)

        request_payload = encode_request(
            rows,
            columns,
            row_ptr,
            column_indices,
            values,
            vector,
        )
        write_bytes_atomic(request_path, request_payload)

        if response_path.exists():
            require(
                not response_path.is_symlink(),
                "Refusing to replace a symlinked MPI response path.",
            )
            response_path.unlink()

        command = [
            *launcher_tokens,
            "-np",
            str(args.processes),
            str(executable_path),
            str(request_path),
            str(response_path),
        ]

        try:
            execution_result = run_command(
                command,
                timeout_seconds=args.timeout,
                environment=environment,
            )
            execution_exit_code = execution_result.returncode
            execution_stdout = execution_result.stdout
            execution_stderr = execution_result.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            execution_stdout = str(exc.stdout or "")
            execution_stderr = str(exc.stderr or "") + "\nMPI_EXECUTION_TIMEOUT\n"
            raise ValidationError("MPI execution timed out.") from exc
        except OSError as exc:
            execution_stderr = f"MPI_LAUNCH_ERROR: {exc}\n"
            raise ValidationError(
                f"Could not launch MPI process: {exc}"
            ) from exc

        require(
            execution_exit_code == 0,
            f"MPI launcher failed with exit code {execution_exit_code}.",
        )
        require(
            response_path.is_file() and not response_path.is_symlink(),
            "MPI process returned success but response file is missing.",
        )

        actual = decode_response(response_path, rows)
        reference = sequential_csr_reference(
            rows,
            row_ptr,
            column_indices,
            values,
            vector,
        )
        comparison = compare_results(actual, reference)

        validation = "PASS"

    except (ValidationError, OSError, ValueError, struct.error) as exc:
        validation = "FAIL"
        execution_stderr += (
            ("\n" if execution_stderr else "")
            + f"P3_MPI_VALIDATION_ERROR: {exc}\n"
        )
        print(f"P3_MPI_VALIDATION_FAILED: {exc}", file=sys.stderr)

    finally:
        write_text(build_log_path, build_output)
        write_text(stdout_path, execution_stdout)
        write_text(stderr_path, execution_stderr)

        # Report only a real executable digest. On failed builds the empty
        # digest deliberately causes the independent final verifier to fail.
        report = make_report(
            run_id=run_id,
            source_commit=source_commit,
            workflow_run_id=workflow_run_id,
            compiler=compiler_path,
            compiler_version=compiler_version,
            executable=EXECUTABLE_RELATIVE.as_posix(),
            executable_sha256=executable_digest,
            build_exit_code=build_exit_code,
            launcher=launcher_display,
            process_count=args.processes,
            execution_exit_code=execution_exit_code,
            skipped=skipped,
            timed_out=timed_out,
            rows=rows,
            columns=columns,
            nnz=nnz,
            comparison=comparison,
            validation=validation,
        )

        write_json_atomic(report_path, report)

    if validation != "PASS":
        return 1

    print("P3_MPI_VALIDATION: PASS")
    print(f"RUN_ID: {run_id}")
    print(f"SOURCE_COMMIT: {source_commit}")
    print(f"WORKFLOW_RUN_ID: {workflow_run_id}")
    print(f"MPI_PROCESSES: {args.processes}")
    print(f"MATRIX: rows={rows}, columns={columns}, nnz={nnz}")
    print(
        "MAX_ABSOLUTE_ERROR: "
        f"{comparison['max_absolute_error']:.17g}"
    )
    print(f"EXECUTABLE_SHA256: {executable_digest}")
    print(f"REPORT: {REPORT_RELATIVE.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
