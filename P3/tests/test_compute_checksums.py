"""Regression tests for the P1-compatible P3 checksum generator."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "compute_checksums.py"
)

SPEC = importlib.util.spec_from_file_location(
    "p3_compute_checksums",
    MODULE_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def create_repository(tmp_path: Path) -> Path:
    """Create a minimal repository fixture containing a P3 directory."""
    root = tmp_path / "repository"

    (root / "P3" / "tools").mkdir(parents=True)
    (root / "P3" / "tests").mkdir(parents=True)
    (root / "P3" / "README.md").write_text(
        "P3 integrity fixture\n",
        encoding="utf-8",
    )
    (root / "P3" / "tools" / "example.py").write_text(
        "VALUE = 42\n",
        encoding="utf-8",
    )
    (root / "P3" / "tests" / "example_test.py").write_text(
        "def test_example():\n    assert True\n",
        encoding="utf-8",
    )

    return root


def read_manifest(root: Path) -> list[str]:
    return (
        root / "P3" / "MANIFEST.txt"
    ).read_text(encoding="utf-8").splitlines()


def read_checksums(root: Path) -> dict[str, str]:
    path = root / "P3" / "SHA256SUMS.txt"
    result: dict[str, str] = {}

    for line in path.read_text(encoding="ascii").splitlines():
        digest, relative = line.split("  ", 1)
        result[relative] = digest

    return result


def test_inventory_contains_repository_relative_p3_paths(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    files = MODULE.inventory_files(root)
    paths = [
        path.relative_to(root).as_posix()
        for path in files
    ]

    assert paths == sorted(paths)
    assert paths
    assert all(path.startswith("P3/") for path in paths)


def test_manifest_contains_only_sorted_paths(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    MODULE.generate(root)

    manifest = read_manifest(root)

    assert manifest == sorted(manifest)
    assert len(manifest) == len(set(manifest))
    assert all(manifest)
    assert all(path.startswith("P3/") for path in manifest)
    assert all(not path.startswith("#") for path in manifest)


def test_manifest_has_no_header_or_count_metadata(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    MODULE.generate(root)

    content = (
        root / "P3" / "MANIFEST.txt"
    ).read_text(encoding="utf-8")

    assert content
    assert not content.startswith("#")
    assert "# File count:" not in content


def test_integrity_files_are_excluded_from_manifest(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    MODULE.generate(root)

    manifest = read_manifest(root)

    assert "P3/MANIFEST.txt" not in manifest
    assert "P3/SHA256SUMS.txt" not in manifest


def test_checksum_paths_match_manifest_paths_exactly(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    MODULE.generate(root)

    manifest_paths = set(read_manifest(root))
    checksum_paths = set(read_checksums(root))

    assert checksum_paths == manifest_paths


def test_checksum_file_does_not_hash_manifest(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    MODULE.generate(root)

    checksums = read_checksums(root)

    assert "P3/MANIFEST.txt" not in checksums
    assert "P3/SHA256SUMS.txt" not in checksums


def test_source_hash_matches_standard_library(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    MODULE.generate(root)

    checksums = read_checksums(root)
    source = root / "P3" / "README.md"

    expected = hashlib.sha256(source.read_bytes()).hexdigest()

    assert checksums["P3/README.md"] == expected


def test_every_checksum_line_uses_gnu_sha256_format(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    MODULE.generate(root)

    content = (
        root / "P3" / "SHA256SUMS.txt"
    ).read_text(encoding="ascii")

    assert content.endswith("\n")

    for line in content.splitlines():
        digest, relative = line.split("  ", 1)

        assert len(digest) == 64
        assert all(char in "0123456789abcdef" for char in digest)
        assert relative.startswith("P3/")


def test_generation_is_deterministic(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    MODULE.generate(root)

    first_manifest = (
        root / "P3" / "MANIFEST.txt"
    ).read_bytes()
    first_checksums = (
        root / "P3" / "SHA256SUMS.txt"
    ).read_bytes()

    MODULE.generate(root)

    second_manifest = (
        root / "P3" / "MANIFEST.txt"
    ).read_bytes()
    second_checksums = (
        root / "P3" / "SHA256SUMS.txt"
    ).read_bytes()

    assert first_manifest == second_manifest
    assert first_checksums == second_checksums


def test_source_change_changes_corresponding_checksum(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    MODULE.generate(root)
    before = read_checksums(root)["P3/README.md"]

    (root / "P3" / "README.md").write_text(
        "changed content\n",
        encoding="utf-8",
    )

    MODULE.generate(root)
    after = read_checksums(root)["P3/README.md"]

    expected = hashlib.sha256(
        (root / "P3" / "README.md").read_bytes()
    ).hexdigest()

    assert before != after
    assert after == expected


def test_new_file_is_added_to_both_inventories(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    MODULE.generate(root)

    new_file = root / "P3" / "new_evidence.txt"
    new_file.write_text("new evidence\n", encoding="utf-8")

    MODULE.generate(root)

    assert "P3/new_evidence.txt" in read_manifest(root)
    assert "P3/new_evidence.txt" in read_checksums(root)


def test_cache_and_build_directories_are_excluded(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    ignored_files = (
        root / "P3" / "target" / "generated.class",
        root / "P3" / "__pycache__" / "generated.pyc",
        root / "P3" / ".pytest_cache" / "cache.data",
        root / "P3" / ".mypy_cache" / "cache.data",
        root / "P3" / ".ruff_cache" / "cache.data",
    )

    for path in ignored_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"ignored")

    MODULE.generate(root)

    manifest = read_manifest(root)

    for path in ignored_files:
        relative = path.relative_to(root).as_posix()
        assert relative not in manifest


def test_python_bytecode_files_are_excluded(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    pyc = root / "P3" / "tools" / "ignored.pyc"
    pyo = root / "P3" / "tools" / "ignored.pyo"

    pyc.write_bytes(b"bytecode")
    pyo.write_bytes(b"bytecode")

    MODULE.generate(root)

    manifest = read_manifest(root)

    assert "P3/tools/ignored.pyc" not in manifest
    assert "P3/tools/ignored.pyo" not in manifest


def test_symlinked_files_are_not_inventoried(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    external = tmp_path / "outside.txt"
    external.write_text("outside P3\n", encoding="utf-8")

    link = root / "P3" / "outside-link.txt"

    try:
        link.symlink_to(external)
    except (OSError, NotImplementedError):
        return

    MODULE.generate(root)

    assert "P3/outside-link.txt" not in read_manifest(root)


def test_symlinked_directories_are_not_traversed(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)

    external_dir = tmp_path / "external"
    external_dir.mkdir()
    (external_dir / "secret.txt").write_text(
        "outside P3\n",
        encoding="utf-8",
    )

    link = root / "P3" / "external-link"

    try:
        link.symlink_to(external_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        return

    MODULE.generate(root)

    assert "P3/external-link/secret.txt" not in read_manifest(root)


def test_empty_inventory_is_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    (root / "P3").mkdir(parents=True)

    try:
        MODULE.generate(root)
    except RuntimeError as exc:
        assert "empty P3 integrity inventory" in str(exc)
    else:
        raise AssertionError("Empty inventory must be rejected")


def test_path_outside_repository_is_rejected(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")

    try:
        MODULE.build_inventory_contents(root, [outside])
    except RuntimeError as exc:
        assert "outside repository root" in str(exc)
    else:
        raise AssertionError("Outside-repository path must be rejected")


def test_path_outside_p3_is_rejected(
    tmp_path: Path,
) -> None:
    root = create_repository(tmp_path)
    outside = root / "OTHER" / "outside.txt"
    outside.parent.mkdir()
    outside.write_text("outside P3\n", encoding="utf-8")

    try:
        MODULE.build_inventory_contents(root, [outside])
    except RuntimeError as exc:
        assert "outside P3/" in str(exc)
    else:
        raise AssertionError("Non-P3 path must be rejected")
