#!/usr/bin/env python3
"""Deterministic P3 manifest and SHA-256 inventory generator.

The format follows the P1 integrity contract:
- MANIFEST.txt contains one sorted repository-relative POSIX path per line.
- SHA256SUMS.txt contains one SHA-256 entry for each manifest path.
- MANIFEST.txt and SHA256SUMS.txt are excluded from both inventories.
- The generator never follows symbolic links.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P3 = ROOT / "P3"

EXCLUDED_NAMES = {
    "MANIFEST.txt",
    "SHA256SUMS.txt",
}

EXCLUDED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "target",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def inventory_files(root: Path) -> list[Path]:
    """Return eligible regular files below root/P3 in deterministic order.

    Returned paths are absolute Path objects. Their serialized names are
    repository-relative POSIX paths, such as P3/tools/example.py.
    """
    root = Path(root).resolve()
    p3_root = root / "P3"

    if not p3_root.exists():
        raise RuntimeError(f"P3 directory does not exist: {p3_root}")

    if p3_root.is_symlink() or not p3_root.is_dir():
        raise RuntimeError(
            f"Refusing to inventory an unsafe P3 directory: {p3_root}"
        )

    eligible: list[Path] = []

    for current, directory_names, file_names in os.walk(
        p3_root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)

        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in EXCLUDED_DIRS
            and not (current_path / name).is_symlink()
        )

        for name in sorted(file_names):
            candidate = current_path / name

            if name in EXCLUDED_NAMES:
                continue

            if candidate.suffix.lower() in EXCLUDED_SUFFIXES:
                continue

            if candidate.is_symlink() or not candidate.is_file():
                continue

            eligible.append(candidate)

    eligible.sort(
        key=lambda path: path.relative_to(root).as_posix()
    )

    relative_paths = [
        path.relative_to(root).as_posix()
        for path in eligible
    ]

    if len(relative_paths) != len(set(relative_paths)):
        raise RuntimeError("Duplicate paths detected in P3 inventory")

    return eligible


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a UTF-8 text file in its destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary_path, path)
        temporary_path = None

    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def build_inventory_contents(
    root: Path,
    files: list[Path],
) -> tuple[str, str]:
    """Build manifest and checksum contents from one ordered file snapshot."""
    root = Path(root).resolve()

    relative_paths: list[str] = []

    for path in files:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(
                f"Inventory candidate changed or became unsafe: {path}"
            )

        try:
            relative = path.relative_to(root).as_posix()
        except ValueError as exc:
            raise RuntimeError(
                f"Inventory path is outside repository root: {path}"
            ) from exc

        if (
            not relative
            or relative.startswith("/")
            or "\\" in relative
            or ".." in Path(relative).parts
        ):
            raise RuntimeError(
                f"Unsafe repository-relative path: {relative}"
            )

        if not relative.startswith("P3/"):
            raise RuntimeError(
                f"Inventory path is outside P3/: {relative}"
            )

        if Path(relative).name in EXCLUDED_NAMES:
            raise RuntimeError(
                f"Self-referential integrity file in inventory: {relative}"
            )

        relative_paths.append(relative)

    if len(relative_paths) != len(set(relative_paths)):
        raise RuntimeError("Duplicate paths detected in P3 inventory")

    if relative_paths != sorted(relative_paths):
        raise RuntimeError("P3 inventory paths are not sorted")

    manifest_content = "".join(
        relative + "\n"
        for relative in relative_paths
    )

    checksum_lines: list[str] = []

    for path, relative in zip(files, relative_paths):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(
                f"Inventory candidate changed before hashing: {path}"
            )

        digest = sha256_bytes(path.read_bytes())
        checksum_lines.append(f"{digest}  {relative}")

    checksum_content = "".join(
        line + "\n"
        for line in checksum_lines
    )

    return manifest_content, checksum_content


def generate(
    root: Path = ROOT,
    *,
    require_nonempty: bool = True,
) -> tuple[int, int]:
    """Generate P3/MANIFEST.txt and P3/SHA256SUMS.txt.

    Returns:
        (manifest_entry_count, checksum_entry_count)
    """
    root = Path(root).resolve()
    p3_root = root / "P3"

    if not p3_root.is_dir() or p3_root.is_symlink():
        raise RuntimeError(
            f"P3 directory is missing or unsafe: {p3_root}"
        )

    files = inventory_files(root)

    if require_nonempty and not files:
        raise RuntimeError(
            "Refusing to generate an empty P3 integrity inventory"
        )

    manifest_content, checksum_content = build_inventory_contents(
        root,
        files,
    )

    manifest_path = p3_root / "MANIFEST.txt"
    checksum_path = p3_root / "SHA256SUMS.txt"

    # Both contents are fully constructed before either destination is
    # replaced. Each individual replacement is atomic.
    atomic_write_text(manifest_path, manifest_content)
    atomic_write_text(checksum_path, checksum_content)

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
