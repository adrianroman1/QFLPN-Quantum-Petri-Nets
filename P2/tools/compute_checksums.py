"""Generate separate P2 path manifest and SHA-256 checksum inventory."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = P2_ROOT / "MANIFEST.txt"
CHECKSUM_PATH = P2_ROOT / "SHA256SUMS.txt"

EXCLUDED_DIRECTORIES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "site-packages",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tmp",
}

EXCLUDED_NAMES = {
    "MANIFEST.txt",
    "SHA256SUMS.txt",
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


def collect_files(root: Path) -> list[Path]:
    root = root.resolve(strict=True)
    collected: list[Path] = []

    for current, directories, filenames in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)
        retained: list[str] = []

        for directory in directories:
            candidate = current_path / directory

            if candidate.is_symlink():
                raise ValueError(
                    f"Symbolic directory is forbidden: {candidate}"
                )

            if directory not in EXCLUDED_DIRECTORIES:
                retained.append(directory)

        directories[:] = retained

        for filename in filenames:
            candidate = current_path / filename

            if candidate.is_symlink():
                raise ValueError(
                    f"Symbolic file is forbidden: {candidate}"
                )

            if filename in EXCLUDED_NAMES:
                continue

            if candidate.suffix.lower() in EXCLUDED_SUFFIXES:
                continue

            if filename.endswith(".tmp"):
                continue

            if not candidate.is_file():
                continue

            collected.append(candidate)

    return sorted(
        collected,
        key=lambda path: path.relative_to(root).as_posix(),
    )


def build_outputs(root: Path) -> tuple[str, str, int]:
    files = collect_files(root)

    if not files:
        raise ValueError("No eligible P2 files found.")

    paths: list[str] = []
    sums: list[str] = []

    for path in files:
        relative = path.relative_to(root).as_posix()

        if relative.startswith("../") or relative.startswith("/"):
            raise ValueError(f"Unsafe relative path: {relative}")

        paths.append(relative)
        sums.append(
            f"{sha256_file(path)}  {relative}"
        )

    manifest = (
        "# QFLPN P2 file inventory\n"
        f"# File count: {len(paths)}\n"
        + "\n".join(paths)
        + "\n"
    )

    checksum_text = (
        "# QFLPN P2 SHA-256 checksums\n"
        f"# File count: {len(sums)}\n"
        + "\n".join(sums)
        + "\n"
    )

    return manifest, checksum_text, len(files)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        path.name + ".tmp"
    )

    if temporary.is_symlink():
        raise ValueError(
            f"Temporary path is a symbolic link: {temporary}"
        )

    temporary.write_text(
        content,
        encoding="utf-8",
        newline="\n",
    )

    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate P2 MANIFEST.txt and SHA256SUMS.txt."
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=P2_ROOT,
    )

    args = parser.parse_args()

    try:
        root = args.root.resolve(strict=True)

        manifest, checksums, count = build_outputs(root)

        atomic_write(
            root / "MANIFEST.txt",
            manifest,
        )

        atomic_write(
            root / "SHA256SUMS.txt",
            checksums,
        )

    except (OSError, ValueError) as exc:
        print("FAIL:", exc)
        return 2

    print("P2 root:", root)
    print("Files inventoried:", count)
    print("Manifest:", root / "MANIFEST.txt")
    print("Checksums:", root / "SHA256SUMS.txt")
    print("VERDICT: P2_INVENTORY_GENERATED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
