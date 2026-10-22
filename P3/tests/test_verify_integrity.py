from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "verify_integrity.py"
)

SPEC = importlib.util.spec_from_file_location(
    "verify_integrity",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None

VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


MANIFEST_HEADER = [
    "# QFLPN P3 generated manifest",
    "# Format: one repository-relative POSIX path per line",
]


def create_tree(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src" / "A.java").write_text(
        "class A {}\n",
        encoding="utf-8",
    )
    (root / "data.txt").write_text(
        "evidence\n",
        encoding="utf-8",
    )

    files = ["data.txt", "src/A.java"]
    manifest_lines = [
        *MANIFEST_HEADER,
        f"# File count: {len(files)}",
        *files,
    ]
    manifest = "\n".join(manifest_lines) + "\n"

    (root / "MANIFEST.txt").write_text(
        manifest,
        encoding="utf-8",
    )

    entries = [
        (
            name,
            hashlib.sha256((root / name).read_bytes()).hexdigest(),
        )
        for name in files
    ]
    entries.append(
        (
            "MANIFEST.txt",
            hashlib.sha256(manifest.encode("utf-8")).hexdigest(),
        )
    )

    checksum_text = "".join(
        f"{digest}  {name}\n"
        for name, digest in sorted(entries)
    )
    (root / "SHA256SUMS.txt").write_text(
        checksum_text,
        encoding="ascii",
    )


def test_independent_verification_passes(tmp_path: Path) -> None:
    create_tree(tmp_path)

    result = VERIFY.verify(tmp_path)

    assert result["validation"] == "PASS"
    assert result["manifest_entries"] == 2
    assert result["sha256_entries_verified"] == 3


def test_detects_modified_file(tmp_path: Path) -> None:
    create_tree(tmp_path)
    (tmp_path / "data.txt").write_text(
        "tampered\n",
        encoding="utf-8",
    )

    try:
        VERIFY.verify(tmp_path)
    except ValueError as exc:
        assert "SHA-256 mismatch" in str(exc)
    else:
        raise AssertionError("tampering was not detected")


def test_detects_unlisted_file(tmp_path: Path) -> None:
    create_tree(tmp_path)
    (tmp_path / "extra.bin").write_bytes(b"extra")

    try:
        VERIFY.verify(tmp_path)
    except ValueError as exc:
        assert "manifest inventory mismatch" in str(exc)
    else:
        raise AssertionError("unlisted file was not detected")


def test_rejects_duplicate_manifest_paths(tmp_path: Path) -> None:
    create_tree(tmp_path)
    path = tmp_path / "MANIFEST.txt"
    content = path.read_text(encoding="utf-8")
    path.write_text(content + "data.txt\n", encoding="utf-8")

    try:
        VERIFY.verify(tmp_path)
    except ValueError as exc:
        assert "file-count mismatch" in str(exc) or "duplicate paths" in str(exc)
    else:
        raise AssertionError("duplicate manifest path was not detected")


def test_rejects_incorrect_manifest_count(tmp_path: Path) -> None:
    create_tree(tmp_path)
    path = tmp_path / "MANIFEST.txt"
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace("# File count: 2", "# File count: 3"),
                    encoding="utf-8")

    try:
        VERIFY.verify(tmp_path)
    except ValueError as exc:
        assert "file-count mismatch" in str(exc)
    else:
        raise AssertionError("incorrect manifest count was not detected")


def test_rejects_unsafe_manifest_path(tmp_path: Path) -> None:
    create_tree(tmp_path)
    path = tmp_path / "MANIFEST.txt"
    content = path.read_text(encoding="utf-8")
    path.write_text(content + "../outside.txt\n", encoding="utf-8")

    try:
        VERIFY.verify(tmp_path)
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe manifest path was not detected")


def test_rejects_modified_manifest_hash(tmp_path: Path) -> None:
    create_tree(tmp_path)
    path = tmp_path / "MANIFEST.txt"
    path.write_text(
        path.read_text(encoding="utf-8") + "# changed\n",
        encoding="utf-8",
    )

    try:
        VERIFY.verify(tmp_path)
    except ValueError as exc:
        assert (
            "manifest inventory mismatch" in str(exc)
            or "SHA-256 mismatch: MANIFEST.txt" in str(exc)
        )
    else:
        raise AssertionError("manifest modification was not detected")


def test_rejects_duplicate_checksum_entry(tmp_path: Path) -> None:
    create_tree(tmp_path)
    path = tmp_path / "SHA256SUMS.txt"
    content = path.read_text(encoding="ascii")
    path.write_text(content + content.splitlines()[0] + "\n",
                    encoding="ascii")

    try:
        VERIFY.verify(tmp_path)
    except ValueError as exc:
        assert "duplicate checksum entry" in str(exc)
    else:
        raise AssertionError("duplicate checksum was not detected")


def test_rejects_malformed_checksum(tmp_path: Path) -> None:
    create_tree(tmp_path)
    (tmp_path / "SHA256SUMS.txt").write_text(
        "not-a-valid-checksum  data.txt\n",
        encoding="ascii",
    )

    try:
        VERIFY.verify(tmp_path)
    except ValueError:
        pass
    else:
        raise AssertionError("malformed checksum was not detected")
