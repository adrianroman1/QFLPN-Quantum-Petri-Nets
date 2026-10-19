"""Pytest configuration for the P2 test suite."""

from __future__ import annotations

import sys
from pathlib import Path


P2_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = P2_ROOT / "code"

if not CODE_DIR.is_dir():
    raise RuntimeError(f"Required source directory is missing: {CODE_DIR}")

code_path = str(CODE_DIR)

if code_path not in sys.path:
    sys.path.insert(0, code_path)
