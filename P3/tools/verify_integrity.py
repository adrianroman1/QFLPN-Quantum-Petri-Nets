#!/usr/bin/env python3
"""Independent, fail-closed verifier for P3 manifest and SHA-256 files.

This module intentionally does not import generate_integrity.py. It independently
walks the tree, parses the manifest/checksum formats, and recomputes every digest.
"""
from __future__ import annotations
import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

EXCLUDED_DIRS = {".git", "target", "__pycache__", ".pytest_cache", ".mypy_cache"}
GENERATED = {"MANIFEST.txt", "SHA256SUMS.txt"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def independent_inventory(root: Path) -> list[str]:
    found: list[str] = []
    for directory, subdirs, filenames in os.walk(root, followlinks=False):
        parent = Path(directory)
        subdirs[:] = [d for d in subdirs if d not in EXCLUDED_DIRS and not (parent / d).is_symlink()]
        for filename in filenames:
            item = parent / filename
            relative = item.relative_to(root).as_posix()
            if relative in GENERATED:
                continue
            if item.is_symlink():
                raise ValueError(f"symbolic link is not permitted in inventory: {relative}")
            if item.is_file():
                found.append(relative)
    found.sort()
    if len(found) != len(set(found)):
        raise ValueError("filesystem walk produced duplicate paths")
    return found


def parse_manifest(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read manifest: {exc}") from exc
    entries = [line for line in lines if line and not line.startswith("#")]
    if len(entries) != len(set(entries)):
        raise ValueError("manifest contains duplicate paths")
    for entry in entries:
        p = Path(entry)
        if p.is_absolute() or "\\" in entry or ".." in p.parts or entry.startswith("./"):
            raise ValueError(f"unsafe/noncanonical manifest path: {entry}")
    return entries


def parse_checksums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read checksum file: {exc}") from exc
    for number, line in enumerate(lines, 1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if not match:
            raise ValueError(f"malformed checksum line {number}")
        value, name = match.groups()
        if name in result:
            raise ValueError(f"duplicate checksum entry: {name}")
        result[name] = value
    return result


def verify(root: Path) -> dict[str, object]:
    root = root.resolve()
    manifest_path = root / "MANIFEST.txt"
    checksum_path = root / "SHA256SUMS.txt"
    if not root.is_dir():
        raise ValueError(f"P3 root does not exist: {root}")
    listed = parse_manifest(manifest_path)
    actual = independent_inventory(root)
    if listed != actual:
        missing = sorted(set(actual) - set(listed))
        extra = sorted(set(listed) - set(actual))
        raise ValueError(f"manifest inventory mismatch; missing={missing}; extra={extra}")
    checksums = parse_checksums(checksum_path)
    expected_names = set(actual) | {"MANIFEST.txt"}
    if set(checksums) != expected_names:
        raise ValueError(
            f"checksum inventory mismatch; missing={sorted(expected_names-set(checksums))}; "
            f"extra={sorted(set(checksums)-expected_names)}"
        )
    verified = 0
    for name in actual:
        if digest(root / name) != checksums[name]:
            raise ValueError(f"SHA-256 mismatch: {name}")
        verified += 1
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if manifest_hash != checksums["MANIFEST.txt"]:
        raise ValueError("SHA-256 mismatch: MANIFEST.txt")
    return {"validation": "PASS", "manifest_entries": len(listed), "sha256_entries_verified": verified + 1}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        result = verify(args.root)
        print(f"[PASS] Independent integrity verification: {result['manifest_entries']} files; {result['sha256_entries_verified']} digests")
        return 0
    except (OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
