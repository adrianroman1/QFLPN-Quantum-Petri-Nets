#!/usr/bin/env python3
"""Generate the deterministic P3 MANIFEST.txt and SHA256SUMS.txt.

The inventory is restricted to P3/. The manifest and global checksum file
are excluded from their own inventory. Symbolic links and non-regular
files are never followed or hashed.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P3 = ROOT / "P3"

EXCLUDED_NAMES = {"MANIFEST.txt", "SHA256SUMS.txt"}
EXCLUDED_DIRS = {
    "target",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory_files(root: Path) -> list[Path]:
    """Return sorted eligible files below root/P3."""
    root = Path(root).resolve()
    p3_root = root / "P3"

    if p3_root.is_symlink() or not p3_root.is_dir():
        raise RuntimeError(f"P3 directory is missing or unsafe: {p3_root}")

    result: list[Path] = []

    for current, directories, filenames in os.walk(
        p3_root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)

        directories[:] = sorted(
            name
            for name in directories
            if name not in EXCLUDED_DIRS
            and not (current_path / name).is_symlink()
        )

        for name in sorted(filenames):
            candidate = current_path / name

            if name in EXCLUDED_NAMES:
                continue
            if candidate.suffix.lower() in EXCLUDED_SUFFIXES:
                continue
            if candidate.is_symlink() or not candidate.is_file():
                continue

            result.append(candidate)

    result.sort(key=lambda path: path.relative_to(root).as_posix())

    relative = [path.relative_to(root).as_posix() for path in result]

    if len(relative) != len(set(relative)):
        raise RuntimeError("Duplicate paths detected in P3 inventory")

    return result


def build_inventory_contents(
    root: Path,
    files: list[Path],
) -> tuple[str, str]:
    """Build the manifest and checksum contents from the same file list."""
    root = Path(root).resolve()
    relative_paths: list[str] = []

    for path in files:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Inventory candidate is unsafe: {path}")

        try:
            relative = path.relative_to(root).as_posix()
        except ValueError as exc:
            raise RuntimeError(
                f"Inventory path is outside repository root: {path}"
            ) from exc

        if (
            not relative.startswith("P3/")
            or "\\" in relative
            or ".." in Path(relative).parts
            or Path(relative).name in EXCLUDED_NAMES
        ):
            raise RuntimeError(f"Unsafe inventory path: {relative}")

        relative_paths.append(relative)

    if len(relative_paths) != len(set(relative_paths)):
        raise RuntimeError("Duplicate paths detected in P3 inventory")

    if relative_paths != sorted(relative_paths):
        raise RuntimeError("P3 inventory paths are not sorted")

    manifest = "".join(path + "\n" for path in relative_paths)

    checksum_lines: list[str] = []

    for path, relative in zip(files, relative_paths):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(
                f"Inventory candidate changed before hashing: {path}"
            )
        checksum_lines.append(f"{sha256_file(path)}  {relative}")

    checksums = "".join(line + "\n" for line in checksum_lines)
    return manifest, checksums


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a UTF-8 file in its destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def generate(
    root: Path = ROOT,
    *,
    require_nonempty: bool = True,
) -> tuple[int, int]:
    """Generate P3/MANIFEST.txt and P3/SHA256SUMS.txt."""
    root = Path(root).resolve()
    p3_root = root / "P3"

    if p3_root.is_symlink() or not p3_root.is_dir():
        raise RuntimeError(f"P3 directory is missing or unsafe: {p3_root}")

    files = inventory_files(root)

    if require_nonempty and not files:
        raise RuntimeError("Refusing to generate an empty P3 inventory")

    manifest, checksums = build_inventory_contents(root, files)

    # Construct both complete contents before replacing either destination.
    atomic_write_text(p3_root / "MANIFEST.txt", manifest)
    atomic_write_text(p3_root / "SHA256SUMS.txt", checksums)

    count = len(files)
    print(f"P3 manifest entries: {count}")
    print(f"P3 SHA-256 entries: {count}")
    print("P3 integrity generation: PASS")
    return count, count


def main() -> int:
    try:
        generate(ROOT)
    except Exception as exc:
        print(
            "P3 integrity generation: FAIL — "
            f"{type(exc).__name__}: {exc}"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
