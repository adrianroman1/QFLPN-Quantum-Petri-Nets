#!/usr/bin/env python3
"""Tests for the P3 fail-closed native MPI validation runner."""

from __future__ import annotations

import importlib.util
import json
import math
import struct
import sys
from pathlib import Path

import pytest


P3_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = P3_ROOT / "hpc" / "mpi" / "run_mpi_validation.py"

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
VALID_ATTEMPT = "1"


def valid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("P3_RUN_ID", VALID_RUN_ID)
    monkeypatch.setenv("P3_SOURCE_COMMIT", VALID_COMMIT)
    monkeypatch.setenv("P3_WORKFLOW_RUN_ID", VALID_WORKFLOW_RUN_ID)
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", VALID_ATTEMPT)


def small_matrix():
    rows = 8
    columns = 8
    row_ptr, col_idx, values, vector = (
        mpi_runner.build_test_matrix(rows, columns)
    )
    return rows, columns, row_ptr, col_idx, values, vector


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


def valid_report_arguments() -> dict:
    return {
        "run_id": VALID_RUN_ID,
        "source_commit": VALID_COMMIT,
        "workflow_run_id": VALID_WORKFLOW_RUN_ID,
        "compiler": "/usr/bin/mpicc",
        "compiler_version": "MPI compiler test version",
        "executable": "P3/target/mpi/p3_mpi_spmv",
        "executable_sha256": "b" * 64,
        "build_exit_code": 0,
        "launcher": "/usr/bin/mpirun",
        "process_count": 2,
        "execution_exit_code": 0,
        "skipped": False,
        "timed_out": False,
        "rows": 128,
        "columns": 128,
        "nnz": 384,
        "comparison": {
            "max_absolute_error": 0.0,
            "max_relative_error": 0.0,
            "max_reference_magnitude": 12.0,
        },
        "validation": "PASS",
    }


def test_runner_exists_and_is_regular_file() -> None:
    assert RUNNER_PATH.is_file()
    assert not RUNNER_PATH.is_symlink()


def test_valid_provenance_accepts_three_argument_contract() -> None:
    # Backward-compatible helper contract used by existing tests/callers.
    mpi_runner.validate_provenance(
        VALID_RUN_ID,
        VALID_COMMIT,
        VALID_WORKFLOW_RUN_ID,
    )


def test_valid_provenance_accepts_explicit_workflow_attempt() -> None:
    mpi_runner.validate_provenance(
        VALID_RUN_ID,
        VALID_COMMIT,
        VALID_WORKFLOW_RUN_ID,
        VALID_ATTEMPT,
    )


@pytest.mark.parametrize(
    ("run_id", "commit", "workflow_id", "attempt"),
    [
        ("", VALID_COMMIT, VALID_WORKFLOW_RUN_ID, VALID_ATTEMPT),
        ("   ", VALID_COMMIT, VALID_WORKFLOW_RUN_ID, VALID_ATTEMPT),
        ("bad run id", VALID_COMMIT, VALID_WORKFLOW_RUN_ID, VALID_ATTEMPT),
        (VALID_RUN_ID, "a" * 39, VALID_WORKFLOW_RUN_ID, VALID_ATTEMPT),
        (VALID_RUN_ID, "g" * 40, VALID_WORKFLOW_RUN_ID, VALID_ATTEMPT),
        (VALID_RUN_ID, VALID_COMMIT.upper(), VALID_WORKFLOW_RUN_ID, VALID_ATTEMPT),
        (VALID_RUN_ID, VALID_COMMIT, "", VALID_ATTEMPT),
        (VALID_RUN_ID, VALID_COMMIT, "12x", VALID_ATTEMPT),
        (VALID_RUN_ID, VALID_COMMIT, VALID_WORKFLOW_RUN_ID, ""),
        (VALID_RUN_ID, VALID_COMMIT, VALID_WORKFLOW_RUN_ID, "0"),
        (VALID_RUN_ID, VALID_COMMIT, VALID_WORKFLOW_RUN_ID, "1x"),
    ],
)
def test_invalid_provenance_fails_closed(
    run_id: str,
    commit: str,
    workflow_id: str,
    attempt: str,
) -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.validate_provenance(
            run_id,
            commit,
            workflow_id,
            attempt,
        )


def test_build_test_matrix_is_deterministic() -> None:
    assert mpi_runner.build_test_matrix(32, 24) == (
        mpi_runner.build_test_matrix(32, 24)
    )


def test_build_test_matrix_produces_valid_csr() -> None:
    rows, columns = 32, 24
    row_ptr, col_idx, values, vector = (
        mpi_runner.build_test_matrix(rows, columns)
    )

    assert len(row_ptr) == rows + 1
    assert row_ptr[0] == 0
    assert row_ptr[-1] == len(col_idx)
    assert len(col_idx) == len(values)
    assert len(vector) == columns
    assert all(a <= b for a, b in zip(row_ptr, row_ptr[1:]))
    assert all(0 <= col < columns for col in col_idx)
    assert all(math.isfinite(x) for x in values + vector)


@pytest.mark.parametrize(
    ("rows", "columns"),
    [(0, 8), (1, 8), (8, 0), (8, 1), (8, 2)],
)
def test_build_test_matrix_rejects_invalid_dimensions(
    rows: int,
    columns: int,
) -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.build_test_matrix(rows, columns)


def test_encode_request_has_expected_header_and_payload() -> None:
    rows, columns, row_ptr, col_idx, values, vector = small_matrix()

    payload = mpi_runner.encode_request(
        rows, columns, row_ptr, col_idx, values, vector
    )

    magic, declared_rows, declared_columns, nnz, vector_length, flags, reserved = (
        struct.unpack("<8s6Q", payload[:56])
    )

    assert magic == b"P3SPMV01"
    assert declared_rows == rows
    assert declared_columns == columns
    assert nnz == len(col_idx)
    assert vector_length == columns
    assert flags == 0
    assert reserved == 0

    expected_length = (
        56
        + (rows + 1) * 8
        + len(col_idx) * 8
        + len(values) * 8
        + columns * 8
    )
    assert len(payload) == expected_length


@pytest.mark.parametrize(
    ("row_ptr", "col_idx", "values", "vector"),
    [
        ([0, 1], [0], [1.0], [1.0, 2.0, 3.0]),
        ([0, 1, 2], [0, 1], [1.0], [1.0, 2.0, 3.0]),
        ([0, 1, 2], [0, 1], [1.0, 2.0], [1.0, 2.0]),
        ([1, 1, 2], [0, 1], [1.0, 2.0], [1.0, 2.0, 3.0]),
        ([0, 2, 1], [0, 1], [1.0, 2.0], [1.0, 2.0, 3.0]),
        ([0, 1, 2], [0, 3], [1.0, 2.0], [1.0, 2.0, 3.0]),
    ],
)
def test_encode_request_rejects_invalid_csr(
    row_ptr: list[int],
    col_idx: list[int],
    values: list[float],
    vector: list[float],
) -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.encode_request(
            rows=2,
            columns=3,
            row_ptr=row_ptr,
            column_indices=col_idx,
            values=values,
            vector=vector,
        )


def test_sequential_reference_matches_hand_calculation() -> None:
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
    actual = [1.0 + 1.0e-13, 2.0 - 1.0e-13, 1.0e-13]

    result = mpi_runner.compare_results(actual, reference)
    allowed = (
        mpi_runner.ABSOLUTE_TOLERANCE
        + mpi_runner.RELATIVE_TOLERANCE
        * result["max_reference_magnitude"]
    )
    assert result["max_absolute_error"] <= allowed


def test_compare_results_rejects_numerical_mismatch() -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.compare_results(
            [1.0, 2.0, 3.01],
            [1.0, 2.0, 3.0],
        )


def test_compare_results_rejects_different_lengths() -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.compare_results([1.0, 2.0], [1.0])


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_compare_results_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.compare_results([value], [0.0])


def test_decode_response_accepts_valid_output(tmp_path: Path) -> None:
    path = tmp_path / "valid-response.p3mpi"
    expected = [1.0, -2.0, 3.5, 0.0]
    write_response(path, expected)

    assert mpi_runner.decode_response(path, len(expected)) == expected


def test_decode_response_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(tmp_path / "missing.p3mpi", 2)


@pytest.mark.parametrize(
    "payload",
    [
        b"P3OUT001",
        struct.pack("<8s3Q", b"BADMAGIC", 1, 0, 0) + struct.pack("<d", 1.0),
        struct.pack("<8s3Q", b"P3OUT001", 1, 1, 0) + struct.pack("<d", 1.0),
        struct.pack("<8s3Q", b"P3OUT001", 1, 0, 1) + struct.pack("<d", 1.0),
        struct.pack("<8s3Q", b"P3OUT001", 2, 0, 0) + struct.pack("<d", 1.0),
        struct.pack("<8s3Q", b"P3OUT001", 1, 0, 0)
        + struct.pack("<d", 1.0) + b"extra",
    ],
)
def test_decode_response_rejects_invalid_payload(
    tmp_path: Path,
    payload: bytes,
) -> None:
    path = tmp_path / "invalid-response.p3mpi"
    path.write_bytes(payload)

    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 1)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_decode_response_rejects_non_finite_values(
    tmp_path: Path,
    value: float,
) -> None:
    path = tmp_path / "non-finite.p3mpi"
    write_response(path, [value])

    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 1)


def test_make_report_contains_required_provenance_and_evidence() -> None:
    report = mpi_runner.make_report(**valid_report_arguments())

    assert report["schema"] == "qflqn-p3-mpi-validation-v1"
    assert report["validation"] == "PASS"
    assert report["run_id"] == VALID_RUN_ID
    assert report["source_commit"] == VALID_COMMIT
    assert report["workflow_run_id"] == VALID_WORKFLOW_RUN_ID
    assert report["workflow_run_attempt"] == 1

    assert report["native_build"]["status"] == "PASS"
    assert report["native_build"]["compiler"] == "mpicc"
    assert report["native_build"]["executable_sha256"] == "b" * 64

    assert report["execution"]["status"] == "PASS"
    assert report["execution"]["process_count"] == 2
    assert report["execution"]["skipped"] is False
    assert report["execution"]["timeout"] is False

    assert report["numerical_validation"]["status"] == "PASS"
    assert report["numerical_validation"]["reference"] == "sequential_csr"
    assert report["numerical_validation"]["comparison"] == "PASS"

    assert report["provenance"] == {
        "commit_verified": True,
        "run_id_verified": True,
        "workflow_run_id_verified": True,
    }


def test_make_report_fails_when_build_fails() -> None:
    arguments = valid_report_arguments()
    arguments["build_exit_code"] = 1
    arguments["executable_sha256"] = ""

    report = mpi_runner.make_report(**arguments)

    assert report["validation"] == "FAIL"
    assert report["native_build"]["status"] == "FAIL"
    assert report["numerical_validation"]["status"] == "FAIL"


def test_make_report_fails_when_execution_is_skipped() -> None:
    arguments = valid_report_arguments()
    arguments["skipped"] = True

    report = mpi_runner.make_report(**arguments)

    assert report["validation"] == "FAIL"
    assert report["execution"]["status"] == "FAIL"
    assert report["execution"]["skipped"] is True


def test_make_report_fails_when_execution_times_out() -> None:
    arguments = valid_report_arguments()
    arguments["timed_out"] = True

    report = mpi_runner.make_report(**arguments)

    assert report["validation"] == "FAIL"
    assert report["execution"]["status"] == "FAIL"
    assert report["execution"]["timeout"] is True


def test_make_report_fails_for_single_process() -> None:
    arguments = valid_report_arguments()
    arguments["process_count"] = 1

    report = mpi_runner.make_report(**arguments)

    assert report["validation"] == "FAIL"
    assert report["execution"]["status"] == "FAIL"


def test_write_json_atomic_creates_parseable_report(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "mpi-validation.json"
    payload = {"schema": "test-schema", "validation": "PASS"}

    mpi_runner.write_json_atomic(target, payload)

    assert target.is_file()
    assert json.loads(target.read_text(encoding="utf-8")) == payload
    assert not target.with_suffix(".json.tmp").exists()


def test_write_json_atomic_rejects_nan(tmp_path: Path) -> None:
    target = tmp_path / "invalid.json"

    with pytest.raises(ValueError):
        mpi_runner.write_json_atomic(target, {"value": math.nan})

    assert not target.exists()


def test_write_bytes_atomic_creates_exact_payload(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "request.bin"
    payload = b"\x00P3SPMV01\xff"

    mpi_runner.write_bytes_atomic(target, payload)

    assert target.read_bytes() == payload
    assert not target.with_suffix(".bin.tmp").exists()


def test_main_fails_closed_when_mpicc_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    source = repository / mpi_runner.SOURCE_RELATIVE
    source.parent.mkdir(parents=True)
    source.write_text("/* test-only source placeholder */\n", encoding="utf-8")

    valid_environment(monkeypatch)
    empty_path = tmp_path / "empty-bin"
    empty_path.mkdir()

    monkeypatch.setenv("PATH", str(empty_path))
    monkeypatch.setenv("MPICC", "missing-mpicc")
    monkeypatch.setenv("P3_MPI_LAUNCHER", "missing-mpirun")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(RUNNER_PATH),
            "--root",
            str(repository),
            "--timeout",
            "5",
        ],
    )

    result = mpi_runner.main()

    assert result == 1

    report_path = repository / mpi_runner.REPORT_RELATIVE
    assert report_path.is_file()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["validation"] == "FAIL"
    assert report["native_build"]["status"] == "FAIL"

    for relative in (
        mpi_runner.BUILD_LOG_RELATIVE,
        mpi_runner.STDOUT_RELATIVE,
        mpi_runner.STDERR_RELATIVE,
    ):
        path = repository / relative
        assert path.is_file()
        assert path.stat().st_size > 0


def test_main_fails_closed_when_provenance_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    source = repository / mpi_runner.SOURCE_RELATIVE
    source.parent.mkdir(parents=True)
    source.write_text("/* test-only source placeholder */\n", encoding="utf-8")

    monkeypatch.delenv("P3_RUN_ID", raising=False)
    monkeypatch.delenv("P3_SOURCE_COMMIT", raising=False)
    monkeypatch.delenv("P3_WORKFLOW_RUN_ID", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    monkeypatch.delenv("GITHUB_RUN_ATTEMPT", raising=False)

    monkeypatch.setattr(
        sys,
        "argv",
        [str(RUNNER_PATH), "--root", str(repository)],
    )

    result = mpi_runner.main()

    assert result == 1
    report_path = repository / mpi_runner.REPORT_RELATIVE
    assert report_path.is_file()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["validation"] == "FAIL"
    assert report["provenance"]["commit_verified"] is False
    assert report["provenance"]["run_id_verified"] is False
    assert report["provenance"]["workflow_run_id_verified"] is False
