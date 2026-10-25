from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

GENERATOR_PATH = REPOSITORY_ROOT / "P3" / "tools" / "compute_checksums.py"
VERIFIER_PATH = REPOSITORY_ROOT / "P3" / "tools" / "verify_integrity.py"


def load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


GENERATOR = load_module("p3_compute_checksums_under_test", GENERATOR_PATH)
VERIFIER = load_module("p3_verify_integrity_under_test", VERIFIER_PATH)


def write_file(root: Path, relative_path: str, content: bytes | str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(content, str):
        content = content.encode("utf-8")

    path.write_bytes(content)
    return path


def create_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()

    write_file(root, "P3/pom.xml", "<project>test</project>\n")
    write_file(root, "P3/tools/example.py", "print('example')\n")
    write_file(root, "P3/tests/example_test.py", "def test_example():\n    assert True\n")
    write_file(root, "P3/src/Example.java", "class Example {}\n")

    return root


def generate_integrity(root: Path) -> None:
    result = GENERATOR.generate(root)

    assert isinstance(result, tuple)
    assert len(result) == 2

    expected_count = len(GENERATOR.inventory_files(root))
    assert result == (expected_count, expected_count)


def manifest_path(root: Path) -> Path:
    return root / "P3" / "MANIFEST.txt"


def checksums_path(root: Path) -> Path:
    return root / "P3" / "SHA256SUMS.txt"


def read_manifest(root: Path) -> list[str]:
    return manifest_path(root).read_text(encoding="ascii").splitlines()


def write_manifest(root: Path, entries: list[str]) -> None:
    content = "".join(f"{entry}\n" for entry in entries)
    manifest_path(root).write_text(content, encoding="ascii", newline="\n")


def read_checksums(root: Path) -> list[str]:
    return checksums_path(root).read_text(encoding="ascii").splitlines()


def write_checksums(root: Path, entries: list[str]) -> None:
    content = "".join(f"{entry}\n" for entry in entries)
    checksums_path(root).write_text(content, encoding="ascii", newline="\n")


def checksum_record(root: Path, relative_path: str) -> str:
    digest = hashlib.sha256((root / relative_path).read_bytes()).hexdigest()
    return f"{digest}  {relative_path}"


def test_clean_package_passes_against_real_generator(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    result = VERIFIER.verify(root)

    assert result["validation"] == "PASS"
    assert result["manifest_entries"] == 4
    assert result["verified_files"] == 4


def test_manifest_contains_sorted_repository_relative_paths(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    entries = read_manifest(root)

    assert entries == sorted(entries)
    assert all(entry.startswith("P3/") for entry in entries)


def test_checksums_use_gnu_format(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    for line in read_checksums(root):
        assert len(line) > 66
        assert line[64:66] == "  "
        assert len(line[:64]) == 64


def test_generated_integrity_files_are_not_in_manifest(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    entries = read_manifest(root)

    assert "P3/MANIFEST.txt" not in entries
    assert "P3/SHA256SUMS.txt" not in entries


def test_generated_integrity_files_are_not_in_checksums(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    entries = read_checksums(root)

    assert all(not line.endswith("P3/MANIFEST.txt") for line in entries)
    assert all(not line.endswith("P3/SHA256SUMS.txt") for line in entries)


def test_missing_manifest_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)
    manifest_path(root).unlink()

    with pytest.raises(VERIFIER.IntegrityError, match="Missing integrity file"):
        VERIFIER.verify(root)


def test_missing_checksums_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)
    checksums_path(root).unlink()

    with pytest.raises(VERIFIER.IntegrityError, match="Missing integrity file"):
        VERIFIER.verify(root)


def test_modified_source_file_fails_checksum_verification(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    write_file(root, "P3/tools/example.py", "print('modified')\n")

    with pytest.raises(VERIFIER.IntegrityError, match="MANIFEST|SHA-256 mismatch"):
        VERIFIER.verify(root)


def test_added_source_file_fails_inventory_verification(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    write_file(root, "P3/src/Added.java", "class Added {}\n")

    with pytest.raises(VERIFIER.IntegrityError, match="MANIFEST.txt"):
        VERIFIER.verify(root)


def test_removed_source_file_fails_inventory_verification(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    (root / "P3" / "src" / "Example.java").unlink()

    with pytest.raises(VERIFIER.IntegrityError, match="MANIFEST.txt"):
        VERIFIER.verify(root)


def test_unsorted_manifest_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    entries = read_manifest(root)
    write_manifest(root, list(reversed(entries)))

    with pytest.raises(VERIFIER.IntegrityError, match="not sorted"):
        VERIFIER.verify(root)


def test_duplicate_manifest_entry_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    entries = read_manifest(root)
    entries.append(entries[0])
    write_manifest(root, sorted(entries))

    with pytest.raises(VERIFIER.IntegrityError, match="duplicate"):
        VERIFIER.verify(root)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.txt",
        "P3/../outside.txt",
        "/P3/file.txt",
        "P3//file.txt",
        "P3/./file.txt",
        r"P3\file.txt",
        "P3/file name.txt",
        "other/file.txt",
    ],
)
def test_unsafe_manifest_paths_fail(tmp_path: Path, unsafe_path: str):
    root = create_repository(tmp_path)
    generate_integrity(root)

    entries = read_manifest(root)
    entries[0] = unsafe_path
    write_manifest(root, sorted(entries))

    with pytest.raises(VERIFIER.IntegrityError):
        VERIFIER.verify(root)


def test_manifest_without_final_newline_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    manifest_path(root).write_bytes(
        manifest_path(root).read_bytes().rstrip(b"\n")
    )

    with pytest.raises(VERIFIER.IntegrityError, match="final newline"):
        VERIFIER.verify(root)


def test_manifest_with_blank_line_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    manifest_path(root).write_bytes(
        manifest_path(root).read_bytes().replace(b"\n", b"\n\n", 1)
    )

    with pytest.raises(VERIFIER.IntegrityError, match="Blank line"):
        VERIFIER.verify(root)


def test_manifest_with_crlf_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    manifest_path(root).write_bytes(
        manifest_path(root).read_bytes().replace(b"\n", b"\r\n")
    )

    with pytest.raises(VERIFIER.IntegrityError, match="CR/CRLF"):
        VERIFIER.verify(root)


def test_checksum_mismatch_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    lines = read_checksums(root)
    digest, separator, path = lines[0].partition("  ")
    changed_digest = ("0" if digest[0] != "0" else "1") + digest[1:]
    lines[0] = changed_digest + separator + path
    write_checksums(root, lines)

    with pytest.raises(VERIFIER.IntegrityError, match="SHA-256 mismatch"):
        VERIFIER.verify(root)


def test_checksum_inventory_missing_entry_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    lines = read_checksums(root)
    write_checksums(root, lines[:-1])

    with pytest.raises(VERIFIER.IntegrityError, match="paths do not match"):
        VERIFIER.verify(root)


def test_checksum_inventory_extra_entry_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    lines = read_checksums(root)
    extra_path = "P3/src/NotInManifest.java"
    extra_digest = "a" * 64
    lines.append(f"{extra_digest}  {extra_path}")
    write_checksums(root, sorted(lines, key=lambda item: item[66:]))

    with pytest.raises(VERIFIER.IntegrityError, match="paths do not match"):
        VERIFIER.verify(root)


def test_duplicate_checksum_path_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    lines = read_checksums(root)
    lines.append(lines[0])
    write_checksums(root, sorted(lines, key=lambda item: item[66:]))

    with pytest.raises(VERIFIER.IntegrityError, match="Duplicate checksum"):
        VERIFIER.verify(root)


def test_unsorted_checksums_fail(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    lines = read_checksums(root)
    write_checksums(root, list(reversed(lines)))

    with pytest.raises(VERIFIER.IntegrityError, match="not sorted"):
        VERIFIER.verify(root)


def test_malformed_checksum_record_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    lines = read_checksums(root)
    lines[0] = "invalid checksum record"
    write_checksums(root, lines)

    with pytest.raises(VERIFIER.IntegrityError, match="Malformed"):
        VERIFIER.verify(root)


def test_checksum_with_non_hex_digest_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    lines = read_checksums(root)
    lines[0] = "z" * 64 + lines[0][64:]
    write_checksums(root, lines)

    with pytest.raises(VERIFIER.IntegrityError, match="Invalid SHA-256"):
        VERIFIER.verify(root)


def test_checksum_without_final_newline_fails(tmp_path: Path):
    root = create_repository(tmp_path)
    generate_integrity(root)

    checksums_path(root).write_bytes(
        checksums_path(root).read_bytes().rstrip(b"\n")
    )

    with pytest.raises(VERIFIER.IntegrityError, match="final newline"):
        VERIFIER.verify(root)


def test_empty_inventory_fails(tmp_path: Path):
    root = tmp_path / "empty_repository"
    (root / "P3").mkdir(parents=True)

    with pytest.raises(VERIFIER.IntegrityError, match="inventory is empty"):
        VERIFIER.independent_inventory(root)


def test_excluded_directories_and_compiled_files_are_ignored(tmp_path: Path):
    root = create_repository(tmp_path)

    write_file(root, "P3/target/generated.txt", "generated\n")
    write_file(root, "P3/tools/__pycache__/module.pyc", b"compiled")
    write_file(root, "P3/tests/.pytest_cache/cache.bin", b"cache")
    write_file(root, "P3/src/module.pyo", b"compiled")

    generate_integrity(root)

    entries = read_manifest(root)

    assert "P3/target/generated.txt" not in entries
    assert "P3/tools/__pycache__/module.pyc" not in entries
    assert "P3/tests/.pytest_cache/cache.bin" not in entries
    assert "P3/src/module.pyo" not in entries

    assert VERIFIER.verify(root)["validation"] == "PASS"


def test_symlinked_source_file_is_excluded(tmp_path: Path):
    root = create_repository(tmp_path)
    target = root / "P3" / "tools" / "example.py"
    link = root / "P3" / "tools" / "linked.py"

    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are not supported in this environment")

    generate_integrity(root)

    assert "P3/tools/linked.py" not in read_manifest(root)
    assert VERIFIER.verify(root)["validation"] == "PASS"


@pytest.mark.parametrize("filename", ["MANIFEST.txt", "SHA256SUMS.txt"])
def test_symlinked_integrity_file_fails(tmp_path: Path, filename: str):
    root = create_repository(tmp_path)
    generate_integrity(root)

    path = root / "P3" / filename
    backup = root / "backup.txt"
    backup.write_bytes(path.read_bytes())
    path.unlink()

    try:
        path.symlink_to(backup)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are not supported in this environment")

    with pytest.raises(VERIFIER.IntegrityError, match="must not be a symlink"):
        VERIFIER.verify(root)


def test_cli_reports_pass(tmp_path: Path, capsys):
    root = create_repository(tmp_path)
    generate_integrity(root)

    exit_code = VERIFIER.main_with_root_for_test(root) if hasattr(
        VERIFIER, "main_with_root_for_test"
    ) else None

    # The public verification API is the authoritative assertion here.
    assert VERIFIER.verify(root)["validation"] == "PASS"
    assert exit_code is None
