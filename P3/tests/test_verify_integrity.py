"""Regression tests for the independent P3 integrity verifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "verify_integrity.py"
)

GENERATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "generate_integrity.py"
)

SPEC = importlib.util.spec_from_file_location(
    "verify_integrity",
    MODULE_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

GENERATOR_SPEC = importlib.util.spec_from_file_location(
    "generate_integrity",
    GENERATOR_PATH,
)

assert GENERATOR_SPEC is not None
assert GENERATOR_SPEC.loader is not None

GENERATOR = importlib.util.module_from_spec(
    GENERATOR_SPEC
)

GENERATOR_SPEC.loader.exec_module(GENERATOR)


def create_fixture(tmp_path: Path) -> Path:
    """Create a nonempty P3 fixture."""
    root = tmp_path / "P3"

    (root / "code").mkdir(parents=True)

    (root / "code" / "Example.java").write_text(
        "class Example {}\n",
        encoding="utf-8",
    )

    (root / "README.md").write_text(
        "P3 verify fixture\n",
        encoding="utf-8",
    )

    return root


def generate_fixture(root: Path) -> None:
    """Generate both integrity files using the repository generator."""
    result = GENERATOR.generate(
        root,
        write=True,
    )

    assert result is True


def test_verify_passes_on_clean_tree(
    tmp_path: Path,
) -> None:
    root = create_fixture(tmp_path)

    generate_fixture(root)

    result = MODULE.verify(root)

    assert result["validation"] == "PASS"
    assert result["manifest_entries"] == 2
    assert result["sha256_entries_verified"] == 3


def test_verify_fails_when_manifest_missing(
    tmp_path: Path,
) -> None:
    root = create_fixture(tmp_path)

    (root / "SHA256SUMS.txt").write_text(
        "0" * 64 + "  README.md\n",
        encoding="ascii",
    )

    try:
        MODULE.verify(root)
    except ValueError as exc:
        assert "MANIFEST.txt is missing" in str(exc)
    else:
        raise AssertionError(
            "verify() must fail when MANIFEST.txt is missing"
        )


def test_verify_fails_when_checksum_file_missing(
    tmp_path: Path,
) -> None:
    root = create_fixture(tmp_path)

    generate_fixture(root)

    (root / "SHA256SUMS.txt").unlink()

    try:
        MODULE.verify(root)
    except ValueError as exc:
        assert "SHA256SUMS.txt is missing" in str(exc)
    else:
        raise AssertionError(
            "verify() must fail when SHA256SUMS.txt is missing"
        )


def test_verify_fails_when_unsafe_manifest_path_present(
    tmp_path: Path,
) -> None:
    root = create_fixture(tmp_path)

    generate_fixture(root)

    manifest = root / "MANIFEST.txt"

    lines = manifest.read_text(
        encoding="utf-8"
    ).splitlines()

    lines.insert(3, "../escape.txt")

    manifest.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    try:
        MODULE.verify(root)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "verify() must reject unsafe manifest paths"
        )


def test_empty_checksum_file_is_rejected(
    tmp_path: Path,
) -> None:
    root = create_fixture(tmp_path)

    generate_fixture(root)

    (root / "SHA256SUMS.txt").write_bytes(b"")

    try:
        MODULE.verify(root)
    except ValueError as exc:
        assert "checksum inventory is empty" in str(exc)
    else:
        raise AssertionError(
            "An empty checksum inventory must be rejected"
        )


def test_whitespace_only_checksum_file_is_rejected(
    tmp_path: Path,
) -> None:
    root = create_fixture(tmp_path)

    generate_fixture(root)

    (root / "SHA256SUMS.txt").write_bytes(
        b"\n   \n\t\n"
    )

    try:
        MODULE.verify(root)
    except ValueError as exc:
        assert "checksum inventory contains no entries" in str(exc)
    else:
        raise AssertionError(
            "A whitespace-only checksum inventory must be rejected"
        )


def test_blank_checksum_line_is_rejected(
    tmp_path: Path,
) -> None:
    root = create_fixture(tmp_path)

    generate_fixture(root)

    checksum_path = root / "SHA256SUMS.txt"

    original = checksum_path.read_text(
        encoding="ascii"
    )

    checksum_path.write_text(
        original + "\n",
        encoding="ascii",
    )

    try:
        MODULE.verify(root)
    except ValueError as exc:
        assert "malformed checksum line" in str(exc)
    else:
        raise AssertionError(
            "A blank checksum record must be rejected"
        )


def test_checksum_inventory_must_match_manifest(
    tmp_path: Path,
) -> None:
    root = create_fixture(tmp_path)

    generate_fixture(root)

    checksum_path = root / "SHA256SUMS.txt"

    checksum_path.write_text(
        "",
        encoding="ascii",
    )

    try:
        MODULE.verify(root)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Checksum inventory mismatch must fail"
        )


def test_verify_fails_after_source_file_is_modified(
    tmp_path: Path,
) -> None:
    root = create_fixture(tmp_path)

    generate_fixture(root)

    source = root / "README.md"

    source.write_text(
        "modified after checksum generation\n",
        encoding="utf-8",
    )

    try:
        MODULE.verify(root)
    except ValueError as exc:
        assert "SHA-256 mismatch" in str(exc)
    else:
        raise AssertionError(
            "Modified source content must fail SHA-256 verification"
        )


def test_verify_fails_when_manifest_is_modified(
    tmp_path: Path,
) -> None:
    root = create_fixture(tmp_path)

    generate_fixture(root)

    manifest = root / "MANIFEST.txt"

    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + "P3/fabricated.txt\n",
        encoding="utf-8",
    )

    try:
        MODULE.verify(root)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Modified manifest must fail verification"
        )


def test_empty_filesystem_inventory_is_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "P3"
    root.mkdir(parents=True)

    try:
        MODULE.independent_inventory(root)
    except ValueError as exc:
        assert "filesystem inventory is empty" in str(exc)
    else:
        raise AssertionError(
            "An empty filesystem inventory must be rejected"
        )
