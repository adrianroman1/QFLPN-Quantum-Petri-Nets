"""Deterministic SHA-256 manifest generation for QFLPN P2."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = P2_ROOT / "MANIFEST.txt"

EXCLUDED_NAMES = {
    "MANIFEST.txt",
    "SHA256SUMS.txt",
}

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


def is_excluded(path: Path) -> bool:
    if path.name in EXCLUDED_NAMES:
        return True

    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True

    if any(
        part in EXCLUDED_DIRECTORIES
        for part in path.parts
    ):
        return True

    return False


def collect_files(root: Path, output: Path) -> list[Path]:
    output_resolved = output.resolve()
    files: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if is_excluded(path.relative_to(root)):
            continue

        if path.is_symlink():
            raise ValueError(
                f"Symbolic links are not allowed: {path}"
            )

        if path.resolve() == output_resolved:
            continue

        files.append(path)

    return sorted(
        files,
        key=lambda item: item.relative_to(root).as_posix(),
    )


def build_manifest(root: Path, files: list[Path]) -> str:
    lines = [
        "# QFLPN P2 SHA-256 manifest",
        "# Format: SHA256  relative/path",
        f"# File count: {len(files)}",
    ]

    for path in files:
        relative = path.relative_to(root).as_posix()
        lines.append(f"{sha256_file(path)}  {relative}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    args = parser.parse_args()

    root = P2_ROOT.resolve()
    output = args.output.resolve()

    if not root.is_dir():
        print("FAIL: P2 root does not exist")
        return 2

    try:
        output.relative_to(root)
        files = collect_files(root, output)
    except (ValueError, OSError) as exc:
        print(f"FAIL: manifest collection: {exc}")
        return 2

    if not files:
        print("FAIL: no files to include")
        return 1

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            build_manifest(root, files),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"FAIL: manifest write: {exc}")
        return 2

    print("Manifest:", output)
    print("Files included:", len(files))
    print("Manifest SHA-256:", sha256_file(output))
    print("VERDICT: MANIFEST_GENERATED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
