"""Fail-closed tests for P2 report and manifest infrastructure."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.validate_reports import validate_pytest_report
from tools.generate_manifest import collect_files, build_manifest
from tools.verify_sha256 import verify_manifest


def valid_report() -> dict:
    return {
        "schema_version": 1,
        "runner": "pytest",
        "command": ["python", "-m", "pytest"],
        "python_version": "3.11",
        "exit_code": 0,
        "status": "PASS",
        "stdout": "================ 10 passed in 1.00s ================",
        "stderr": "",
    }


def test_valid_pytest_report_is_accepted():
    assert validate_pytest_report(valid_report()) == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "FAIL"),
        ("status", "UNKNOWN"),
        ("exit_code", 1),
        ("exit_code", True),
        ("runner", "other"),
        ("schema_version", 2),
        ("stdout", ""),
        ("stderr", "unexpected error"),
    ],
)
def test_invalid_pytest_report_is_rejected(field, value):
    report = valid_report()
    report[field] = value

    assert validate_pytest_report(report)


def test_report_rejects_missing_required_field():
    report = valid_report()
    del report["exit_code"]

    assert validate_pytest_report(report)


def test_report_rejects_failed_pytest_summary():
    report = valid_report()
    report["stdout"] = (
        "================ 9 passed, 1 failed in 1.00s ================"
    )

    assert validate_pytest_report(report)


def test_manifest_excludes_cache_and_bytecode(tmp_path: Path):
    source = tmp_path / "source.py"
    source.write_text("value = 1\n", encoding="utf-8")

    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "source.pyc").write_bytes(b"cache")

    pytest_cache = tmp_path / ".pytest_cache"
    pytest_cache.mkdir()
    (pytest_cache / "state").write_text("volatile")

    files = collect_files(tmp_path, tmp_path / "MANIFEST.txt")
    names = {
        path.relative_to(tmp_path).as_posix()
        for path in files
    }

    assert names == {"source.py"}


def test_manifest_detects_missing_versioned_file(tmp_path: Path):
    source = tmp_path / "source.py"
    source.write_text("value = 1\n", encoding="utf-8")

    omitted = tmp_path / "omitted.py"
    omitted.write_text("value = 2\n", encoding="utf-8")

    manifest = tmp_path / "MANIFEST.txt"

    files = collect_files(tmp_path, manifest)
    files = [path for path in files if path.name != "omitted.py"]

    manifest.write_text(
        build_manifest(tmp_path, files),
        encoding="utf-8",
    )

    _, failed, errors = verify_manifest(tmp_path, manifest)

    assert failed > 0
    assert any("omitted.py" in error for error in errors)


def test_manifest_detects_modified_file(tmp_path: Path):
    source = tmp_path / "source.py"
    source.write_text("value = 1\n", encoding="utf-8")

    manifest = tmp_path / "MANIFEST.txt"
    files = collect_files(tmp_path, manifest)

    manifest.write_text(
        build_manifest(tmp_path, files),
        encoding="utf-8",
    )

    source.write_text("value = 999\n", encoding="utf-8")

    _, failed, errors = verify_manifest(tmp_path, manifest)

    assert failed > 0
    assert any("SHA-256 mismatch" in error for error in errors)


def test_manifest_detects_duplicate_entries(tmp_path: Path):
    source = tmp_path / "source.py"
    source.write_text("value = 1\n", encoding="utf-8")

    manifest = tmp_path / "MANIFEST.txt"
    files = collect_files(tmp_path, manifest)
    content = build_manifest(tmp_path, files)

    entry = content.splitlines()[-1]

    manifest.write_text(
        content + entry + "\n",
        encoding="utf-8",
    )

    _, failed, errors = verify_manifest(tmp_path, manifest)

    assert failed > 0
    assert any("duplicate" in error.lower() for error in errors)
