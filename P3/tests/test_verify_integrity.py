"""Regression tests for the independent P3 integrity verifier."""

import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "verify_integrity.py"
)

SPEC = importlib.util.spec_from_file_location(
    "verify_integrity",
    MODULE_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def create_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "P3"

    (root / "code").mkdir(parents=True)

    (root / "code" / "Example.java").write_text(
        "class Example {}\n",
        encoding="utf-8",
    )

    (root / "README.md").write_text(
        "P3 verify fixture\n",
        encoding="utf-8",
    )

    return root


def test_verify_passes_on_clean_tree(tmp_path: Path):
    root = create_fixture(tmp_path)

    generator = importlib.util.spec_from_file_location(
        "generate_integrity",
        Path(__file__).resolve().parents[1] / "tools" / "generate_integrity.py",
    )
    assert generator is not None and generator.loader is not None
    mod = importlib.util.module_from_spec(generator)
    generator.loader.exec_module(mod)

    mod.generate(root, write=True)

    result = MODULE.verify(root)
    assert result["validation"] == "PASS"


def test_verify_fails_when_manifest_missing(tmp_path: Path):
    root = create_fixture(tmp_path)

    (root / "MANIFEST.txt").write_text("x\n", encoding="utf-8")

    try:
        MODULE.verify(root)
        assert False, "verify() should fail without a checksum file"
    except ValueError:
        pass


def test_verify_fails_when_unsafe_manifest_path_present(tmp_path: Path):
    root = create_fixture(tmp_path)

    generator = importlib.util.spec_from_file_location(
        "generate_integrity",
        Path(__file__).resolve().parents[1] / "tools" / "generate_integrity.py",
    )
    assert generator is not None and generator.loader is not None
    mod = importlib.util.module_from_spec(generator)
    generator.loader.exec_module(mod)

    mod.generate(root, write=True)

    manifest = root / "MANIFEST.txt"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    lines.insert(3, "../escape.txt")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    try:
        MODULE.verify(root)
        assert False, "verify() should reject unsafe manifest paths"
    except ValueError:
        pass
