#!/usr/bin/env python3
"""Generate deterministic P3 manifest and SHA-256 inventory files."""
from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", "target", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
GENERATED_FILES = {"MANIFEST.txt", "SHA256SUMS.txt"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_unsafe_relative(path: str) -> bool:
    candidate = Path(path)
    return (
        candidate.is_absolute()
        or "\\" in path
        or ".." in candidate.parts
        or path.startswith("./")
        or path.strip() != path
        or path in GENERATED_FILES
    )


def inventory(root: Path) -> list[str]:
    """Return sorted repository-relative paths; never follow symlinks."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"P3 root is not a directory: {root}")

    paths: list[str] = []
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        base = Path(current)
        directories[:] = sorted(
            name
            for name in directories
            if name not in EXCLUDED_DIRS and not (base / name).is_symlink()
        )

        for filename in sorted(filenames):
            path = base / filename
            relative = path.relative_to(root).as_posix()

            if relative in GENERATED_FILES:
                continue
            if path.is_symlink() or not path.is_file():
                continue
            if is_unsafe_relative(relative):
                continue
            paths.append(relative)

    paths.sort()
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate path in filesystem inventory")
    return paths


def manifest_bytes(paths: list[str]) -> bytes:
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("manifest paths must be unique and sorted")

    lines = [
        "# QFLPN P3 generated manifest",
        "# Format: one repository-relative POSIX path per line",
        f"# File count: {len(paths)}",
        *paths,
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def checksum_bytes(root: Path, paths: list[str], manifest: bytes) -> bytes:
    entries = [(relative, sha256_file(root / relative)) for relative in paths]
    entries.append(("MANIFEST.txt", hashlib.sha256(manifest).hexdigest()))
    entries.sort(key=lambda item: item[0])
    return "".join(f"{digest}  {relative}\n" for relative, digest in entries).encode("ascii")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)

    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def generate(root: Path, write: bool = True) -> bool:
    """
    Generate files when write=True.
    When write=False, compare expected bytes without modifying the tree.
    Returns False when check mode detects missing or stale files.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"P3 root is not a directory: {root}")

    paths = inventory(root)
    manifest = manifest_bytes(paths)
    checksums = checksum_bytes(root, paths, manifest)

    expected = {root / "MANIFEST.txt": manifest, root / "SHA256SUMS.txt": checksums}

    if write:
        for destination, content in expected.items():
            atomic_write(destination, content)
        print(f"[PASS] Generated deterministic manifest and SHA-256 inventory for {len(paths)} files")
        return True

    stale = [destination.name for destination, content in expected.items() if not destination.is_file() or destination.read_bytes() != content]
    if stale:
        print("[FAIL] Missing or stale integrity files: " + ", ".join(stale))
        return False

    print(f"[PASS] Integrity files are reproducible ({len(paths)} inventoried files)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or check deterministic P3 integrity files.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()

    try:
        success = generate(args.root, write=args.write)
        return 0 if success else 1
    except (OSError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
