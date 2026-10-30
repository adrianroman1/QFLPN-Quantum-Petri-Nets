#!/usr/bin/env python3
"""Tests for the fail-closed P3 native MPI validation runner.

These tests validate the runner's protocol, numerical checks, provenance,
report contract and failure behavior without requiring an MPI installation.

A real multi-process MPI execution is performed by the p3_validation
workflow stage, not by these unit tests.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import struct
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "hpc" / "mpi" / "run_mpi_validation.py"

SPEC = importlib.util.spec_from_file_location(
    "p3_run_mpi_validation_under_test",
    RUNNER_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

mpi_runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mpi_runner
SPEC.loader.exec_module(mpi_runner)


VALID_RUN_ID = "p3-123456789-1"
VALID_COMMIT = "a" * 40
VALID_WORKFLOW_RUN_ID = "123456789"


def valid_provenance_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("P3_RUN_ID", VALID_RUN_ID)
    monkeypatch.setenv("P3_SOURCE_COMMIT", VALID_COMMIT)
    monkeypatch.setenv("P3_WORKFLOW_RUN_ID", VALID_WORKFLOW_RUN_ID)


def make_small_matrix() -> tuple[
    int,
    int,
    list[int],
    list[int],
    list[float],
    list[float],
]:
    rows = 8
    columns = 8

    row_ptr, column_indices, values, vector = (
        mpi_runner.build_test_matrix(rows, columns)
    )

    return (
        rows,
        columns,
        row_ptr,
        column_indices,
        values,
        vector,
    )


def write_response(
    path: Path,
    values: list[float],
    *,
    magic: bytes = b"P3OUT001",
    rows: int | None = None,
    status: int = 0,
    reserved: int = 0,
) -> None:
    declared_rows = len(values) if rows is None else rows

    header = struct.pack(
        "<8s3Q",
        magic,
        declared_rows,
        status,
        reserved,
    )

    payload = (
        struct.pack(f"<{len(values)}d", *values)
        if values
        else b""
    )

    path.write_bytes(header + payload)


def test_runner_file_exists_and_is_regular_file() -> None:
    assert RUNNER_PATH.is_file()
    assert not RUNNER_PATH.is_symlink()


def test_valid_provenance_is_accepted() -> None:
    mpi_runner.validate_provenance(
        VALID_RUN_ID,
        VALID_COMMIT,
        VALID_WORKFLOW_RUN_ID,
    )


@pytest.mark.parametrize(
    ("run_id", "commit", "workflow_run_id"),
    [
        ("", VALID_COMMIT, VALID_WORKFLOW_RUN_ID),
        ("   ", VALID_COMMIT, VALID_WORKFLOW_RUN_ID),
        (VALID_RUN_ID, "a" * 39, VALID_WORKFLOW_RUN_ID),
        (VALID_RUN_ID, "g" * 40, VALID_WORKFLOW_RUN_ID),
        (VALID_RUN_ID, VALID_COMMIT.upper(), VALID_WORKFLOW_RUN_ID),
        (VALID_RUN_ID, VALID_COMMIT, ""),
        (VALID_RUN_ID, VALID_COMMIT, "12x"),
    ],
)
def test_invalid_provenance_fails_closed(
    run_id: str,
    commit: str,
    workflow_run_id: str,
) -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.validate_provenance(
            run_id,
            commit,
            workflow_run_id,
        )


def test_build_test_matrix_is_deterministic() -> None:
    first = mpi_runner.build_test_matrix(32, 24)
    second = mpi_runner.build_test_matrix(32, 24)

    assert first == second


def test_build_test_matrix_produces_valid_csr() -> None:
    rows, columns = 32, 24

    row_ptr, column_indices, values, vector = (
        mpi_runner.build_test_matrix(rows, columns)
    )

    assert len(row_ptr) == rows + 1
    assert row_ptr[0] == 0
    assert row_ptr[-1] == len(column_indices)
    assert len(column_indices) == len(values)
    assert len(vector) == columns

    assert all(
        left <= right
        for left, right in zip(row_ptr, row_ptr[1:])
    )

    assert all(
        0 <= column < columns
        for column in column_indices
    )

    assert all(math.isfinite(value) for value in values)
    assert all(math.isfinite(value) for value in vector)


@pytest.mark.parametrize(
    ("rows", "columns"),
    [
        (0, 8),
        (1, 8),
        (8, 0),
        (8, 1),
        (8, 2),
    ],
)
def test_build_test_matrix_rejects_invalid_dimensions(
    rows: int,
    columns: int,
) -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.build_test_matrix(rows, columns)


def test_binary_request_has_documented_header_and_payload() -> None:
    (
        rows,
        columns,
        row_ptr,
        column_indices,
        values,
        vector,
    ) = make_small_matrix()

    payload = mpi_runner.encode_request(
        rows,
        columns,
        row_ptr,
        column_indices,
        values,
        vector,
    )

    assert payload[:8] == b"P3SPMV01"

    (
        magic,
        encoded_rows,
        encoded_columns,
        nnz,
        vector_length,
        flags,
        reserved,
    ) = struct.unpack("<8s6Q", payload[:56])

    assert magic == b"P3SPMV01"
    assert encoded_rows == rows
    assert encoded_columns == columns
    assert nnz == len(column_indices)
    assert vector_length == columns
    assert flags == 0
    assert reserved == 0

    expected_length = (
        56
        + (rows + 1) * 8
        + nnz * 8
        + nnz * 8
        + columns * 8
    )

    assert len(payload) == expected_length


def test_encode_request_rejects_inconsistent_csr_lengths() -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.encode_request(
            rows=2,
            columns=3,
            row_ptr=[0, 1],
            column_indices=[0],
            values=[1.0],
            vector=[1.0, 2.0, 3.0],
        )


def test_encode_request_rejects_inconsistent_values_length() -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.encode_request(
            rows=2,
            columns=3,
            row_ptr=[0, 1, 2],
            column_indices=[0, 1],
            values=[1.0],
            vector=[1.0, 2.0, 3.0],
        )


def test_encode_request_rejects_inconsistent_vector_length() -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.encode_request(
            rows=2,
            columns=3,
            row_ptr=[0, 1, 2],
            column_indices=[0, 1],
            values=[1.0, 2.0],
            vector=[1.0, 2.0],
        )


def test_sequential_reference_matches_hand_calculated_result() -> None:
    result = mpi_runner.sequential_csr_reference(
        rows=3,
        row_ptr=[0, 2, 3, 5],
        column_indices=[0, 2, 1, 0, 2],
        values=[2.0, 3.0, -1.0, 4.0, 5.0],
        vector=[1.0, 2.0, 3.0],
    )

    assert result == [11.0, -2.0, 19.0]


def test_sequential_reference_supports_empty_rows() -> None:
    result = mpi_runner.sequential_csr_reference(
        rows=4,
        row_ptr=[0, 1, 1, 1, 2],
        column_indices=[0, 1],
        values=[3.0, 7.0],
        vector=[2.0, 5.0],
    )

    assert result == [6.0, 0.0, 0.0, 35.0]


def test_compare_results_accepts_identical_vectors() -> None:
    values = [0.0, 1.0, -2.5, 8.125]

    result = mpi_runner.compare_results(values, values)

    assert result["max_absolute_error"] == 0.0
    assert result["max_relative_error"] == 0.0
    assert result["max_reference_magnitude"] == 8.125


def test_compare_results_accepts_values_inside_tolerance() -> None:
    reference = [1.0, 2.0, 0.0]
    actual = [
        1.0 + 1.0e-13,
        2.0 - 1.0e-13,
        1.0e-13,
    ]

    result = mpi_runner.compare_results(actual, reference)

    assert result["max_absolute_error"] <= (
        mpi_runner.ABSOLUTE_TOLERANCE
        + mpi_runner.RELATIVE_TOLERANCE
        * result["max_reference_magnitude"]
    )


def test_compare_results_rejects_numerical_mismatch() -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.compare_results(
            [1.0, 2.0, 3.0],
            [1.0, 2.0, 3.01],
        )


def test_compare_results_rejects_different_vector_lengths() -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.compare_results(
            [1.0, 2.0],
            [1.0],
        )


@pytest.mark.parametrize(
    "values",
    [
        [math.nan],
        [math.inf],
        [-math.inf],
    ],
)
def test_compare_results_rejects_non_finite_values(
    values: list[float],
) -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.compare_results(values, [0.0])


def test_decode_response_accepts_valid_output(tmp_path: Path) -> None:
    path = tmp_path / "valid-response.p3mpi"
    expected = [1.0, -2.0, 3.5, 0.0]

    write_response(path, expected)

    assert mpi_runner.decode_response(path, len(expected)) == expected


def test_decode_response_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        mpi_runner.decode_response(
            tmp_path / "missing.p3mpi",
            2,
        )


def test_decode_response_rejects_short_header(tmp_path: Path) -> None:
    path = tmp_path / "short-header.p3mpi"
    path.write_bytes(b"P3OUT001")

    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 1)


def test_decode_response_rejects_wrong_magic(tmp_path: Path) -> None:
    path = tmp_path / "wrong-magic.p3mpi"

    write_response(
        path,
        [1.0],
        magic=b"BADMAGIC",
    )

    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 1)


def test_decode_response_rejects_wrong_row_count(tmp_path: Path) -> None:
    path = tmp_path / "wrong-rows.p3mpi"

    write_response(
        path,
        [1.0, 2.0],
        rows=3,
    )

    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 2)


def test_decode_response_rejects_nonzero_status(tmp_path: Path) -> None:
    path = tmp_path / "failed-status.p3mpi"

    write_response(
        path,
        [1.0],
        status=1,
    )

    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 1)


def test_decode_response_rejects_nonzero_reserved_field(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reserved.p3mpi"

    write_response(
        path,
        [1.0],
        reserved=1,
    )

    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 1)


def test_decode_response_rejects_truncated_payload(tmp_path: Path) -> None:
    path = tmp_path / "truncated.p3mpi"

    path.write_bytes(
        struct.pack("<8s3Q", b"P3OUT001", 2, 0, 0)
        + struct.pack("<d", 1.0)
    )

    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 2)


def test_decode_response_rejects_trailing_payload(tmp_path: Path) -> None:
    path = tmp_path / "trailing.p3mpi"

    path.write_bytes(
        struct.pack("<8s3Q", b"P3OUT001", 1, 0, 0)
        + struct.pack("<d", 1.0)
        + b"unexpected"
    )

    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 1)


@pytest.mark.parametrize(
    "value",
    [
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_decode_response_rejects_non_finite_values(
    tmp_path: Path,
    value: float,
) -> None:
    path = tmp_path / "non-finite.p3mpi"
    write_response(path, [value])

    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 1)


def test_make_report_contains_required_provenance_and_evidence() -> None:
    comparison = {
        "max_absolute_error": 0.0,
        "max_relative_error": 0.0,
        "max_reference_magnitude": 12.0,
    }

    report = mpi_runner.make_report(
        run_id=VALID_RUN_ID,
        source_commit=VALID_COMMIT,
        workflow_run_id=VALID_WORKFLOW_RUN_ID,
        compiler="/usr/bin/mpicc",
        compiler_version="MPI compiler test version",
        executable="P3/target/mpi/p3_mpi_spmv",
        executable_sha256="b" * 64,
        build_exit_code=0,
        launcher="/usr/bin/mpirun",
        process_count=2,
        execution_exit_code=0,
        skipped=False,
        timed_out=False,
        rows=128,
        columns=128,
        nnz=384,
        comparison=comparison,
        validation="PASS",
    )

    assert report["schema"] == "qflqn-p3-mpi-validation-v1"
    assert report["validation"] == "PASS"
    assert report["run_id"] == VALID_RUN_ID
    assert report["source_commit"] == VALID_COMMIT
    assert report["workflow_run_id"] == VALID_WORKFLOW_RUN_ID

    assert report["native_build"]["status"] == "PASS"
    assert report["native_build"]["compiler"] == "mpicc"
    assert report["native_build"]["exit_code"] == 0
    assert report["native_build"]["executable_sha256"] == "b" * 64

    assert report["execution"]["status"] == "PASS"
    assert report["execution"]["process_count"] == 2
    assert report["execution"]["exit_code"] == 0
    assert report["execution"]["skipped"] is False
    assert report["execution"]["timeout"] is False

    assert report["numerical_validation"]["status"] == "PASS"
    assert report["numerical_validation"]["comparison"] == "PASS"
    assert report["numerical_validation"]["reference"] == "sequential_csr"

    assert report["provenance"] == {
        "commit_verified": True,
        "run_id_verified": True,
        "workflow_run_id_verified": True,
    }


def test_make_report_marks_failed_build_as_failure() -> None:
    report = mpi_runner.make_report(
        run_id=VALID_RUN_ID,
        source_commit=VALID_COMMIT,
        workflow_run_id=VALID_WORKFLOW_RUN_ID,
        compiler="/usr/bin/mpicc",
        compiler_version="test",
        executable="P3/target/mpi/p3_mpi_spmv",
        executable_sha256="",
        build_exit_code=1,
        launcher="/usr/bin/mpirun",
        process_count=2,
        execution_exit_code=1,
        skipped=False,
        timed_out=False,
        rows=128,
        columns=128,
        nnz=384,
        comparison={
            "max_absolute_error": 0.0,
            "max_relative_error": 0.0,
            "max_reference_magnitude": 0.0,
        },
        validation="FAIL",
    )

    assert report["validation"] == "FAIL"
    assert report["native_build"]["status"] == "FAIL"
    assert report["execution"]["status"] == "FAIL"
    assert report["numerical_validation"]["status"] == "FAIL"


def test_make_report_marks_skipped_execution_as_failure() -> None:
    report = mpi_runner.make_report(
        run_id=VALID_RUN_ID,
        source_commit=VALID_COMMIT,
        workflow_run_id=VALID_WORKFLOW_RUN_ID,
        compiler="/usr/bin/mpicc",
        compiler_version="test",
        executable="P3/target/mpi/p3_mpi_spmv",
        executable_sha256="b" * 64,
        build_exit_code=0,
        launcher="/usr/bin/mpirun",
        process_count=2,
        execution_exit_code=0,
        skipped=True,
        timed_out=False,
        rows=128,
        columns=128,
        nnz=384,
        comparison={
            "max_absolute_error": 0.0,
            "max_relative_error": 0.0,
            "max_reference_magnitude": 0.0,
        },
        validation="FAIL",
    )

    assert report["execution"]["status"] == "FAIL"
    assert report["execution"]["skipped"] is True
    assert report["validation"] == "FAIL"


def test_make_report_marks_timeout_as_failure() -> None:
    report = mpi_runner.make_report(
        run_id=VALID_RUN_ID,
        source_commit=VALID_COMMIT,
        workflow_run_id=VALID_WORKFLOW_RUN_ID,
        compiler="/usr/bin/mpicc",
        compiler_version="test",
        executable="P3/target/mpi/p3_mpi_spmv",
        executable_sha256="b" * 64,
        build_exit_code=0,
        launcher="/usr/bin/mpirun",
        process_count=2,
        execution_exit_code=1,
        skipped=False,
        timed_out=True,
        rows=128,
        columns=128,
        nnz=384,
        comparison={
            "max_absolute_error": 0.0,
            "max_relative_error": 0.0,
            "max_reference_magnitude": 0.0,
        },
        validation="FAIL",
    )

    assert report["execution"]["status"] == "FAIL"
    assert report["execution"]["timeout"] is True
    assert report["validation"] == "FAIL"


def test_write_json_atomic_creates_parseable_report(
    tmp_path: Path,
) -> None:
    target = tmp_path / "nested" / "mpi-validation.json"
    payload = {
        "schema": "test-schema",
        "validation": "PASS",
        "value": 1,
    }

    mpi_runner.write_json_atomic(target, payload)

    assert target.is_file()
    assert json.loads(target.read_text(encoding="utf-8")) == payload
    assert not target.with_suffix(".json.tmp").exists()


def test_write_json_atomic_rejects_nan(tmp_path: Path) -> None:
    target = tmp_path / "invalid.json"

    with pytest.raises(ValueError):
        mpi_runner.write_json_atomic(
            target,
            {"value": math.nan},
        )

    assert not target.exists()


def test_write_bytes_atomic_creates_exact_payload(
    tmp_path: Path,
) -> None:
    target = tmp_path / "nested" / "request.bin"
    payload = b"\x00P3SPMV01\xff"

    mpi_runner.write_bytes_atomic(target, payload)

    assert target.read_bytes() == payload
    assert not target.with_suffix(".bin.tmp").exists()


def test_main_fails_closed_when_mpicc_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repository"
    source = root / mpi_runner.SOURCE_RELATIVE
    source.parent.mkdir(parents=True)
    source.write_text(
        "/* test-only MPI source placeholder */\n",
        encoding="utf-8",
    )

    valid_provenance_environment(monkeypatch)

    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    monkeypatch.setenv("MPICC", "definitely-missing-mpicc")
    monkeypatch.setenv("P3_MPI_LAUNCHER", "definitely-missing-mpirun")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(RUNNER_PATH),
            "--root",
            str(root),
        ],
    )

    exit_code = mpi_runner.main()

    assert exit_code == 1

    report_path = root / mpi_runner.REPORT_RELATIVE
    stdout_path = root / mpi_runner.STDOUT_RELATIVE
    stderr_path = root / mpi_runner.STDERR_RELATIVE
    build_log_path = root / mpi_runner.BUILD_LOG_RELATIVE

    assert report_path.is_file()
    assert stdout_path.is_file()
    assert stderr_path.is_file()
    assert build_log_path.is_file()

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["schema"] == "qflqn-p3-mpi-validation-v1"
    assert report["validation"] == "FAIL"
    assert report["run_id"] == VALID_RUN_ID
    assert report["source_commit"] == VALID_COMMIT
    assert report["workflow_run_id"] == VALID_WORKFLOW_RUN_ID
    assert report["native_build"]["status"] == "FAIL"
    assert report["execution"]["status"] == "FAIL"

    assert "P3_MPI_VALIDATION_ERROR" in stderr_path.read_text(
        encoding="utf-8"
    )


def test_main_rejects_single_process_before_tool_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repository"
    source = root / mpi_runner.SOURCE_RELATIVE
    source.parent.mkdir(parents=True)
    source.write_text("/* test source */\n", encoding="utf-8")

    valid_provenance_environment(monkeypatch)

    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    monkeypatch.setenv("MPICC", "missing-mpicc")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(RUNNER_PATH),
            "--root",
            str(root),
            "--processes",
            "1",
        ],
    )

    exit_code = mpi_runner.main()

    assert exit_code == 1

    report_path = root / mpi_runner.REPORT_RELATIVE
    assert report_path.is_file()

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["validation"] == "FAIL"
    assert report["execution"]["process_count"] == 1


def test_main_rejects_missing_run_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repository"
    source = root / mpi_runner.SOURCE_RELATIVE
    source.parent.mkdir(parents=True)
    source.write_text("/* test source */\n", encoding="utf-8")

    monkeypatch.delenv("P3_RUN_ID", raising=False)
    monkeypatch.setenv("P3_SOURCE_COMMIT", VALID_COMMIT)
    monkeypatch.setenv("P3_WORKFLOW_RUN_ID", VALID_WORKFLOW_RUN_ID)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(RUNNER_PATH),
            "--root",
            str(root),
        ],
    )

    exit_code = mpi_runner.main()

    assert exit_code == 1

    report_path = root / mpi_runner.REPORT_RELATIVE
    assert report_path.is_file()

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["validation"] == "FAIL"
    assert report["run_id"] == ""


def test_main_does_not_mark_missing_compiler_as_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repository"
    source = root / mpi_runner.SOURCE_RELATIVE
    source.parent.mkdir(parents=True)
    source.write_text("/* test source */\n", encoding="utf-8")

    valid_provenance_environment(monkeypatch)

    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    monkeypatch.setenv("MPICC", "missing-mpicc")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(RUNNER_PATH),
            "--root",
            str(root),
        ],
    )

    assert mpi_runner.main() == 1

    report = json.loads(
        (root / mpi_runner.REPORT_RELATIVE).read_text(encoding="utf-8")
    )

    assert report["execution"]["skipped"] is False
    assert report["validation"] == "FAIL"


def test_report_schema_constant_matches_verifier_contract() -> None:
    assert mpi_runner.SCHEMA == "qflqn-p3-mpi-validation-v1"


def test_mpi_report_paths_are_inside_p3_tree() -> None:
    paths = (
        mpi_runner.SOURCE_RELATIVE,
        mpi_runner.EXECUTABLE_RELATIVE,
        mpi_runner.REQUEST_RELATIVE,
        mpi_runner.RESPONSE_RELATIVE,
        mpi_runner.REPORT_RELATIVE,
        mpi_runner.STDOUT_RELATIVE,
        mpi_runner.STDERR_RELATIVE,
        mpi_runner.BUILD_LOG_RELATIVE,
    )

    for path in paths:
        assert not path.is_absolute()
        assert ".." not in path.parts
        assert path.parts[0] == "P3"


def test_smoke_dimensions_are_large_enough_for_two_processes() -> None:
    assert mpi_runner.DEFAULT_ROWS >= 2
    assert mpi_runner.DEFAULT_COLUMNS >= 3


def test_reference_and_encoded_matrix_agree() -> None:
    (
        rows,
        columns,
        row_ptr,
        column_indices,
        values,
        vector,
    ) = make_small_matrix()

    expected = mpi_runner.sequential_csr_reference(
        rows,
        row_ptr,
        column_indices,
        values,
        vector,
    )

    encoded = mpi_runner.encode_request(
        rows,
        columns,
        row_ptr,
        column_indices,
        values,
        vector,
    )

    assert encoded.startswith(b"P3SPMV01")
    assert len(expected) == rows
    assert all(math.isfinite(value) for value in expected)


def test_reference_is_independent_of_mpi_process_count() -> None:
    (
        rows,
        _columns,
        row_ptr,
        column_indices,
        values,
        vector,
    ) = make_small_matrix()

    first = mpi_runner.sequential_csr_reference(
        rows,
        row_ptr,
        column_indices,
        values,
        vector,
    )

    second = mpi_runner.sequential_csr_reference(
        rows,
        row_ptr,
        column_indices,
        values,
        vector,
    )

    assert first == second


def test_main_report_is_not_written_as_pass_on_preflight_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repository"
    source = root / mpi_runner.SOURCE_RELATIVE
    source.parent.mkdir(parents=True)
    source.write_text("/* test source */\n", encoding="utf-8")

    valid_provenance_environment(monkeypatch)

    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    monkeypatch.setenv("MPICC", "missing-mpicc")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(RUNNER_PATH),
            "--root",
            str(root),
        ],
    )

    assert mpi_runner.main() != 0

    report = json.loads(
        (root / mpi_runner.REPORT_RELATIVE).read_text(encoding="utf-8")
    )

    assert report["validation"] != "PASS"
    assert report["native_build"]["status"] != "PASS"
    assert report["execution"]["status"] != "PASS"
