"""Create matching final manifest and SHA-256 inventories."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "P1"
EXCLUDED_NAMES = {"MANIFEST.txt", "SHA256SUMS.txt"}
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inventory_files(root: Path) -> list[Path]:
    candidates = []
    for base in (root / "P1", root / ".github" / "workflows"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            if path.name in EXCLUDED_NAMES or path.suffix == ".pyc":
                continue
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            candidates.append(path)
    return sorted(set(candidates), key=lambda p: p.relative_to(root).as_posix())


def main() -> None:
    files = inventory_files(ROOT)
    relative_paths = [path.relative_to(ROOT).as_posix() for path in files]
    (P1 / "MANIFEST.txt").write_text("".join(path + "\n" for path in relative_paths), encoding="utf-8")
    checksum_lines = [f"{sha256_bytes(path.read_bytes())}  {rel}" for path, rel in zip(files, relative_paths)]
    (P1 / "SHA256SUMS.txt").write_text("".join(line + "\n" for line in checksum_lines), encoding="utf-8")
    print(f"Manifest entries: {len(relative_paths)}; SHA-256 entries: {len(checksum_lines)}")


if __name__ == "__main__":
    main()
