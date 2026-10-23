#!/usr/bin/env python3
"""Independent fail-closed verifier for P3 manifest and SHA-256 inventory."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", "target", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
GENERATED_FILES = {"MANIFEST.txt", "SHA256SUMS.txt"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_HEADER = [
    "# QFLPN P3 generated manifest",
    "# Format: one repository-relative POSIX path per line",
]


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def independent_inventory(root: Path) -> list[str]:
    """Rebuild the inventory independently; never follow symbolic links."""
    found: list[str] = []
    for directory, subdirectories, filenames in os.walk(root, topdown=True, followlinks=False):
        parent = Path(directory)
        subdirectories[:] = sorted(
            name for name in subdirectories if name not in EXCLUDED_DIRS and not (parent / name).is_symlink()
        )

        for filename in sorted(filenames):
            item = parent / filename
            relative = item.relative_to(root).as_posix()
            if relative in GENERATED_FILES:
                continue
            if item.is_symlink() or not item.is_file():
                continue
            found.append(relative)

    found.sort()
    if len(found) != len(set(found)):
        raise ValueError("filesystem inventory contains duplicate paths")
    return found


def parse_manifest(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read UTF-8 manifest: {exc}") from exc

    if len(lines) < 3 or lines[:2] != MANIFEST_HEADER:
        raise ValueError("manifest header or format version is invalid")

    match = re.fullmatch(r"# File count: (0|[1-9][0-9]*)", lines[2])
    if not match:
        raise ValueError("manifest file-count declaration is invalid")

    declared_count = int(match.group(1))
    entries = lines[3:]

    if any(not entry for entry in entries):
        raise ValueError("manifest contains blank path entries")
    if len(entries) != declared_count:
        raise ValueError(f"manifest file-count mismatch: declared {declared_count}, found {len(entries)}")
    if entries != sorted(entries):
        raise ValueError("manifest paths are not sorted")
    if len(entries) != len(set(entries)):
        raise ValueError("manifest contains duplicate paths")

    for entry in entries:
        candidate = Path(entry)
        if (
            candidate.is_absolute()
            or "\\" in entry
            or ".." in candidate.parts
            or entry.startswith("./")
            or entry in GENERATED_FILES
            or entry.strip() != entry
        ):
            raise ValueError(f"unsafe or noncanonical manifest path: {entry}")

    return entries


def parse_checksums(path: Path) -> dict[str, str]:
    try:
        content = path.read_text(encoding="ascii")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read ASCII checksum file: {exc}") from exc

    if content and not content.endswith("\n"):
        raise ValueError("checksum file must end with a newline")

    result: dict[str, str] = {}
    lines = content.splitlines()

    for number, line in enumerate(lines, start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if not match:
            raise ValueError(f"malformed checksum line {number}")

        value, name = match.groups()
        if name in result:
            raise ValueError(f"duplicate checksum entry: {name}")

        candidate = Path(name)
        if (
            candidate.is_absolute()
            or "\\" in name
            or ".." in candidate.parts
            or name.startswith("./")
            or name.strip() != name
        ):
            raise ValueError(f"unsafe checksum path: {name}")
        if not HEX64.fullmatch(value):
            raise ValueError(f"checksum digest is not a valid SHA-256 for {name}")

        result[name] = value

    if list(result) != sorted(result):
        raise ValueError("checksum entries are not sorted")

    return result


def verify(root: Path) -> dict[str, object]:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"P3 root does not exist: {root}")

    manifest_path = root / "MANIFEST.txt"
    checksum_path = root / "SHA256SUMS.txt"

    if not manifest_path.is_file() or not checksum_path.is_file():
        raise ValueError("MANIFEST.txt or SHA256SUMS.txt is missing")

    listed = parse_manifest(manifest_path)
    actual = independent_inventory(root)

    if listed != actual:
        missing = sorted(set(actual) - set(listed))
        extra = sorted(set(listed) - set(actual))
        raise ValueError(f"manifest inventory mismatch; missing={missing}; extra={extra}")

    checksums = parse_checksums(checksum_path)
    expected_names = set(actual) | {"MANIFEST.txt"}

    if set(checksums) != expected_names:
        missing = sorted(expected_names - set(checksums))
        extra = sorted(set(checksums) - expected_names)
        raise ValueError(f"checksum inventory mismatch; missing={missing}; extra={extra}")

    verified = 0
    for relative in actual:
        expected = checksums[relative]
        actual_digest = digest_file(root / relative)
        if actual_digest != expected:
            raise ValueError(f"SHA-256 mismatch: {relative}")
        verified += 1

    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if manifest_digest != checksums["MANIFEST.txt"]:
        raise ValueError("SHA-256 mismatch: MANIFEST.txt")

    return {
        "validation": "PASS",
        "manifest_entries": len(listed),
        "sha256_entries_verified": verified + 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently verify P3 file inventory and SHA-256 hashes.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()

    try:
        result = verify(args.root)
        print("[PASS] Independent integrity verification: "
              f"{result['manifest_entries']} files; {result['sha256_entries_verified']} SHA-256 digests")
        return 0
    except (OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
