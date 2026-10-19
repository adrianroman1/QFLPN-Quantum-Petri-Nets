"""Deterministic manifest and SHA-256 inventory generator for P1."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "P1"

EXCLUDED_NAMES = {"MANIFEST.txt", "SHA256SUMS.txt"}
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inventory_files(root: Path) -> list[Path]:
    """Return every eligible regular file under P1 and GitHub workflows.

    Symlinks, bytecode, cache directories and the two self-referential
    inventory files are excluded. Paths are returned in POSIX sort order.
    """
    eligible: set[Path] = set()

    scan_roots = (
        root / "P1",
        root / ".github" / "workflows",
    )

    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        if scan_root.is_symlink() or not scan_root.is_dir():
            continue

        for current, directory_names, file_names in os.walk(
            scan_root,
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

            for name in file_names:
                candidate = current_path / name

                if name in EXCLUDED_NAMES:
                    continue
                if candidate.suffix == ".pyc":
                    continue
                if candidate.is_symlink() or not candidate.is_file():
                    continue

                eligible.add(candidate)

    return sorted(
        eligible,
        key=lambda path: path.relative_to(root).as_posix(),
    )


def main() -> None:
    if not P1.is_dir():
        raise SystemExit("P1 directory does not exist")

    files = inventory_files(ROOT)

    if not files:
        raise SystemExit("Refusing to generate an empty P1 inventory")

    relative_paths = [
        path.relative_to(ROOT).as_posix()
        for path in files
    ]

    if len(relative_paths) != len(set(relative_paths)):
        raise SystemExit("Duplicate paths detected in P1 inventory")

    manifest_content = "".join(
        relative_path + "\n"
        for relative_path in relative_paths
    )

    checksum_lines = [
        f"{sha256_bytes(path.read_bytes())}  {relative_path}"
        for path, relative_path in zip(files, relative_paths)
    ]

    checksum_content = "".join(
        line + "\n"
        for line in checksum_lines
    )

    manifest_path = P1 / "MANIFEST.txt"
    checksum_path = P1 / "SHA256SUMS.txt"

    manifest_path.write_text(
        manifest_content,
        encoding="utf-8",
        newline="\n",
    )

    checksum_path.write_text(
        checksum_content,
        encoding="utf-8",
        newline="\n",
    )

    print(
        f"Manifest entries: {len(relative_paths)}; "
        f"SHA-256 entries: {len(checksum_lines)}"
    )


if __name__ == "__main__":
    main()
