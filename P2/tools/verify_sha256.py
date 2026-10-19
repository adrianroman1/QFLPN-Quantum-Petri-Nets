"""Fail-closed SHA-256 manifest verification for P2."""

from __future__ import annotations

import argparse
import hashlib
import os
import re

from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = P2_ROOT / "MANIFEST.txt"

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

EXCLUDED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "site-packages",
    "reports",
    "results",
}

EXCLUDED_NAMES = {
    "MANIFEST.txt",
    "SHA256SUMS.txt",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def collect_expected_paths(root: Path) -> set[str]:
    root = root.resolve()
    expected: set[str] = set()

    for current, directories, filenames in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)
        retained_directories = []

        for directory in directories:
            candidate = current_path / directory

            if candidate.is_symlink():
                raise ValueError(
                    f"Symbolic directory forbidden: {candidate}"
                )

            if directory not in EXCLUDED_DIRS:
                retained_directories.append(directory)

        directories[:] = retained_directories

        for filename in filenames:
            candidate = current_path / filename

            if candidate.is_symlink():
                raise ValueError(
                    f"Symbolic file forbidden: {candidate}"
                )

            relative = candidate.relative_to(root)

            if filename in EXCLUDED_NAMES:
                continue

            if candidate.suffix.lower() in EXCLUDED_SUFFIXES:
                continue

            if any(part in EXCLUDED_DIRS for part in relative.parts):
                continue

            if candidate.is_file():
                expected.add(relative.as_posix())

    return expected


def parse_manifest(
    manifest: Path,
) -> tuple[dict[str, str], list[str]]:
    entries: dict[str, str] = {}
    errors: list[str] = []

    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return {}, [f"Cannot read manifest: {exc}"]

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        parts = stripped.split(maxsplit=1)

        if len(parts) != 2:
            errors.append(
                f"Line {line_number}: invalid entry"
            )
            continue

        expected_hash, relative_path = parts
        candidate = Path(relative_path)

        if not SHA256_PATTERN.fullmatch(expected_hash):
            errors.append(
                f"Line {line_number}: invalid SHA-256"
            )
            continue

        if (
            candidate.is_absolute()
            or ".." in candidate.parts
            or not candidate.parts
            or "\\" in relative_path
        ):
            errors.append(
                f"Line {line_number}: unsafe path"
            )
            continue

        normalized = candidate.as_posix()

        if normalized in entries:
            errors.append(
                f"Line {line_number}: duplicate path {normalized}"
            )
            continue

        if (
            candidate.name in EXCLUDED_NAMES
            or candidate.suffix.lower() in EXCLUDED_SUFFIXES
            or any(part in EXCLUDED_DIRS for part in candidate.parts)
        ):
            errors.append(
                f"Line {line_number}: excluded path listed"
            )
            continue

        entries[normalized] = expected_hash

    if not entries and not errors:
        errors.append("Manifest contains no entries")

    return entries, errors


def verify_manifest(
    root: Path,
    manifest: Path,
) -> tuple[int, int, list[str]]:
    entries, errors = parse_manifest(manifest)

    passed = 0
    failed = len(errors)

    try:
        expected_paths = collect_expected_paths(root)
    except (OSError, ValueError) as exc:
        return passed, failed + 1, errors + [str(exc)]

    manifest_paths = set(entries)

    for relative in sorted(expected_paths - manifest_paths):
        errors.append(f"Missing from manifest: {relative}")
        failed += 1

    for relative in sorted(manifest_paths - expected_paths):
        errors.append(f"Unexpected manifest path: {relative}")
        failed += 1

    root_resolved = root.resolve()

    for relative, expected_hash in sorted(entries.items()):
        candidate = root / relative

        try:
            if candidate.is_symlink():
                raise ValueError("Symbolic links are forbidden")

            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root_resolved)

            if not resolved.is_file():
                raise ValueError("Not a regular file")

            actual_hash = sha256_file(resolved)

        except (OSError, ValueError) as exc:
            errors.append(f"{relative}: {exc}")
            failed += 1
            continue

        if actual_hash != expected_hash:
            errors.append(f"{relative}: SHA-256 mismatch")
            failed += 1
        else:
            passed += 1

    return passed, failed, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=P2_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    root = args.root.resolve()
    manifest = args.manifest.resolve()

    if not root.is_dir():
        print("FAIL: P2 root does not exist")
        return 2

    if not manifest.is_file():
        print("FAIL: manifest does not exist:", manifest)
        return 2

    try:
        manifest.relative_to(root)
    except ValueError:
        print("FAIL: manifest must be inside P2 root")
        return 2

    passed, failed, errors = verify_manifest(root, manifest)

    for error in errors:
        print("FAIL:", error)

    print("=" * 72)
    print("SHA-256 PASS:", passed)
    print("SHA-256 FAIL:", failed)

    if failed:
        print("VERDICT: P2_INTEGRITY_REJECTED")
        return 1

    print("VERDICT: P2_INTEGRITY_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
