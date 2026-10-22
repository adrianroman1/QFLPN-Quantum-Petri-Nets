"""Regression tests for the P3 integrity generator."""

import hashlib
import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "generate_integrity.py"
)

SPEC = importlib.util.spec_from_file_location(
    "generate_integrity",
    MODULE_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def create_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "P3"

    (root / "code").mkdir(parents=True)

    (root / "code" / "Example.java").write_text(
        "class Example {}\n",
        encoding="utf-8",
    )

    (root / "README.md").write_text(
        "P3 integrity fixture\n",
        encoding="utf-8",
    )

    return root


def read_checksums(root: Path) -> dict[str, str]:
    checksum_file = root / "SHA256SUMS.txt"

    entries = {}

    for line in checksum_file.read_text(
        encoding="utf-8"
    ).splitlines():
        digest, filename = line.split("  ", 1)
        entries[filename] = digest

    return entries


def test_write_then_check_passes(tmp_path: Path):
    root = create_fixture(tmp_path)

    assert MODULE.generate(root, write=True)
    assert MODULE.generate(root, write=False)

    assert (root / "MANIFEST.txt").is_file()
    assert (root / "SHA256SUMS.txt").is_file()


def test_manifest_is_sorted(tmp_path: Path):
    root = create_fixture(tmp_path)

    MODULE.generate(root, write=True)

    lines = (
        root / "MANIFEST.txt"
    ).read_text(encoding="utf-8").splitlines()

    names = [
        line
        for line in lines
        if line and not line.startswith("#")
    ]

    assert names == sorted(names)


def test_manifest_excludes_generated_outputs(tmp_path: Path):
    root = create_fixture(tmp_path)

    MODULE.generate(root, write=True)

    manifest = (
        root / "MANIFEST.txt"
    ).read_text(encoding="utf-8")

    assert "MANIFEST.txt" not in manifest
    assert "SHA256SUMS.txt" not in manifest


def test_checksum_contains_manifest_hash(tmp_path: Path):
    root = create_fixture(tmp_path)

    MODULE.generate(root, write=True)

    entries = read_checksums(root)

    expected = hashlib.sha256(
        (root / "MANIFEST.txt").read_bytes()
    ).hexdigest()

    assert entries["MANIFEST.txt"] == expected


def test_checksum_contains_source_hash(tmp_path: Path):
    root = create_fixture(tmp_path)

    MODULE.generate(root, write=True)

    entries = read_checksums(root)

    expected = hashlib.sha256(
        (root / "README.md").read_bytes()
    ).hexdigest()

    assert entries["README.md"] == expected


def test_check_fails_after_source_change(tmp_path: Path):
    root = create_fixture(tmp_path)

    MODULE.generate(root, write=True)

    (root / "README.md").write_text(
        "modified content\n",
        encoding="utf-8",
    )

    assert not MODULE.generate(root, write=False)


def test_regeneration_updates_checksum(tmp_path: Path):
    root = create_fixture(tmp_path)

    MODULE.generate(root, write=True)

    previous = (
        root / "SHA256SUMS.txt"
    ).read_bytes()

    (root / "README.md").write_text(
        "new content\n",
        encoding="utf-8",
    )

    MODULE.generate(root, write=True)

    current = (
        root / "SHA256SUMS.txt"
    ).read_bytes()

    assert previous != current
    assert MODULE.generate(root, write=False)


def test_build_directories_are_excluded(tmp_path: Path):
    root = create_fixture(tmp_path)

    (root / "target").mkdir()
    (root / "target" / "ignored.class").write_text(
        "ignored",
        encoding="utf-8",
    )

    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "ignored.pyc").write_bytes(b"x")

    MODULE.generate(root, write=True)

    manifest = (
        root / "MANIFEST.txt"
    ).read_text(encoding="utf-8")

    assert "ignored.class" not in manifest
    assert "ignored.pyc" not in manifest


def test_symlink_is_not_inventoried(tmp_path: Path):
    root = create_fixture(tmp_path)

    external = tmp_path / "outside.txt"
    external.write_text("outside", encoding="utf-8")

    try:
        (root / "outside-link").symlink_to(external)
    except OSError:
        return

    MODULE.generate(root, write=True)

    manifest = (
        root / "MANIFEST.txt"
    ).read_text(encoding="utf-8")

    assert "outside-link" not in manifest
