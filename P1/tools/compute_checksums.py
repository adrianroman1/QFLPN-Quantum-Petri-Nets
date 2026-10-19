"""Deterministic manifest and SHA-256 inventory generator for P1."""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "P1"

EXCLUDED_NAMES = {
    "MANIFEST.txt",
    "SHA256SUMS.txt",
}

EXCLUDED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def inventory_files(root: Path) -> list[Path]:
    """Return every eligible regular file under P1 and GitHub workflows.

    Symlinks, bytecode, cache directories and the two self-referential
    inventory files are excluded. Returned paths use deterministic
    repository-relative POSIX ordering.
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

                if candidate.suffix in {".pyc", ".pyo"}:
                    continue

                if candidate.is_symlink() or not candidate.is_file():
                    continue

                eligible.add(candidate)

    return sorted(
        eligible,
        key=lambda path: path.relative_to(root).as_posix(),
    )


def atomic_write_text(path: Path, content: str) -> None:
    """Write UTF-8 text through a temporary file and atomic replacement.

    The temporary file is created in the destination directory so that
    os.replace operates on the same filesystem.
    """
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

        if relative.startswith("/") or ".." in Path(relative).parts:
            raise RuntimeError(
                f"Unsafe repository-relative path: {relative}"
            )

        relative_paths.append(relative)

    if len(relative_paths) != len(set(relative_paths)):
        raise RuntimeError("Duplicate paths detected in P1 inventory")

    if relative_paths != sorted(relative_paths):
        raise RuntimeError("Inventory paths are not sorted")

    if any(
        relative in EXCLUDED_NAMES
        or Path(relative).name in EXCLUDED_NAMES
        for relative in relative_paths
    ):
        raise RuntimeError(
            "Self-referential inventory file found in eligible paths"
        )

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

        checksum_lines.append(
            f"{digest}  {relative}"
        )

    checksum_content = "".join(
        line + "\n"
        for line in checksum_lines
    )

    return manifest_content, checksum_content


def main() -> None:
    if not P1.is_dir():
        raise SystemExit("P1 directory does not exist")

    if P1.is_symlink():
        raise SystemExit("Refusing to inventory a symlinked P1 directory")

    files = inventory_files(ROOT)

    if not files:
        raise SystemExit(
            "Refusing to generate an empty P1 inventory"
        )

    try:
        manifest_content, checksum_content = build_inventory_contents(
            ROOT,
            files,
        )

        manifest_path = P1 / "MANIFEST.txt"
        checksum_path = P1 / "SHA256SUMS.txt"

        # Each destination is replaced only after its complete temporary
        # file has been written and flushed.
        atomic_write_text(
            manifest_path,
            manifest_content,
        )

        atomic_write_text(
            checksum_path,
            checksum_content,
        )

    except Exception as exc:
        raise SystemExit(
            f"P1 inventory generation failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    print(
        f"Manifest entries: {len(files)}; "
        f"SHA-256 entries: {len(files)}"
    )


if __name__ == "__main__":
    main()
