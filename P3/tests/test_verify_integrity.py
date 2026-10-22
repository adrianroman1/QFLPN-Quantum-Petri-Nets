from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "verify_integrity.py"
spec = importlib.util.spec_from_file_location("verify_integrity", MODULE)
verify_integrity = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(verify_integrity)


def create_tree(root: Path) -> None:
    (root / "src").mkdir()
    (root / "src" / "A.java").write_text("class A {}\n", encoding="utf-8")
    (root / "data.txt").write_text("evidence\n", encoding="utf-8")
    files = ["data.txt", "src/A.java"]
    manifest = "# test manifest\n# File count: 2\n" + "\n".join(files) + "\n"
    (root / "MANIFEST.txt").write_text(manifest, encoding="utf-8")
    entries = [(p, hashlib.sha256((root / p).read_bytes()).hexdigest()) for p in files]
    entries.append(("MANIFEST.txt", hashlib.sha256(manifest.encode()).hexdigest()))
    (root / "SHA256SUMS.txt").write_text("".join(f"{h}  {p}\n" for p, h in sorted(entries)), encoding="ascii")


def test_independent_verification_passes(tmp_path):
    create_tree(tmp_path)
    result = verify_integrity.verify(tmp_path)
    assert result["validation"] == "PASS"
    assert result["manifest_entries"] == 2


def test_detects_modified_file(tmp_path):
    create_tree(tmp_path)
    (tmp_path / "data.txt").write_text("tampered\n", encoding="utf-8")
    try:
        verify_integrity.verify(tmp_path)
    except ValueError as exc:
        assert "SHA-256 mismatch" in str(exc)
    else:
        raise AssertionError("tampering was not detected")


def test_detects_unlisted_file(tmp_path):
    create_tree(tmp_path)
    (tmp_path / "extra.bin").write_bytes(b"extra")
    try:
        verify_integrity.verify(tmp_path)
    except ValueError as exc:
        assert "manifest inventory mismatch" in str(exc)
    else:
        raise AssertionError("unlisted file was not detected")


def test_rejects_duplicate_manifest_paths(tmp_path):
    create_tree(tmp_path)
    manifest = (tmp_path / "MANIFEST.txt").read_text(encoding="utf-8")
    (tmp_path / "MANIFEST.txt").write_text(manifest + "data.txt\n", encoding="utf-8")
    try:
        verify_integrity.verify(tmp_path)
    except ValueError as exc:
        assert "duplicate paths" in str(exc)
    else:
        raise AssertionError("duplicate manifest path was not detected")
