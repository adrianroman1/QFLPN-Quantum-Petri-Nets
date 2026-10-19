"""Fail-closed verification of P2/SHA256SUMS.txt."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMS = P2_ROOT / "SHA256SUMS.txt"

HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")

PROTECTED_CONFIG = "reports/reference_config.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def parse_sums(path: Path) -> tuple[dict[str, str], list[str]]:
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

        if relative == "MANIFEST.txt" or relative == "SHA256SUMS.txt":
            errors.append(
                f"Line {number}: checksum inventory cannot hash itself"
            )
            continue

        entries[relative] = digest

    if not entries:
        errors.append("SHA256SUMS contains no entries")

    return entries, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify P2 SHA256SUMS.txt."
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
        sums.relative_to(root)
    except ValueError:
        print("FAIL: SHA256SUMS must be inside P2 root")
        return 2

    entries, errors = parse_sums(sums)

    if PROTECTED_CONFIG not in entries:
        errors.append(
            f"Protected configuration missing: {PROTECTED_CONFIG}"
        )

    passed = 0
    failed = len(errors)

    for relative, expected in sorted(entries.items()):
        candidate = root / relative

        try:
            if candidate.is_symlink():
                raise ValueError("Symbolic links are forbidden")

            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)

            if not resolved.is_file():
                raise ValueError("Not a regular file")

            actual = sha256_file(resolved)

        except (OSError, ValueError) as exc:
            errors.append(f"{relative}: {exc}")
            failed += 1
            continue

        if actual != expected:
            errors.append(f"{relative}: SHA-256 mismatch")
            failed += 1
        else:
            passed += 1

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
