"""Adversarial tests for P1 inventory, checksums and evidence validation."""
from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET

import pytest

from P1.tools.compute_checksums import (
    inventory_files,
    sha256_bytes,
)
from P1.tools.verify_final_package import safe_relative
from P1.tools.write_test_results import is_valid_numeric, junit_counts


def test_sha256_helper_matches_standard_library():
    payload = b"P1 deterministic integrity test"
    assert sha256_bytes(payload) == hashlib.sha256(payload).hexdigest()


def test_inventory_is_sorted_and_contains_no_duplicates(tmp_path):
    (tmp_path / "P1" / "code").mkdir(parents=True)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)

    (tmp_path / "P1" / "code" / "z.py").write_text("z\n")
    (tmp_path / "P1" / "code" / "a.py").write_text("a\n")
    (tmp_path / ".github" / "workflows" / "p1.yml").write_text("name: P1\n")

    paths = inventory_files(tmp_path)
    relative = [path.relative_to(tmp_path).as_posix() for path in paths]

    assert relative == sorted(relative)
    assert len(relative) == len(set(relative))


def test_inventory_excludes_self_referential_files(tmp_path):
    (tmp_path / "P1").mkdir()
    (tmp_path / "P1" / "MANIFEST.txt").write_text("stale\n")
    (tmp_path / "P1" / "SHA256SUMS.txt").write_text("stale\n")
    (tmp_path / "P1" / "source.py").write_text("pass\n")

    relative = {
        path.relative_to(tmp_path).as_posix()
        for path in inventory_files(tmp_path)
    }

    assert "P1/source.py" in relative
    assert "P1/MANIFEST.txt" not in relative
    assert "P1/SHA256SUMS.txt" not in relative


def test_inventory_excludes_bytecode_and_cache_directories(tmp_path):
    (tmp_path / "P1" / "__pycache__").mkdir(parents=True)
    (tmp_path / "P1" / ".pytest_cache").mkdir()

    (tmp_path / "P1" / "__pycache__" / "module.pyc").write_bytes(b"x")
    (tmp_path / "P1" / ".pytest_cache" / "cache.bin").write_bytes(b"x")
    (tmp_path / "P1" / "valid.py").write_text("pass\n")

    relative = {
        path.relative_to(tmp_path).as_posix()
        for path in inventory_files(tmp_path)
    }

    assert relative == {"P1/valid.py"}


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/absolute/path",
        "../outside.txt",
        "P1/../outside.txt",
        "P1\\outside.txt",
        "./P1/file.py",
        "P1//file.py",
    ],
)
def test_safe_relative_rejects_unsafe_paths(path):
    assert safe_relative(path) is False


@pytest.mark.parametrize(
    "path",
    [
        "P1/code/qflpn_reference.py",
        "P1/tests/test_p1_integrity.py",
        ".github/workflows/p1-validation.yml",
    ],
)
def test_safe_relative_accepts_normalized_repository_paths(path):
    assert safe_relative(path) is True


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        "0.0",
        "1",
        None,
        float("nan"),
        float("inf"),
        -float("inf"),
    ],
)
def test_evidence_numeric_validator_rejects_invalid_values(value):
    assert is_valid_numeric(value) is False


@pytest.mark.parametrize(
    "value",
    [
        0,
        1,
        -1,
        0.0,
        1.25,
    ],
)
def test_evidence_numeric_validator_accepts_finite_numbers(value):
    assert is_valid_numeric(value) is True


def test_junit_counts_detects_counter_mismatch(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<?xml version="1.0"?>
<testsuite tests="2" failures="0" errors="0" skipped="0">
  <testcase classname="p1" name="test_one"/>
</testsuite>
""",
        encoding="utf-8",
    )

    tests, failures, errors, skipped, names, problems = junit_counts(junit)

    assert tests == 1
    assert failures == 0
    assert errors == 0
    assert skipped == 0
    assert len(names) == 1
    assert any("tests mismatch" in item for item in problems)


def test_junit_counts_accept_consistent_test_report(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<?xml version="1.0"?>
<testsuite tests="2" failures="0" errors="0" skipped="0">
  <testcase classname="p1" name="test_one"/>
  <testcase classname="p1" name="test_two"/>
</testsuite>
""",
        encoding="utf-8",
    )

    tests, failures, errors, skipped, names, problems = junit_counts(junit)

    assert (tests, failures, errors, skipped) == (2, 0, 0, 0)
    assert len(names) == 2
    assert problems == []
