#!/usr/bin/env python3
"""Independently verify the P3 MANIFEST.txt and SHA256SUMS.txt files."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]

EXCLUDED_DIRS = {
    "target",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

EXCLUDED_NAMES = {
    "MANIFEST.txt",
    "SHA256SUMS.txt",
}


class IntegrityError(Exception):
    """Raised when package integrity verification fails."""


def independent_inventory(repository_root: Path) -> list[str]:
    """Build an independent inventory of eligible files under P3/."""
    p3_root = repository_root / "P3"

    if not p3_root.is_dir() or p3_root.is_symlink():
        raise IntegrityError(f"Invalid P3 directory: {p3_root}")

    entries: list[str] = []

    for path in p3_root.rglob("*"):
        if path.is_symlink():
            continue

        if not path.is_file():
            continue

        relative_parts = path.relative_to(p3_root).parts

        if any(part in EXCLUDED_DIRS for part in relative_parts[:-1]):
            continue

        if path.name in EXCLUDED_NAMES:
            continue

        if path.suffix.lower() in {".pyc", ".pyo"}:
            continue

        repository_relative = path.relative_to(repository_root).as_posix()
        entries.append(repository_relative)

    entries.sort()

    if not entries:
        raise IntegrityError("P3 inventory is empty")

    if len(entries) != len(set(entries)):
        raise IntegrityError("P3 inventory contains duplicate paths")

    return entries


def validate_inventory_path(value: str) -> str:
    """Validate a canonical repository-relative P3 path."""
    if not value:
        raise IntegrityError("Empty inventory path")

    if "\\" in value:
        raise IntegrityError(f"Backslash is not allowed in path: {value}")

    if any(character.isspace() for character in value):
        raise IntegrityError(f"Whitespace is not allowed in path: {value}")

    pure = PurePosixPath(value)

    if pure.is_absolute():
        raise IntegrityError(f"Absolute path is not allowed: {value}")

    if pure.as_posix() != value:
        raise IntegrityError(f"Non-canonical path: {value}")

    if not value.startswith("P3/"):
        raise IntegrityError(f"Path is outside P3/: {value}")

    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise IntegrityError(f"Unsafe path component: {value}")

    if pure.name in EXCLUDED_NAMES:
        raise IntegrityError(f"Generated integrity file cannot be listed: {value}")

    if pure.suffix.lower() in {".pyc", ".pyo"}:
        raise IntegrityError(f"Compiled Python file cannot be listed: {value}")

    if any(part in EXCLUDED_DIRS for part in pure.parts[1:-1]):
        raise IntegrityError(f"Excluded directory in path: {value}")

    return value


def read_canonical_text(path: Path) -> list[str]:
    """Read an ASCII integrity file with canonical LF line endings."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise IntegrityError(f"Cannot read {path}: {exc}") from exc

    if not raw:
        raise IntegrityError(f"Integrity file is empty: {path}")

    if not raw.endswith(b"\n"):
        raise IntegrityError(f"Missing final newline: {path}")

    if b"\r" in raw:
        raise IntegrityError(f"CR/CRLF line endings are not allowed: {path}")

    try:
        content = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise IntegrityError(f"Non-ASCII content in {path}") from exc

    lines = content[:-1].split("\n")

    if any(line == "" for line in lines):
        raise IntegrityError(f"Blank line in integrity file: {path}")

    return lines


def parse_manifest(path: Path) -> list[str]:
    """Parse and validate the sorted MANIFEST.txt inventory."""
    lines = read_canonical_text(path)
    entries = [validate_inventory_path(line) for line in lines]

    if entries != sorted(entries):
        raise IntegrityError("MANIFEST.txt entries are not sorted")

    if len(entries) != len(set(entries)):
        raise IntegrityError("MANIFEST.txt contains duplicate entries")

    return entries


def parse_checksums(path: Path) -> dict[str, str]:
    """Parse GNU-style SHA256SUMS.txt records."""
    lines = read_canonical_text(path)
    checksums: dict[str, str] = {}
    paths: list[str] = []

    for line_number, line in enumerate(lines, start=1):
        if len(line) < 67 or line[64:66] != "  ":
            raise IntegrityError(
                f"Malformed checksum record at line {line_number}"
            )

        digest = line[:64]
        relative_path = validate_inventory_path(line[66:])

        if any(character not in "0123456789abcdef" for character in digest):
            raise IntegrityError(
                f"Invalid SHA-256 digest at line {line_number}"
            )

        if len(digest) != 64:
            raise IntegrityError(
                f"Invalid SHA-256 digest length at line {line_number}"
            )

        if relative_path in checksums:
            raise IntegrityError(
                f"Duplicate checksum path: {relative_path}"
            )

        checksums[relative_path] = digest
        paths.append(relative_path)

    if paths != sorted(paths):
        raise IntegrityError("SHA256SUMS.txt entries are not sorted")

    return checksums


def sha256_file(path: Path) -> str:
    """Calculate SHA-256 without loading the entire file into memory."""
    digest = hashlib.sha256()

    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise IntegrityError(f"Cannot hash {path}: {exc}") from exc

    return digest.hexdigest()


def verify(repository_root: Path) -> dict[str, object]:
    """Verify inventory and checksums against the actual P3 files."""
    repository_root = repository_root.resolve()

    manifest_path = repository_root / "P3" / "MANIFEST.txt"
    checksums_path = repository_root / "P3" / "SHA256SUMS.txt"

    for integrity_path in (manifest_path, checksums_path):
        if integrity_path.is_symlink():
            raise IntegrityError(
                f"Integrity file must not be a symlink: {integrity_path}"
            )

        if not integrity_path.is_file():
            raise IntegrityError(
                f"Missing integrity file: {integrity_path}"
            )

    actual_inventory = independent_inventory(repository_root)
    manifest_inventory = parse_manifest(manifest_path)
    checksums = parse_checksums(checksums_path)

    if manifest_inventory != actual_inventory:
        missing = sorted(set(actual_inventory) - set(manifest_inventory))
        unexpected = sorted(set(manifest_inventory) - set(actual_inventory))

        raise IntegrityError(
            "MANIFEST.txt does not match actual P3 inventory; "
            f"missing={missing[:10]}, unexpected={unexpected[:10]}"
        )

    manifest_set = set(manifest_inventory)
    checksum_set = set(checksums)

    if checksum_set != manifest_set:
        missing = sorted(manifest_set - checksum_set)
        unexpected = sorted(checksum_set - manifest_set)

        raise IntegrityError(
            "SHA256SUMS.txt paths do not match MANIFEST.txt; "
            f"missing={missing[:10]}, unexpected={unexpected[:10]}"
        )

    verified_count = 0

    for relative_path in manifest_inventory:
        file_path = repository_root.joinpath(*relative_path.split("/"))

        if file_path.is_symlink():
            raise IntegrityError(f"Listed file is a symlink: {relative_path}")

        if not file_path.is_file():
            raise IntegrityError(f"Listed file does not exist: {relative_path}")

        actual_digest = sha256_file(file_path)
        expected_digest = checksums[relative_path]

        if actual_digest != expected_digest:
            raise IntegrityError(
                f"SHA-256 mismatch for {relative_path}: "
                f"expected={expected_digest}, actual={actual_digest}"
            )

        verified_count += 1

    return {
        "validation": "PASS",
        "manifest": "P3/MANIFEST.txt",
        "checksums": "P3/SHA256SUMS.txt",
        "manifest_entries": len(manifest_inventory),
        "verified_files": verified_count,
        "format": "repository-relative GNU SHA-256",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify P3 manifest and SHA-256 checksums."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root containing the P3 directory.",
    )
    args = parser.parse_args()

    try:
        result = verify(args.root)
    except (IntegrityError, OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        print("P3_INDEPENDENT_INTEGRITY: FAIL", file=sys.stderr)
        return 1

    print("[PASS] Independent P3 integrity verification")
    print(f"Manifest entries: {result['manifest_entries']}")
    print(f"Verified files: {result['verified_files']}")
    print(f"Manifest: {result['manifest']}")
    print(f"Checksums: {result['checksums']}")
    print("P3_INDEPENDENT_INTEGRITY: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
