"""Fail-closed tests for P2 report and manifest infrastructure."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.validate_reports import (
    validate_pytest_report,
    validate_pytest_json,
    validate_junit,
)

from tools.generate_manifest import (
    collect_files,
    build_manifest,
)

from tools.verify_sha256 import verify_manifest


def valid_report() -> dict:
    return {
        "schema_version": 2,
        "runner": "pytest",
        "command": [
            "python",
            "-m",
            "pytest",
            "P2/tests",
        ],
        "python_version": "3.11.9",
        "working_directory": "/workspace/P2",
        "test_directory": "/workspace/P2/tests",
        "junit_report": "reports/junit.xml",
        "exit_code": 0,
        "status": "PASS",
        "stdout": (
            "============================== "
            "10 passed =============================="
        ),
        "stderr": "",
    }


def write_report(
    tmp_path: Path,
    report: dict,
) -> Path:
    path = tmp_path / "pytest-run.json"

    path.write_text(
        json.dumps(report, allow_nan=True),
        encoding="utf-8",
    )

    return path


def write_junit(
    tmp_path: Path,
    content: str,
) -> Path:
    path = tmp_path / "junit.xml"

    path.write_text(
        content,
        encoding="utf-8",
    )

    return path


def valid_junit_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="2" failures="0" errors="0" skipped="0">
    <testsuite name="P2" tests="2" failures="0" errors="0" skipped="0">
        <testcase classname="P2.test_one" name="test_one"/>
        <testcase classname="P2.test_two" name="test_two"/>
    </testsuite>
</testsuites>
"""


def test_valid_schema_v2_report_is_accepted():
    assert validate_pytest_report(valid_report()) == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 1),
        ("schema_version", True),
        ("schema_version", "2"),
        ("status", "FAIL"),
        ("status", "UNKNOWN"),
        ("exit_code", 1),
        ("exit_code", True),
        ("exit_code", "0"),
        ("runner", "other"),
        ("command", []),
        ("command", "python -m pytest"),
        ("command", ["python", ""]),
        ("python_version", ""),
        ("python_version", None),
        ("working_directory", ""),
        ("working_directory", None),
        ("test_directory", 7),
        ("junit_report", ""),
        ("junit_report", None),
        ("stdout", None),
        ("stdout", ""),
        ("stderr", None),
    ],
)
def test_invalid_report_fields_are_rejected(
    field: str,
    value,
):
    report = valid_report()
    report[field] = value

    assert validate_pytest_report(report)


def test_report_rejects_missing_required_field():
    report = valid_report()
    del report["exit_code"]

    errors = validate_pytest_report(report)

    assert errors
    assert any(
        "exit_code" in error
        for error in errors
    )


def test_report_rejects_non_object_root():
    assert validate_pytest_report([])


def test_report_rejects_no_tests_ran():
    report = valid_report()
    report["stdout"] = "no tests ran"

    errors = validate_pytest_report(report)

    assert any(
        "no tests ran" in error
        for error in errors
    )


def test_report_rejects_failure_summary():
    report = valid_report()
    report["stdout"] = "10 passed, 1 failed"

    errors = validate_pytest_report(report)

    assert any(
        "pytest summary reports failures or errors" in error
        for error in errors
    )


def test_report_rejects_error_summary():
    report = valid_report()
    report["stdout"] = "10 passed, 1 error"

    errors = validate_pytest_report(report)

    assert any(
        "pytest summary reports failures or errors" in error
        for error in errors
    )


def test_report_allows_failure_word_outside_summary():
    report = valid_report()
    report["stdout"] = (
        "Test named test_failed_state passed\n"
        "============================== 10 passed "
        "=============================="
    )

    assert validate_pytest_report(report) == []


def test_report_rejects_non_finite_numeric_value():
    report = valid_report()
    report["unexpected_value"] = float("nan")

    errors = validate_pytest_report(report)

    assert any(
        "non-finite" in error
        for error in errors
    )


def test_json_reader_accepts_valid_report(tmp_path: Path):
    path = write_report(
        tmp_path,
        valid_report(),
    )

    assert validate_pytest_json(path) == []


def test_json_reader_rejects_malformed_json(tmp_path: Path):
    path = tmp_path / "pytest-run.json"

    path.write_text(
        '{"schema_version": 2,',
        encoding="utf-8",
    )

    assert validate_pytest_json(path)


def test_json_reader_rejects_nan_constant(tmp_path: Path):
    path = tmp_path / "pytest-run.json"

    path.write_text(
        '{"value": NaN}',
        encoding="utf-8",
    )

    assert validate_pytest_json(path)


def test_json_reader_rejects_missing_file(tmp_path: Path):
    path = tmp_path / "missing.json"

    assert validate_pytest_json(path)


# ---------------------------------------------------------
# JUnit adversarial validation
# ---------------------------------------------------------


def test_junit_accepts_valid_report(tmp_path: Path):
    path = write_junit(
        tmp_path,
        valid_junit_xml(),
    )

    assert validate_junit(path) == []


def test_junit_rejects_missing_file(tmp_path: Path):
    path = tmp_path / "missing.xml"

    errors = validate_junit(path)

    assert errors
    assert any(
        "does not exist" in error
        for error in errors
    )


def test_junit_rejects_malformed_xml(tmp_path: Path):
    path = write_junit(
        tmp_path,
        "<testsuites><testsuite>",
    )

    assert validate_junit(path)


def test_junit_rejects_unexpected_root(tmp_path: Path):
    path = write_junit(
        tmp_path,
        "<unexpected/>",
    )

    errors = validate_junit(path)

    assert any(
        "Unexpected JUnit root" in error
        for error in errors
    )


def test_junit_rejects_zero_tests(tmp_path: Path):
    path = write_junit(
        tmp_path,
        """<testsuite tests="0" failures="0" errors="0"/>""",
    )

    errors = validate_junit(path)

    assert any(
        "zero tests" in error
        for error in errors
    )


def test_junit_rejects_failure_count(tmp_path: Path):
    path = write_junit(
        tmp_path,
        """<testsuite tests="1" failures="1" errors="0">
        <testcase name="test_failure">
            <failure message="failure"/>
        </testcase>
        </testsuite>""",
    )

    errors = validate_junit(path)

    assert any(
        "failures" in error
        for error in errors
    )


def test_junit_rejects_error_count(tmp_path: Path):
    path = write_junit(
        tmp_path,
        """<testsuite tests="1" failures="0" errors="1">
        <testcase name="test_error">
            <error message="error"/>
        </testcase>
        </testsuite>""",
    )

    errors = validate_junit(path)

    assert any(
        "errors" in error
        for error in errors
    )


def test_junit_rejects_invalid_numeric_counter(tmp_path: Path):
    path = write_junit(
        tmp_path,
        """<testsuite tests="invalid" failures="0" errors="0"/>""",
    )

    errors = validate_junit(path)

    assert any(
        "invalid numeric counters" in error
        for error in errors
    )


def test_junit_rejects_negative_counter(tmp_path: Path):
    path = write_junit(
        tmp_path,
        """<testsuite tests="-1" failures="0" errors="0"/>""",
    )

    errors = validate_junit(path)

    assert any(
        "must not be negative" in error
        for error in errors
    )


def test_junit_rejects_testcase_count_mismatch(tmp_path: Path):
    path = write_junit(
        tmp_path,
        """<testsuite tests="2" failures="0" errors="0">
        <testcase name="only_one"/>
        </testsuite>""",
    )

    errors = validate_junit(path)

    assert any(
        "does not match testcase elements" in error
        for error in errors
    )


def test_junit_rejects_skipped_count_above_total(tmp_path: Path):
    path = write_junit(
        tmp_path,
        """<testsuite tests="1" failures="0" errors="0" skipped="2">
        <testcase name="test_one"/>
        </testsuite>""",
    )

    errors = validate_junit(path)

    assert any(
        "skipped count exceeds" in error
        for error in errors
    )


# ---------------------------------------------------------
# SHA-256 manifest integrity
# ---------------------------------------------------------


def test_manifest_excludes_cache_and_bytecode(
    tmp_path: Path,
):
    source = tmp_path / "source.py"
    source.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    cache = tmp_path / "__pycache__"
    cache.mkdir()

    (cache / "source.pyc").write_bytes(
        b"cache"
    )

    pytest_cache = tmp_path / ".pytest_cache"
    pytest_cache.mkdir()

    (pytest_cache / "state").write_text(
        "volatile",
        encoding="utf-8",
    )

    files = collect_files(
        tmp_path,
        tmp_path / "MANIFEST.txt",
    )

    names = {
        path.relative_to(tmp_path).as_posix()
        for path in files
    }

    assert names == {"source.py"}


def test_manifest_detects_missing_versioned_file(
    tmp_path: Path,
):
    source = tmp_path / "source.py"
    source.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    omitted = tmp_path / "omitted.py"
    omitted.write_text(
        "value = 2\n",
        encoding="utf-8",
    )

    manifest = tmp_path / "MANIFEST.txt"

    files = collect_files(
        tmp_path,
        manifest,
    )

    files = [
        path
        for path in files
        if path.name != "omitted.py"
    ]

    manifest.write_text(
        build_manifest(tmp_path, files),
        encoding="utf-8",
    )

    _, failed, errors = verify_manifest(
        tmp_path,
        manifest,
    )

    assert failed > 0
    assert any(
        "omitted.py" in error
        for error in errors
    )


def test_manifest_detects_modified_file(
    tmp_path: Path,
):
    source = tmp_path / "source.py"
    source.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    manifest = tmp_path / "MANIFEST.txt"

    files = collect_files(
        tmp_path,
        manifest,
    )

    manifest.write_text(
        build_manifest(tmp_path, files),
        encoding="utf-8",
    )

    source.write_text(
        "value = 999\n",
        encoding="utf-8",
    )

    _, failed, errors = verify_manifest(
        tmp_path,
        manifest,
    )

    assert failed > 0
    assert any(
        "SHA-256 mismatch" in error
        for error in errors
    )


def test_manifest_detects_duplicate_entries(
    tmp_path: Path,
):
    source = tmp_path / "source.py"
    source.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    manifest = tmp_path / "MANIFEST.txt"

    files = collect_files(
        tmp_path,
        manifest,
    )

    content = build_manifest(
        tmp_path,
        files,
    )

    entry = content.splitlines()[-1]

    manifest.write_text(
        content + entry + "\n",
        encoding="utf-8",
    )

    _, failed, errors = verify_manifest(
        tmp_path,
        manifest,
    )

    assert failed > 0
    assert any(
        "duplicate" in error.lower()
        for error in errors
    )
