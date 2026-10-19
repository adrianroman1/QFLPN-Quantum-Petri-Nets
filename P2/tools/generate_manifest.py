"""Generate a deterministic SHA-256 manifest for the P2 directory."""

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


def sha256_file(path: Path) -> str:
    """Calculate the SHA-256 digest of a file incrementally."""
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def collect_files(root: Path, output: Path) -> list[Path]:
    """Collect regular files in deterministic relative-path order."""
    output_resolved = output.resolve()
    files: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if path.name in EXCLUDED_NAMES:
            continue

        if path.resolve() == output_resolved:
            continue

        files.append(path)

    return sorted(
        files,
        key=lambda item: item.relative_to(root).as_posix(),
    )


def build_manifest(root: Path, files: list[Path]) -> str:
    """Build a UTF-8 manifest with SHA-256 and relative paths."""
    lines = [
        "# QFLPN P2 SHA-256 manifest",
        "# Format: SHA256  relative/path",
        f"# File count: {len(files)}",
    ]

    for path in files:
        relative_path = path.relative_to(root).as_posix()
        digest = sha256_file(path)
        lines.append(f"{digest}  {relative_path}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the P2 SHA-256 manifest."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Manifest output path.",
    )
    args = parser.parse_args()

    root = P2_ROOT.resolve()
    output = args.output.resolve()

    if not root.is_dir():
        print(f"ERROR: P2 directory not found: {root}")
        return 2

    try:
        output.relative_to(root)
    except ValueError:
        print("ERROR: Manifest output must be inside the P2 directory.")
        return 2

    files = collect_files(root, output)

    if not files:
        print("ERROR: No source files found; manifest not generated.")
        return 1

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        manifest = build_manifest(root, files)
        output.write_text(manifest, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: Manifest generation failed: {exc}")
        return 2

    print("Manifest generated:", output)
    print("Files included:", len(files))
    print("Manifest SHA-256:", sha256_file(output))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
