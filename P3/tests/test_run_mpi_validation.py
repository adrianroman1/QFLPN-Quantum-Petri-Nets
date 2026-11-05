#!/usr/bin/env python3
"""Tests for the P3 fail-closed native MPI validation runner."""

from __future__ import annotations

import importlib.util
import json
import math
import struct
import subprocess
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
    rows, columns = 8, 8
    row_ptr, col_idx, values, vector = mpi_runner.build_test_matrix(
        rows, columns
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
        "<8s3Q", magic, declared_rows, status, reserved
    )
    payload = struct.pack(f"<{len(values)}d", *values) if values else b""
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


def test_valid_provenance_accepts_default_attempt() -> None:
    mpi_runner.validate_provenance(
        VALID_RUN_ID, VALID_COMMIT, VALID_WORKFLOW_RUN_ID
    )


def test_valid_provenance_accepts_explicit_attempt() -> None:
    mpi_runner.validate_provenance(
        VALID_RUN_ID, VALID_COMMIT, VALID_WORKFLOW_RUN_ID, VALID_ATTEMPT
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
            run_id, commit, workflow_id, attempt
        )


def test_build_test_matrix_is_deterministic() -> None:
    assert mpi_runner.build_test_matrix(32, 24) == (
        mpi_runner.build_test_matrix(32, 24)
    )


def test_build_test_matrix_produces_valid_csr() -> None:
    rows, columns = 32, 24
    row_ptr, col_idx, values, vector = mpi_runner.build_test_matrix(
        rows, columns
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
    rows: int, columns: int
) -> None:
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.build_test_matrix(rows, columns)


def test_encode_request_has_expected_header_and_payload() -> None:
    rows, columns, row_ptr, col_idx, values, vector = small_matrix()
    payload = mpi_runner.encode_request(
        rows, columns, row_ptr, col_idx, values, vector
    )
    (
        magic, declared_rows, declared_columns, nnz,
        vector_length, flags, reserved,
    ) = struct.unpack("<8s6Q", payload[:56])

    assert magic == b"P3SPMV01"
    assert declared_rows == rows
    assert declared_columns == columns
    assert nnz == len(col_idx)
    assert vector_length == columns
    assert flags == reserved == 0

    expected_length = (
        56 + (rows + 1) * 8 + len(col_idx) * 8
        + len(values) * 8 + columns * 8
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


def test_compare_results_reports_identical_vectors() -> None:
    values = [0.0, 1.0, -2.5, 8.125]
    result = mpi_runner.compare_results(values, values)
    assert result["max_absolute_error"] == 0.0
    assert result["max_relative_error"] == 0.0
    assert result["max_reference_magnitude"] == 8.125


def test_compare_results_reports_errors_inside_tolerance() -> None:
    reference = [1.0, 2.0, 0.0]
    actual = [1.0 + 1e-13, 2.0 - 1e-13, 1e-13]
    result = mpi_runner.compare_results(actual, reference)
    metrics, passed = mpi_runner.compare_results_with_status(
        actual, reference
    )
    assert passed is True
    assert metrics == result


def test_compare_results_retains_metrics_for_numerical_mismatch() -> None:
    metrics, passed = mpi_runner.compare_results_with_status(
        [1.0, 2.0, 3.01],
        [1.0, 2.0, 3.0],
    )
    assert passed is False
    assert metrics["max_absolute_error"] == pytest.approx(0.01)
    assert metrics["max_relative_error"] > 0.0
    assert metrics["max_reference_magnitude"] == 3.0


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
    tmp_path: Path, payload: bytes
) -> None:
    path = tmp_path / "invalid-response.p3mpi"
    path.write_bytes(payload)
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 1)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_decode_response_rejects_non_finite_values(
    tmp_path: Path, value: float
) -> None:
    path = tmp_path / "non-finite.p3mpi"
    write_response(path, [value])
    with pytest.raises(mpi_runner.ValidationError):
        mpi_runner.decode_response(path, 1)


def test_process_outcome_distinguishes_exit_15_from_sigterm() -> None:
    normal_exit = mpi_runner._process_outcome(15, False, None)
    signal_exit = mpi_runner._process_outcome(-15, False, None)

    assert normal_exit["type"] == "EXIT_CODE"
    assert normal_exit["exit_code"] == 15
    assert normal_exit["signal"] is None

    assert signal_exit["type"] == "SIGNAL"
    assert signal_exit["exit_code"] is None
    assert signal_exit["signal"] == 15
    assert signal_exit["signal_name"] == "SIGTERM"


def test_process_outcome_classifies_timeout_and_launch_error() -> None:
    timeout = mpi_runner._process_outcome(None, True, None)
    launch = mpi_runner._process_outcome(
        None, False, "FileNotFoundError: mpirun"
    )
    not_run = mpi_runner._process_outcome(None, False, None, not_run=True)

    assert timeout["type"] == "TIMEOUT"
    assert launch["type"] == "LAUNCH_ERROR"
    assert not_run["type"] == "NOT_RUN"


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


def test_make_report_sets_unexecuted_comparison_metrics_to_null() -> None:
    arguments = valid_report_arguments()
    arguments.update(
        comparison={},
        comparison_executed=False,
        comparison_passed=False,
        validation="FAIL",
        execution_outcome=mpi_runner._process_outcome(15, False, None),
    )
    report = mpi_runner.make_report(**arguments)
    numerical = report["numerical_validation"]

    assert report["validation"] == "FAIL"
    assert numerical["comparison_executed"] is False
    assert numerical["comparison"] == "NOT_RUN"
    assert numerical["max_absolute_error"] is None
    assert numerical["max_relative_error"] is None
    assert numerical["max_reference_magnitude"] is None


def test_make_report_preserves_metrics_when_comparison_fails() -> None:
    arguments = valid_report_arguments()
    arguments.update(
        comparison={
            "max_absolute_error": 0.01,
            "max_relative_error": 0.003333,
            "max_reference_magnitude": 3.0,
        },
        comparison_executed=True,
        comparison_passed=False,
        validation="FAIL",
    )
    report = mpi_runner.make_report(**arguments)
    numerical = report["numerical_validation"]

    assert numerical["comparison_executed"] is True
    assert numerical["comparison"] == "FAIL"
    assert numerical["max_absolute_error"] == pytest.approx(0.01)
    assert numerical["max_relative_error"] == pytest.approx(0.003333)


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
    arguments.update(
        timed_out=True,
        execution_outcome=mpi_runner._process_outcome(None, True, None),
    )
    report = mpi_runner.make_report(**arguments)
    assert report["validation"] == "FAIL"
    assert report["execution"]["status"] == "FAIL"
    assert report["execution"]["outcome_type"] == "TIMEOUT"


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


def prepare_main_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    repository = tmp_path / "repository"
    source = repository / mpi_runner.SOURCE_RELATIVE
    source.parent.mkdir(parents=True)
    source.write_text(
        "/* test-only native MPI source placeholder */\n",
        encoding="utf-8",
    )
    valid_environment(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(RUNNER_PATH), "--root", str(repository), "--timeout", "5"
        ],
    )
    return repository


def install_fake_tools(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    mpi_returncode: int = 0,
    mpi_error: BaseException | None = None,
    actual_values: list[float] | None = None,
) -> tuple[str, str]:
    compiler = "/test-tools/mpicc"
    launcher = "/test-tools/mpirun"
    executable = repository / mpi_runner.EXECUTABLE_RELATIVE

    monkeypatch.setenv("MPICC", compiler)
    monkeypatch.setenv("P3_MPI_LAUNCHER", launcher)

    def fake_resolve_tool(value: str, label: str) -> str:
        if value in (compiler, launcher):
            return value
        raise mpi_runner.ValidationError(f"Unexpected tool: {value}")

    def fake_command_version(command, environment):
        return "MPI test tool version"

    def fake_run_command(command, timeout_seconds, environment):
        if command[0] == compiler:
            executable.parent.mkdir(parents=True, exist_ok=True)
            executable.write_bytes(b"fake executable")
            executable.chmod(0o755)
            return subprocess.CompletedProcess(command, 0, "compiler ok\n", "")

        if command[0] == launcher:
            if mpi_error is not None:
                raise mpi_error
            if mpi_returncode != 0:
                return subprocess.CompletedProcess(
                    command, mpi_returncode, "mpi stdout", "mpi stderr"
                )

            response = Path(command[-1])
            rows, columns = 128, 128
            row_ptr, col_idx, values, vector = (
                mpi_runner.build_test_matrix(rows, columns)
            )
            reference = mpi_runner.sequential_csr_reference(
                rows, row_ptr, col_idx, values, vector
            )
            output = reference if actual_values is None else actual_values
            write_response(response, output)
            return subprocess.CompletedProcess(
                command, 0, "MPI ok\n", ""
            )

        raise AssertionError(f"Unexpected command: {command!r}")

    monkeypatch.setattr(mpi_runner, "resolve_tool", fake_resolve_tool)
    monkeypatch.setattr(mpi_runner, "command_version", fake_command_version)
    monkeypatch.setattr(mpi_runner, "run_command", fake_run_command)
    monkeypatch.setattr(mpi_runner, "sha256_file", lambda path: "c" * 64)
    return compiler, launcher


def read_report(repository: Path) -> dict:
    path = repository / mpi_runner.REPORT_RELATIVE
    assert path.is_file()
    return json.loads(path.read_text(encoding="utf-8"))


def test_main_successful_build_execution_and_comparison(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = prepare_main_repository(tmp_path, monkeypatch)
    install_fake_tools(repository, monkeypatch)

    assert mpi_runner.main() == 0
    report = read_report(repository)

    assert report["validation"] == "PASS"
    assert report["native_build"]["status"] == "PASS"
    assert report["execution"]["status"] == "PASS"
    assert report["execution"]["outcome_type"] == "EXIT_CODE"
    assert report["execution"]["exit_code"] == 0
    assert report["execution"]["duration_seconds"] >= 0
    assert report["execution"]["command"]
    assert report["execution"]["launcher_metadata"]["path"]
    assert report["numerical_validation"]["comparison_executed"] is True
    assert report["numerical_validation"]["comparison"] == "PASS"


@pytest.mark.parametrize(
    ("returncode", "expected_type", "expected_exit", "expected_signal"),
    [
        (15, "EXIT_CODE", 15, None),
        (-15, "SIGNAL", None, 15),
    ],
)
def test_main_classifies_mpi_exit_status_and_signal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    expected_type: str,
    expected_exit: int | None,
    expected_signal: int | None,
) -> None:
    repository = prepare_main_repository(tmp_path, monkeypatch)
    install_fake_tools(
        repository, monkeypatch, mpi_returncode=returncode
    )

    assert mpi_runner.main() == 1
    report = read_report(repository)
    execution = report["execution"]
    numerical = report["numerical_validation"]

    assert execution["outcome_type"] == expected_type
    assert execution["exit_code"] == expected_exit
    assert execution["signal"] == expected_signal
    assert execution["returncode"] == returncode
    assert numerical["comparison_executed"] is False
    assert numerical["comparison"] == "NOT_RUN"
    assert numerical["max_absolute_error"] is None
    assert numerical["max_relative_error"] is None
    assert numerical["max_reference_magnitude"] is None


def test_main_records_mpi_timeout_and_duration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = prepare_main_repository(tmp_path, monkeypatch)
    install_fake_tools(
        repository,
        monkeypatch,
        mpi_error=subprocess.TimeoutExpired(
            ["/test-tools/mpirun", "-np", "2"], 5,
            output=b"partial out", stderr=b"partial err"
        ),
    )

    assert mpi_runner.main() == 1
    report = read_report(repository)
    execution = report["execution"]

    assert execution["outcome_type"] == "TIMEOUT"
    assert execution["timeout"] is True
    assert execution["duration_seconds"] is not None
    assert execution["duration_seconds"] >= 0
    assert execution["command"]
    assert report["numerical_validation"]["comparison_executed"] is False


def test_main_records_mpi_launch_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = prepare_main_repository(tmp_path, monkeypatch)
    install_fake_tools(
        repository,
        monkeypatch,
        mpi_error=FileNotFoundError("mpirun executable disappeared"),
    )

    assert mpi_runner.main() == 1
    report = read_report(repository)
    execution = report["execution"]

    assert execution["outcome_type"] == "LAUNCH_ERROR"
    assert execution["exit_code"] is None
    assert execution["signal"] is None
    assert "FileNotFoundError" in execution["launch_error"]
    assert execution["duration_seconds"] is not None
    assert report["numerical_validation"]["max_absolute_error"] is None


def test_main_preserves_numerical_mismatch_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = prepare_main_repository(tmp_path, monkeypatch)
    install_fake_tools(
        repository, monkeypatch, actual_values=[999.0] * 128
    )

    assert mpi_runner.main() == 1
    report = read_report(repository)
    numerical = report["numerical_validation"]

    assert report["validation"] == "FAIL"
    assert numerical["status"] == "FAIL"
    assert numerical["comparison_executed"] is True
    assert numerical["comparison"] == "FAIL"
    assert numerical["max_absolute_error"] is not None
    assert numerical["max_absolute_error"] > 0
    assert numerical["max_relative_error"] is not None


def test_main_fails_closed_when_mpicc_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = prepare_main_repository(tmp_path, monkeypatch)
    empty_path = tmp_path / "empty-bin"
    empty_path.mkdir()
    monkeypatch.setenv("PATH", str(empty_path))
    monkeypatch.setenv("MPICC", "missing-mpicc")
    monkeypatch.setenv("P3_MPI_LAUNCHER", "missing-mpirun")

    assert mpi_runner.main() == 1
    report = read_report(repository)
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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    source = repository / mpi_runner.SOURCE_RELATIVE
    source.parent.mkdir(parents=True)
    source.write_text("/* test source */\n", encoding="utf-8")

    for name in (
        "P3_RUN_ID", "P3_SOURCE_COMMIT", "P3_WORKFLOW_RUN_ID",
        "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setattr(
        sys, "argv", [str(RUNNER_PATH), "--root", str(repository)]
    )

    assert mpi_runner.main() == 1
    report = read_report(repository)
    assert report["validation"] == "FAIL"
    assert report["provenance"]["commit_verified"] is False
    assert report["provenance"]["run_id_verified"] is False
    assert report["provenance"]["workflow_run_id_verified"] is False


def test_main_rejects_compiler_nonzero_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = prepare_main_repository(tmp_path, monkeypatch)
    compiler = "/test-tools/mpicc"
    monkeypatch.setenv("MPICC", compiler)
    monkeypatch.setenv("P3_MPI_LAUNCHER", "/test-tools/mpirun")
    monkeypatch.setattr(mpi_runner, "resolve_tool", lambda value, label: value)
    monkeypatch.setattr(
        mpi_runner, "command_version", lambda command, environment: "version"
    )

    def failed_compile(command, timeout_seconds, environment):
        return subprocess.CompletedProcess(
            command, 2, "", "intentional compile error"
        )

    monkeypatch.setattr(mpi_runner, "run_command", failed_compile)
    assert mpi_runner.main() == 1
    report = read_report(repository)
    assert report["validation"] == "FAIL"
    assert report["native_build"]["status"] == "FAIL"
    assert report["native_build"]["exit_code"] == 2
    assert not (repository / mpi_runner.RESPONSE_RELATIVE).exists()


def test_main_removes_stale_response_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = prepare_main_repository(tmp_path, monkeypatch)
    response = repository / mpi_runner.RESPONSE_RELATIVE
    response.parent.mkdir(parents=True, exist_ok=True)
    write_response(response, [1.0] * 128)

    compiler = "/test-tools/mpicc"
    launcher = "/test-tools/mpirun"
    executable = repository / mpi_runner.EXECUTABLE_RELATIVE
    monkeypatch.setenv("MPICC", compiler)
    monkeypatch.setenv("P3_MPI_LAUNCHER", launcher)
    monkeypatch.setattr(mpi_runner, "resolve_tool", lambda value, label: value)
    monkeypatch.setattr(
        mpi_runner, "command_version", lambda command, environment: "version"
    )

    def fake_run(command, timeout_seconds, environment):
        if command[0] == compiler:
            executable.parent.mkdir(parents=True, exist_ok=True)
            executable.write_bytes(b"fake executable")
            executable.chmod(0o755)
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[0] == launcher:
            assert not response.exists()
            return subprocess.CompletedProcess(command, 9, "", "failed")
        raise AssertionError(command)

    monkeypatch.setattr(mpi_runner, "run_command", fake_run)
    monkeypatch.setattr(mpi_runner, "sha256_file", lambda path: "f" * 64)

    assert mpi_runner.main() == 1
    assert not response.exists()
    report = read_report(repository)
    assert report["validation"] == "FAIL"
    assert report["execution"]["exit_code"] == 9
