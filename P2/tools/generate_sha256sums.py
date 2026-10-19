"""Generate a deterministic SHA256SUMS.txt inventory for P2."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = P2_ROOT / "SHA256SUMS.txt"

EXCLUDED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "site-packages",
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

PROTECTED_REPORT_FILES = {
    "reports/reference_config.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def is_excluded(relative: Path) -> bool:
    if relative.as_posix() in PROTECTED_REPORT_FILES:
        return False

    if relative.name in EXCLUDED_NAMES:
        return True

    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return True

    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return True

    return "reports" in relative.parts


def collect_files(root: Path, output: Path) -> list[Path]:
    root = root.resolve(strict=True)
    output = output.resolve()
    output.relative_to(root)

    files: list[Path] = []

    for current, directories, filenames in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)
        retained = []

        for directory in directories:
            candidate = current_path / directory

            if candidate.is_symlink():
                raise ValueError(
                    f"Symbolic directory forbidden: {candidate}"
                )

            if directory not in EXCLUDED_DIRS:
                retained.append(directory)

        directories[:] = retained

        for filename in filenames:
            candidate = current_path / filename

            if candidate.is_symlink():
                raise ValueError(
                    f"Symbolic file forbidden: {candidate}"
                )

            relative = candidate.relative_to(root)

            if candidate.resolve() == output:
                continue

            if is_excluded(relative):
                continue

            if candidate.is_file():
                files.append(candidate)

    return sorted(
        files,
        key=lambda item: item.relative_to(root).as_posix(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate P2 SHA256SUMS.txt."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    args = parser.parse_args()

    root = P2_ROOT.resolve(strict=True)
    output = args.output.resolve()

    try:
        output.relative_to(root)

        files = collect_files(root, output)

        if not files:
            raise ValueError("No eligible P2 files found")

        config = root / "reports" / "reference_config.json"

        if not config.is_file():
            raise ValueError(
                "Missing protected reference configuration"
            )

        if config not in files:
            raise ValueError(
                "Reference configuration is not included"
            )

        lines = []

        for path in files:
            relative = path.relative_to(root).as_posix()
            lines.append(
                f"{sha256_file(path)}  {relative}"
            )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = output.with_name(output.name + ".tmp")

        if temporary.is_symlink():
            raise ValueError(
                "Temporary output path is a symbolic link"
            )

        temporary.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(output)

    except (OSError, ValueError) as exc:
        print("FAIL:", exc)
        return 2

    print("SHA256SUMS:", output)
    print("Files included:", len(files))
    print("VERDICT: SHA256SUMS_GENERATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
