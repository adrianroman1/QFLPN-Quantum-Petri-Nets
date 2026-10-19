"""Generate a deterministic SHA-256 manifest for P2 source artifacts."""

from __future__ import annotations

import argparse
import hashlib
import os

from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = P2_ROOT / "MANIFEST.txt"

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


def _is_excluded(relative: Path) -> bool:
    return (
        relative.name in EXCLUDED_NAMES
        or relative.suffix.lower() in EXCLUDED_SUFFIXES
        or any(
            part in EXCLUDED_DIRS
            for part in relative.parts
        )
    )


def collect_files(root: Path, output: Path) -> list[Path]:
    root = root.resolve()
    output = output.resolve()
    files: list[Path] = []

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
                    f"Symbolic directory is forbidden: {candidate}"
                )

            if directory not in EXCLUDED_DIRS:
                retained_directories.append(directory)

        directories[:] = retained_directories

        for filename in filenames:
            candidate = current_path / filename

            if candidate.is_symlink():
                raise ValueError(
                    f"Symbolic file is forbidden: {candidate}"
                )

            relative = candidate.relative_to(root)

            if candidate == output or _is_excluded(relative):
                continue

            if candidate.is_file():
                files.append(candidate)

    return sorted(
        files,
        key=lambda item: item.relative_to(root).as_posix(),
    )


def build_manifest(root: Path, files: list[Path]) -> str:
    """Build deterministic manifest content from an explicit file list."""

    root = root.resolve()
    normalized: list[tuple[str, Path]] = []
    seen: set[str] = set()

    for path in files:
        candidate = Path(path)

        if candidate.is_symlink():
            raise ValueError(
                f"Symbolic file is forbidden: {candidate}"
            )

        resolved = candidate.resolve(strict=True)

        try:
            relative = resolved.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError(
                f"File is outside manifest root: {candidate}"
            ) from exc

        if not resolved.is_file():
            raise ValueError(
                f"Manifest entry is not a regular file: {candidate}"
            )

        relative_path = Path(relative)

        if _is_excluded(relative_path):
            raise ValueError(
                f"Excluded file cannot be manifested: {relative}"
            )

        if relative in seen:
            raise ValueError(
                f"Duplicate manifest path: {relative}"
            )

        seen.add(relative)
        normalized.append((relative, resolved))

    normalized.sort(key=lambda item: item[0])

    lines = [
        "# QFLPN P2 SHA-256 source manifest",
        "# Format: SHA256  relative/path",
        f"# File count: {len(normalized)}",
    ]

    for relative, path in normalized:
        lines.append(
            f"{sha256_file(path)}  {relative}"
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the deterministic P2 SHA-256 manifest."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    args = parser.parse_args()

    root = P2_ROOT.resolve()
    output = args.output.resolve()

    try:
        output.relative_to(root)
        files = collect_files(root, output)

        if not files:
            print("FAIL: no source files found")
            return 1

        content = build_manifest(root, files)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = output.with_suffix(
            output.suffix + ".tmp"
        )

        temporary.write_text(
            content,
            encoding="utf-8",
        )
        temporary.replace(output)

    except (OSError, ValueError) as exc:
        print("FAIL:", exc)
        return 2

    print("Manifest:", output)
    print("Files included:", len(files))
    print("Manifest SHA-256:", sha256_file(output))
    print("VERDICT: MANIFEST_GENERATED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
