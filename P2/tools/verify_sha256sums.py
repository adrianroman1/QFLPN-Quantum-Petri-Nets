"""Fail-closed verification of the complete P2 SHA256SUMS inventory."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMS = P2_ROOT / "SHA256SUMS.txt"

HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PROTECTED_CONFIG = "reports/reference_config.json"

EXCLUDED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "site-packages",
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


def is_excluded(relative: Path) -> bool:
    if relative.name in EXCLUDED_NAMES:
        return True

    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return True

    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return True

    if "reports" in relative.parts:
        return relative.as_posix() != PROTECTED_CONFIG

    return False


def collect_expected_paths(root: Path) -> set[str]:
    root = root.resolve(strict=True)
    expected: set[str] = set()

    for current, directories, filenames in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)
        retained = []

        for directory in directories:
            candidate = current_path / directory

            if candidate.is_symlink():
                raise ValueError(
                    f"Symbolic directory forbidden: {candidate}"
                )

            if directory not in EXCLUDED_DIRS:
                retained.append(directory)

        directories[:] = retained

        for filename in filenames:
            candidate = current_path / filename

            if candidate.is_symlink():
                raise ValueError(
                    f"Symbolic file forbidden: {candidate}"
                )

            relative = candidate.relative_to(root)

            if is_excluded(relative):
                continue

            if candidate.is_file():
                expected.add(relative.as_posix())

    if PROTECTED_CONFIG not in expected:
        raise ValueError(
            f"Required protected configuration missing: "
            f"{PROTECTED_CONFIG}"
        )

    return expected


def parse_sums(
    path: Path,
) -> tuple[dict[str, str], list[str]]:
    entries: dict[str, str] = {}
    errors: list[str] = []

    try:
        lines = path.read_text(
            encoding="utf-8"
        ).splitlines()
    except (OSError, UnicodeError) as exc:
        return {}, [f"Cannot read SHA256SUMS: {exc}"]

    for number, line in enumerate(lines, start=1):
        if not line:
            continue

        parts = line.split("  ", 1)

        if len(parts) != 2:
            errors.append(
                f"Line {number}: invalid checksum format"
            )
            continue

        digest, relative = parts

        if not HASH_PATTERN.fullmatch(digest):
            errors.append(
                f"Line {number}: invalid SHA-256 digest"
            )
            continue

        candidate = Path(relative)

        if (
            candidate.is_absolute()
            or not candidate.parts
            or ".." in candidate.parts
            or "." in candidate.parts
            or "\\" in relative
            or candidate.as_posix() != relative
        ):
            errors.append(
                f"Line {number}: unsafe or non-normalized path"
            )
            continue

        if relative in entries:
            errors.append(
                f"Line {number}: duplicate path {relative}"
            )
            continue

        if is_excluded(candidate):
            errors.append(
                f"Line {number}: excluded path listed: {relative}"
            )
            continue

        entries[relative] = digest

    if not entries:
        errors.append("SHA256SUMS contains no entries")

    return entries, errors


def verify(
    root: Path,
    sums: Path,
) -> tuple[int, int, list[str]]:
    root = root.resolve(strict=True)
    sums = sums.resolve(strict=True)

    try:
        sums.relative_to(root)
    except ValueError:
        return 0, 1, [
            "SHA256SUMS must be inside the P2 root"
        ]

    entries, errors = parse_sums(sums)

    try:
        expected_paths = collect_expected_paths(root)
    except (OSError, ValueError) as exc:
        return 0, len(errors) + 1, errors + [str(exc)]

    listed_paths = set(entries)

    for relative in sorted(expected_paths - listed_paths):
        errors.append(
            f"Missing from SHA256SUMS: {relative}"
        )

    for relative in sorted(listed_paths - expected_paths):
        errors.append(
            f"Unexpected SHA256SUMS path: {relative}"
        )

    passed = 0
    failed = len(errors)

    for relative, expected_hash in sorted(entries.items()):
        candidate = root / relative

        try:
            if candidate.is_symlink():
                raise ValueError(
                    "Symbolic links are forbidden"
                )

            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)

            if not resolved.is_file():
                raise ValueError(
                    "Not a regular file"
                )

            actual_hash = sha256_file(resolved)

        except (OSError, ValueError) as exc:
            errors.append(
                f"{relative}: {exc}"
            )
            failed += 1
            continue

        if actual_hash != expected_hash:
            errors.append(
                f"{relative}: SHA-256 mismatch"
            )
            failed += 1
        else:
            passed += 1

    return passed, failed, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the complete P2 SHA256SUMS inventory."
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=P2_ROOT,
    )

    parser.add_argument(
        "--sums",
        type=Path,
        default=DEFAULT_SUMS,
    )

    args = parser.parse_args()

    root = args.root.resolve()
    sums = args.sums.resolve()

    if not root.is_dir():
        print("FAIL: P2 root does not exist")
        return 2

    if not sums.is_file():
        print("FAIL: SHA256SUMS does not exist")
        return 2

    try:
        passed, failed, errors = verify(root, sums)
    except (OSError, ValueError) as exc:
        print("FAIL:", exc)
        return 2

    for error in errors:
        print("FAIL:", error)

    print("=" * 72)
    print("SHA256SUMS PASS:", passed)
    print("SHA256SUMS FAIL:", failed)

    if failed:
        print("VERDICT: SHA256SUMS_REJECTED")
        return 1

    print("VERDICT: SHA256SUMS_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
