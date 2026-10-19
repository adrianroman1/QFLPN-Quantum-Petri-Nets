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
    "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", ".venv", "venv",
    "site-packages", "results",
}

EXCLUDED_NAMES = {"MANIFEST.txt", "SHA256SUMS.txt"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
PROTECTED_REPORT_FILES = {"reports/reference_config.json"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_excluded(relative: Path) -> bool:
    normalized = relative.as_posix()

    if normalized in PROTECTED_REPORT_FILES:
        return False
    if relative.name in EXCLUDED_NAMES:
        return True
    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return True
    if "reports" in relative.parts:
        return True

    return False


def collect_expected_paths(
    root: Path,
    require_protected_config: bool = False,
) -> set[str]:
    root = root.resolve(strict=True)
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

            if is_excluded(relative):
                continue

            if candidate.is_file():
                expected.add(relative.as_posix())

    protected_config = "reports/reference_config.json"

    if (
        require_protected_config
        and protected_config not in expected
    ):
        raise ValueError(
            "Required protected configuration is missing: "
            f"{protected_config}"
        )

    return expected


def parse_manifest(
    manifest: Path,
) -> tuple[dict[str, str], list[str], int | None]:
    entries: dict[str, str] = {}
    errors: list[str] = []
    declared_count: int | None = None

    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return {}, [f"Cannot read manifest: {exc}"], None

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("#"):
            prefix = "# File count:"

            if stripped.startswith(prefix):
                if declared_count is not None:
                    errors.append(
                        f"Line {line_number}: duplicate file count header"
                    )
                    continue

                value = stripped[len(prefix):].strip()

                if not value.isdigit():
                    errors.append(
                        f"Line {line_number}: invalid file count header"
                    )
                    continue

                declared_count = int(value)

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
            or not candidate.parts
            or ".." in candidate.parts
            or "." in candidate.parts
            or "\\" in relative_path
            or candidate.as_posix() != relative_path
        ):
            errors.append(
                f"Line {line_number}: unsafe or non-normalized path"
            )
            continue

        normalized = candidate.as_posix()

        if normalized in entries:
            errors.append(
                f"Line {line_number}: duplicate path {normalized}"
            )
            continue

        if is_excluded(candidate):
            errors.append(
                f"Line {line_number}: excluded path listed"
            )
            continue

        entries[normalized] = expected_hash

    if declared_count is None:
        errors.append("Manifest is missing the file count header")
    elif declared_count != len(entries):
        errors.append(
            "Manifest file count mismatch: "
            f"declared={declared_count}, parsed={len(entries)}"
        )

    if not entries and not errors:
        errors.append("Manifest contains no entries")

    return entries, errors, declared_count


def verify_manifest(
    root: Path,
    manifest: Path,
    require_protected_config: bool = False,
) -> tuple[int, int, list[str]]:
    entries, errors, _ = parse_manifest(manifest)

    passed = 0
    failed = len(errors)

    try:
        expected_paths = collect_expected_paths(
            root,
            require_protected_config=require_protected_config,
        )
    except (OSError, ValueError) as exc:
        return passed, failed + 1, errors + [str(exc)]

    manifest_paths = set(entries)

    for relative in sorted(expected_paths - manifest_paths):
        errors.append(f"Missing from manifest: {relative}")
        failed += 1

    for relative in sorted(manifest_paths - expected_paths):
        errors.append(f"Unexpected manifest path: {relative}")
        failed += 1

    root_resolved = root.resolve(strict=True)

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
    parser = argparse.ArgumentParser(
        description="Verify the P2 SHA-256 source manifest."
    )
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
        collect_expected_paths(
            root,
            require_protected_config=True,
        )
    except (OSError, ValueError) as exc:
        print("FAIL:", exc)
        return 2

    passed, failed, errors = verify_manifest(
        root,
        manifest,
        require_protected_config=True,
    )

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
