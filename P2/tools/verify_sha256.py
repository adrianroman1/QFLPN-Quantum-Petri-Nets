"""Fail-closed SHA-256 manifest verification for QFLPN P2."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


P2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = P2_ROOT / "MANIFEST.txt"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def parse_manifest(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """Parse manifest entries and report malformed lines."""
    entries: list[tuple[str, str]] = []
    errors: list[str] = []
    seen: set[str] = set()

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"Cannot read manifest: {exc}"]

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        parts = stripped.split(maxsplit=1)

        if len(parts) != 2:
            errors.append(
                f"Line {line_number}: expected SHA256 and relative path."
            )
            continue

        expected_hash, relative_path = parts
        relative_path = relative_path.strip()

        if not SHA256_PATTERN.fullmatch(expected_hash):
            errors.append(
                f"Line {line_number}: invalid SHA-256 digest."
            )
            continue

        if not relative_path:
            errors.append(f"Line {line_number}: empty file path.")
            continue

        candidate = Path(relative_path)

        if candidate.is_absolute():
            errors.append(
                f"Line {line_number}: absolute paths are forbidden."
            )
            continue

        if ".." in candidate.parts:
            errors.append(
                f"Line {line_number}: parent traversal is forbidden."
            )
            continue

        normalized = candidate.as_posix()

        if normalized in seen:
            errors.append(
                f"Line {line_number}: duplicate path {normalized!r}."
            )
            continue

        seen.add(normalized)
        entries.append((expected_hash, normalized))

    if not entries and not errors:
        errors.append("Manifest contains no file entries.")

    return entries, errors


def verify_manifest(root: Path, manifest: Path) -> tuple[int, int, list[str]]:
    """Verify all manifest entries without following paths outside root."""
    entries, errors = parse_manifest(manifest)

    passed = 0
    failed = len(errors)
    root_resolved = root.resolve()

    for expected_hash, relative_path in entries:
        candidate = root / relative_path

        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root_resolved)
        except (OSError, ValueError):
            errors.append(
                f"{relative_path}: missing file or path escapes P2 root."
            )
            failed += 1
            continue

        if not resolved.is_file():
            errors.append(f"{relative_path}: not a regular file.")
            failed += 1
            continue

        try:
            actual_hash = sha256_file(resolved)
        except OSError as exc:
            errors.append(f"{relative_path}: read error: {exc}")
            failed += 1
            continue

        if actual_hash != expected_hash:
            errors.append(
                f"{relative_path}: SHA-256 mismatch "
                f"(expected {expected_hash}, got {actual_hash})."
            )
            failed += 1
        else:
            passed += 1

    return passed, failed, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify P2 files against MANIFEST.txt."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=P2_ROOT,
        help="P2 root directory.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Manifest file.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    manifest = args.manifest.resolve()

    if not root.is_dir():
        print(f"FAIL: P2 root does not exist: {root}")
        return 2

    try:
        manifest.relative_to(root)
    except ValueError:
        print("FAIL: Manifest must be located inside the P2 root.")
        return 2

    if not manifest.is_file():
        print(f"FAIL: Manifest not found: {manifest}")
        return 2

    passed, failed, errors = verify_manifest(root, manifest)

    for error in errors:
        print("FAIL:", error)

    print("-" * 72)
    print("Files verified:", passed + failed)
    print("PASS:", passed)
    print("FAIL:", failed)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
