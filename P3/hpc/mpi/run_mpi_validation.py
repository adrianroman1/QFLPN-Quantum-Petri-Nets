#!/usr/bin/env python3
"""Fail-closed MPI validation for P3 distributed CSR SpMV.

This is a multi-process correctness smoke test. It is not evidence of
multi-node scaling or HPC performance.

The JSON report is designed to be independently checked by
P3/tools/verify_final_package.py.
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
    """Validate execution identity."""
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
        isinstance(workflow_run_id, str)
        and workflow_run_id.isdigit(),
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
    """Create a deterministic CSR matrix with up to three entries per row."""
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
        "<8s6Q",
        INPUT_MAGIC,
        rows,
        columns,
        nnz,
        len(vector),
        0,
        0,
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
        if expected_rows
        else []
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
    """Independent scalar CSR reference implementation."""
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
    """Compare results with mixed absolute/relative tolerance.

    The reported relative error uses max(abs(reference), absolute tolerance)
    as its denominator. This keeps the diagnostic finite when a reference
    component is zero while preserving the actual acceptance criterion.
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
        allowed = ABSOLUTE_TOLERANCE + RELATIVE_TOLERANCE * magnitude

        require(
            absolute_error <= allowed,
            (
                "MPI numerical mismatch: "
                f"actual={observed!r}, reference={expected!r}, "
                f"error={absolute_error!r}, allowed={allowed!r}"
            ),
        )

        relative_error = absolute_error / max(
            magnitude,
            ABSOLUTE_TOLERANCE,
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
    workflow_run_attempt: str = "1",
) -> dict[str, Any]:
    """Build the stable report contract consumed by verify_final_package.py."""
    build_ok = build_exit_code == 0 and bool(executable_sha256)
    execution_ok = (
        execution_exit_code == 0
        and not skipped
        and not timed_out
        and process_count >= 2
    )
    numerical_ok = validation == "PASS" and execution_ok and build_ok

    return {
        "schema": SCHEMA,
        "validation": "PASS" if numerical_ok else "FAIL",
        "run_id": run_id,
        "source_commit": source_commit,
        "workflow_run_id": workflow_run_id,
        "workflow_run_attempt": (
            int(workflow_run_attempt)
            if workflow_run_attempt.isdigit()
            else 0
        ),
        "repository": REPOSITORY,
        "native_build": {
            "status": "PASS" if build_ok else "FAIL",
            "compiler": "mpicc",
            "compiler_path": compiler,
            "compiler_version": compiler_version,
            "source_file": SOURCE_RELATIVE.as_posix(),
            "executable": executable,
            "executable_sha256": executable_sha256,
            "exit_code": build_exit_code,
        },
        "execution": {
            "status": "PASS" if execution_ok else "FAIL",
            "launcher": launcher,
            "process_count": process_count,
            "exit_code": execution_exit_code,
            "skipped": skipped,
            "timeout": timed_out,
            "stdout_file": STDOUT_RELATIVE.as_posix(),
            "stderr_file": STDERR_RELATIVE.as_posix(),
        },
        "numerical_validation": {
            "status": "PASS" if numerical_ok else "FAIL",
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
            "comparison": "PASS" if numerical_ok else "FAIL",
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
        os.environ.get("P3_SOURCE_COMMIT")
        or os.environ.get("GITHUB_SHA", "")
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
        require(rows >= 2 and columns >= 3, "Invalid smoke matrix dimensions.")

        validate_provenance(
            run_id,
            source_commit,
            workflow_run_id,
            workflow_run_attempt,
        )

        require(
            source_path.is_file() and not source_path.is_symlink(),
            f"Native MPI source is missing or unsafe: {SOURCE_RELATIVE}",
        )

        environment = os.environ.copy()
        environment.setdefault("OMPI_ALLOW_RUN_AS_ROOT", "1")
        environment.setdefault("OMPI_ALLOW_RUN_AS_ROOT_CONFIRM", "1")

        compiler_path = resolve_tool(
            os.environ.get("MPICC", "mpicc"),
            "MPI C compiler",
        )
        compiler_version = command_version(
            [compiler_path, "--version"],
            environment,
        )

        launcher_tokens = shlex.split(
            os.environ.get("P3_MPI_LAUNCHER", "mpirun")
        )
        require(bool(launcher_tokens), "P3_MPI_LAUNCHER is empty.")
        launcher_tokens[0] = resolve_tool(
            launcher_tokens[0],
            "MPI launcher",
        )
        launcher_display = shlex.join(launcher_tokens)

        executable_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.parent.mkdir(parents=True, exist_ok=True)
        response_path.parent.mkdir(parents=True, exist_ok=True)

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
            result = run_command(
                compile_command,
                args.timeout,
                environment,
            )
            build_exit_code = result.returncode
            build_output = (
                "$ " + shlex.join(compile_command)
                + "\nSTDOUT:\n" + result.stdout
                + "\nSTDERR:\n" + result.stderr
                + f"\nEXIT_CODE={build_exit_code}\n"
            )
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            build_output = (
                "$ " + shlex.join(compile_command)
                + "\nBUILD_TIMEOUT\n"
                + f"STDOUT={exc.stdout!r}\nSTDERR={exc.stderr!r}\n"
            )
            raise ValidationError(
                "Native MPI compilation timed out."
            ) from exc
        except OSError as exc:
            build_output = f"BUILD_LAUNCH_ERROR: {exc}\n"
            raise ValidationError(
                f"Could not launch mpicc: {exc}"
            ) from exc

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
            rows,
            columns,
        )
        nnz = len(column_indices)

        write_bytes_atomic(
            request_path,
            encode_request(
                rows,
                columns,
                row_ptr,
                column_indices,
                values,
                vector,
            ),
        )

        if response_path.exists() or response_path.is_symlink():
            require(
                not response_path.is_symlink(),
                "Refusing to replace a symlinked MPI response.",
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
            result = run_command(
                command,
                args.timeout,
                environment,
            )
            execution_exit_code = result.returncode
            execution_stdout = result.stdout
            execution_stderr = result.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            execution_stdout = str(exc.stdout or "")
            execution_stderr = (
                str(exc.stderr or "") + "\nMPI_EXECUTION_TIMEOUT\n"
            )
            raise ValidationError("MPI execution timed out.") from exc
        except OSError as exc:
            execution_stderr = f"MPI_LAUNCH_ERROR: {exc}\n"
            raise ValidationError(
                f"Could not launch MPI: {exc}"
            ) from exc

        require(
            execution_exit_code == 0,
            f"MPI launcher failed with exit code {execution_exit_code}.",
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

    except (
        ValidationError,
        OSError,
        ValueError,
        struct.error,
        OverflowError,
    ) as exc:
        validation = "FAIL"
        execution_stderr += (
            ("\n" if execution_stderr else "")
            + f"P3_MPI_VALIDATION_ERROR: {type(exc).__name__}: {exc}\n"
        )
        print(
            f"P3_MPI_VALIDATION_FAILED: {exc}",
            file=sys.stderr,
        )

    finally:
        # The verifier requires all evidence paths to exist, even on failure.
        if not build_output:
            build_output = "BUILD_NOT_COMPLETED\n"
        if not execution_stdout:
            execution_stdout = "NO_STDOUT_CAPTURED\n"
        if not execution_stderr:
            execution_stderr = "NO_STDERR_CAPTURED\n"

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
    print(f"WORKFLOW_RUN_ATTEMPT: {workflow_run_attempt}")
    print(f"MPI_PROCESSES: {args.processes}")
    print(
        f"MATRIX: rows={rows}, columns={columns}, nnz={nnz}"
    )
    print(
        "MAX_ABSOLUTE_ERROR: "
        f"{comparison['max_absolute_error']:.17g}"
    )
    print(f"EXECUTABLE_SHA256: {executable_digest}")
    print(f"REPORT: {REPORT_RELATIVE.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
