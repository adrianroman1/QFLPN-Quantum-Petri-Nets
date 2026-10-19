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

            if directory in EXCLUDED_DIRS:
                continue

            retained_directories.append(directory)

        directories[:] = retained_directories

        for filename in filenames:
            candidate = current_path / filename

            if candidate.is_symlink():
                raise ValueError(
                    f"Symbolic file is forbidden: {candidate}"
                )

            relative = candidate.relative_to(root)

            if candidate == output:
                continue

            if filename in EXCLUDED_NAMES:
                continue

            if candidate.suffix.lower() in EXCLUDED_SUFFIXES:
                continue

            if any(part in EXCLUDED_DIRS for part in relative.parts):
                continue

            if not candidate.is_file():
                continue

            files.append(candidate)

    return sorted(
        files,
        key=lambda item: item.relative_to(root).as_posix(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    root = P2_ROOT.resolve()
    output = args.output.resolve()

    try:
        output.relative_to(root)
        files = collect_files(root, output)
    except (OSError, ValueError) as exc:
        print("FAIL:", exc)
        return 2

    if not files:
        print("FAIL: no source files found")
        return 1

    lines = [
        "# QFLPN P2 SHA-256 source manifest",
        "# Format: SHA256  relative/path",
        f"# File count: {len(files)}",
    ]

    for path in files:
        relative = path.relative_to(root).as_posix()
        lines.append(f"{sha256_file(path)}  {relative}")

    content = "\n".join(lines) + "\n"

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(output)
    except OSError as exc:
        print("FAIL: cannot write manifest:", exc)
        return 2

    print("Manifest:", output)
    print("Files included:", len(files))
    print("Manifest SHA-256:", sha256_file(output))
    print("VERDICT: MANIFEST_GENERATED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
