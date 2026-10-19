"""Adversarial tests for the P2 SHA-256 manifest generator."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tools.generate_manifest import build_manifest, collect_files


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_build_manifest_generates_expected_hash_and_path(tmp_path: Path):
    source = tmp_path / "sample.py"
    source.write_text("value = 42\n", encoding="utf-8")

    expected_hash = sha256_text("value = 42\n")
    content = build_manifest(tmp_path, [source])

    assert "# File count: 1" in content
    assert f"{expected_hash}  sample.py" in content


def test_build_manifest_is_deterministic(tmp_path: Path):
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("a = 1\n", encoding="utf-8")
    second.write_text("b = 2\n", encoding="utf-8")

    assert build_manifest(tmp_path, [first, second]) == build_manifest(
        tmp_path, [second, first]
    )


def test_build_manifest_rejects_duplicate_paths(tmp_path: Path):
    source = tmp_path / "sample.py"
    source.write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate"):
        build_manifest(tmp_path, [source, source])


def test_build_manifest_rejects_outside_path(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside manifest root"):
        build_manifest(root, [outside])


def test_build_manifest_rejects_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        build_manifest(tmp_path, [tmp_path / "missing.py"])


@pytest.mark.parametrize(
    "relative",
    [
        "__pycache__/module.py",
        ".pytest_cache/state",
        "reports/test.log",
        "results/output.json",
        "module.pyc",
        "module.pyo",
        "MANIFEST.txt",
        "SHA256SUMS.txt",
    ],
)
def test_build_manifest_rejects_excluded_paths(
    tmp_path: Path, relative: str
):
    source = tmp_path / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("excluded\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Excluded"):
        build_manifest(tmp_path, [source])


def test_collect_files_returns_sorted_inventory(tmp_path: Path):
    (tmp_path / "z.py").write_text("z = 1\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("a = 1\n", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.py").write_text("b = 1\n", encoding="utf-8")

    files = collect_files(tmp_path, tmp_path / "MANIFEST.txt")
    names = [p.relative_to(tmp_path).as_posix() for p in files]

    assert names == ["a.py", "nested/b.py", "z.py"]


def test_collect_files_excludes_manifest_and_reports(tmp_path: Path):
    (tmp_path / "source.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "MANIFEST.txt").write_text("old\n", encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "junit.xml").write_text("<testsuite/>\n", encoding="utf-8")

    files = collect_files(tmp_path, tmp_path / "MANIFEST.txt")

    assert {p.relative_to(tmp_path).as_posix() for p in files} == {
        "source.py"
    }


def test_build_manifest_rejects_symbolic_file(tmp_path: Path):
    target = tmp_path / "target.py"
    target.write_text("value = 1\n", encoding="utf-8")
    link = tmp_path / "link.py"

    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symbolic links are unavailable")

    with pytest.raises(ValueError, match="Symbolic"):
        build_manifest(tmp_path, [link])


def test_manifest_hash_changes_when_file_changes(tmp_path: Path):
    source = tmp_path / "sample.py"
    source.write_text("value = 1\n", encoding="utf-8")
    first = build_manifest(tmp_path, [source])

    source.write_text("value = 2\n", encoding="utf-8")
    second = build_manifest(tmp_path, [source])

    assert first != second
