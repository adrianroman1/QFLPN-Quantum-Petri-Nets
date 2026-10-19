"""Adversarial tests for the complete P2 SHA256SUMS inventory."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tools.verify_sha256sums import (
    parse_sums,
    verify,
)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def create_fixture(root: Path) -> Path:
    (root / "reports").mkdir(parents=True)

    (root / "reports" / "reference_config.json").write_text(
        '{"schema_version": 1}\n',
        encoding="utf-8",
    )

    (root / "source.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    (root / "README.md").write_text(
        "P2 test fixture\n",
        encoding="utf-8",
    )

    return root


def write_sums(root: Path, path: Path) -> None:
    files = [
        root / "README.md",
        root / "reports" / "reference_config.json",
        root / "source.py",
    ]

    lines = []

    for file in files:
        relative = file.relative_to(root).as_posix()
        lines.append(
            f"{digest(file.read_bytes())}  {relative}"
        )

    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def test_complete_inventory_is_accepted(tmp_path: Path):
    root = create_fixture(tmp_path)
    sums = root / "SHA256SUMS.txt"

    write_sums(root, sums)

    passed, failed, errors = verify(root, sums)

    assert passed == 3
    assert failed == 0
    assert errors == []


def test_missing_inventory_entry_is_rejected(tmp_path: Path):
    root = create_fixture(tmp_path)
    sums = root / "SHA256SUMS.txt"

    write_sums(root, sums)

    lines = [
        line
        for line in sums.read_text(encoding="utf-8").splitlines()
        if not line.endswith("source.py")
    ]

    sums.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    _, failed, errors = verify(root, sums)

    assert failed > 0
    assert any(
        "Missing from SHA256SUMS: source.py" in error
        for error in errors
    )


def test_modified_file_is_rejected(tmp_path: Path):
    root = create_fixture(tmp_path)
    sums = root / "SHA256SUMS.txt"

    write_sums(root, sums)

    (root / "source.py").write_text(
        "value = 999\n",
        encoding="utf-8",
    )

    _, failed, errors = verify(root, sums)

    assert failed > 0
    assert any(
        "SHA-256 mismatch" in error
        for error in errors
    )


def test_unexpected_inventory_path_is_rejected(tmp_path: Path):
    root = create_fixture(tmp_path)
    sums = root / "SHA256SUMS.txt"

    write_sums(root, sums)

    lines = sums.read_text(encoding="utf-8").splitlines()
    lines.append(
        f"{'0' * 64}  nonexistent.py"
    )

    sums.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    _, failed, errors = verify(root, sums)

    assert failed > 0
    assert any(
        "Unexpected SHA256SUMS path" in error
        for error in errors
    )


def test_duplicate_entry_is_rejected(tmp_path: Path):
    root = create_fixture(tmp_path)
    sums = root / "SHA256SUMS.txt"

    write_sums(root, sums)

    lines = sums.read_text(encoding="utf-8").splitlines()
    lines.append(lines[0])

    sums.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    _, failed, errors = verify(root, sums)

    assert failed > 0
    assert any(
        "duplicate path" in error.lower()
        for error in errors
    )


def test_invalid_hash_is_rejected(tmp_path: Path):
    root = create_fixture(tmp_path)
    sums = root / "SHA256SUMS.txt"

    write_sums(root, sums)

    lines = sums.read_text(encoding="utf-8").splitlines()
    lines[0] = f"{'Z' * 64}  README.md"

    sums.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    _, failed, errors = verify(root, sums)

    assert failed > 0
    assert any(
        "invalid SHA-256 digest" in error
        for error in errors
    )


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.py",
        "/tmp/outside.py",
        "./source.py",
        "folder\\source.py",
    ],
)
def test_unsafe_paths_are_rejected(
    tmp_path: Path,
    unsafe_path: str,
):
    sums = tmp_path / "SHA256SUMS.txt"

    sums.write_text(
        f"{'0' * 64}  {unsafe_path}\n",
        encoding="utf-8",
    )

    _, errors = parse_sums(sums)

    assert errors


def test_protected_configuration_is_mandatory(
    tmp_path: Path,
):
    root = tmp_path
    (root / "source.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    sums = root / "SHA256SUMS.txt"
    sums.write_text(
        f"{digest(b'value = 1\\n')}  source.py\n",
        encoding="utf-8",
    )

    _, failed, errors = verify(root, sums)

    assert failed > 0
    assert any(
        "reference_config.json" in error
        for error in errors
    )


def test_inventory_files_are_not_self_hashed(
    tmp_path: Path,
):
    root = create_fixture(tmp_path)
    sums = root / "SHA256SUMS.txt"

    write_sums(root, sums)

    lines = sums.read_text(encoding="utf-8").splitlines()
    lines.append(
        f"{'0' * 64}  SHA256SUMS.txt"
    )

    sums.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    _, errors = parse_sums(sums)

    assert any(
        "excluded path listed" in error
        for error in errors
    )


def test_symbolic_file_is_rejected_when_supported(
    tmp_path: Path,
):
    root = create_fixture(tmp_path)
    target = root / "source.py"
    link = root / "linked.py"

    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symbolic links are unavailable")

    sums = root / "SHA256SUMS.txt"
    write_sums(root, sums)

    _, failed, errors = verify(root, sums)

    assert failed > 0
    assert any(
        "Symbolic file forbidden" in error
        for error in errors
    )
