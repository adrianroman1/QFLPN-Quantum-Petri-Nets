from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from P3.tools import verify_remote_integrity as remote_integrity


def command(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def remote_repository(tmp_path: Path) -> tuple[Path, Path]:
    work = tmp_path / "work"
    bare = tmp_path / "remote.git"
    work.mkdir()

    command("git", "init", "-b", "main", str(work))
    command("git", "init", "--bare", str(bare))

    command(
        "git", "config", "user.name", "P3 Test",
        cwd=work,
    )
    command(
        "git", "config", "user.email", "p3-test@example.invalid",
        cwd=work,
    )

    payloads = {
        "P3/reports/environment.txt": b"runner=linux\n",
        "P3/reports/benchmark-report.md": b"# Benchmark\n",
        "P3/benchmarks/benchmark_results_v2.csv": (
            b"run_id,dimension\np3-test-1,100\n"
        ),
    }

    for relative, content in payloads.items():
        path = work / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    paths = sorted(payloads)
    manifest = "".join(path + "\n" for path in paths)
    checksums = "".join(
        f"{sha256(payloads[path])}  {path}\n"
        for path in paths
    )

    (work / "P3/MANIFEST.txt").write_text(
        manifest,
        encoding="utf-8",
    )
    (work / "P3/SHA256SUMS.txt").write_text(
        checksums,
        encoding="ascii",
    )

    command("git", "add", "P3", cwd=work)
    command("git", "commit", "-m", "initial P3 evidence", cwd=work)
    command("git", "remote", "add", "origin", str(bare), cwd=work)
    command("git", "push", "-u", "origin", "main", cwd=work)

    return work, bare


def test_verify_remote_checks_every_manifest_blob(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    result = remote_integrity.verify_remote(
        work,
        remote="origin",
        branch="main",
    )

    assert result["validation"] == "PASS"
    assert result["manifest_entries"] == 3
    assert result["verified_remote_blobs"] == 3
    assert result["branch"] == "main"
    assert len(result["commit"]) == 40
    assert all(item["status"] == "PASS" for item in result["files"])


def test_verify_remote_fails_when_remote_blob_hash_is_wrong(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    target = work / "P3/reports/environment.txt"
    target.write_text("tampered environment\n", encoding="utf-8")

    command("git", "add", "P3/reports/environment.txt", cwd=work)
    command("git", "commit", "-m", "tamper evidence", cwd=work)
    command("git", "push", "origin", "main", cwd=work)

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="SHA-256 mismatch",
    ):
        remote_integrity.verify_remote(
            work,
            remote="origin",
            branch="main",
        )


def test_verify_remote_fails_when_remote_manifest_path_is_missing(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    missing = work / "P3/reports/environment.txt"
    missing.unlink()

    command("git", "add", "-A", cwd=work)
    command("git", "commit", "-m", "remove manifested file", cwd=work)
    command("git", "push", "origin", "main", cwd=work)

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="missing or is not a blob",
    ):
        remote_integrity.verify_remote(
            work,
            remote="origin",
            branch="main",
        )


def test_parse_manifest_rejects_duplicate_paths() -> None:
    raw = (
        b"P3/a.txt\n"
        b"P3/a.txt\n"
    )

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="duplicate",
    ):
        remote_integrity.parse_manifest(raw)


def test_parse_manifest_rejects_unsorted_paths() -> None:
    raw = (
        b"P3/z.txt\n"
        b"P3/a.txt\n"
    )

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="not sorted",
    ):
        remote_integrity.parse_manifest(raw)


@pytest.mark.parametrize(
    "path",
    [
        "../outside.txt",
        "/absolute.txt",
        "P3/../outside.txt",
        "P3\\windows.txt",
        "P3/MANIFEST.txt",
        "P3/SHA256SUMS.txt",
        "other/file.txt",
    ],
)
def test_validate_relative_path_rejects_unsafe_paths(path: str) -> None:
    with pytest.raises(remote_integrity.RemoteIntegrityError):
        remote_integrity.validate_relative_path(path)


def test_parse_checksums_rejects_invalid_digest() -> None:
    raw = (
        b"not-a-sha256  P3/reports/report.txt\n"
    )

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="Malformed",
    ):
        remote_integrity.parse_checksums(raw)


def test_parse_checksums_rejects_duplicate_paths() -> None:
    digest = b"a" * 64
    raw = (
        digest + b"  P3/a.txt\n"
        + digest + b"  P3/a.txt\n"
    )

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="Duplicate",
    ):
        remote_integrity.parse_checksums(raw)


def test_parse_checksums_rejects_missing_final_newline() -> None:
    raw = b"a" * 64 + b"  P3/a.txt"

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="final newline",
    ):
        remote_integrity.parse_checksums(raw)


def test_parse_checksums_rejects_manifest_checksum_set_mismatch(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    # A valid checksum file cannot silently omit a manifest path.
    checksums = (
        work / "P3/SHA256SUMS.txt"
    )
    lines = checksums.read_text(encoding="ascii").splitlines()
    checksums.write_text(
        "\n".join(lines[:-1]) + "\n",
        encoding="ascii",
    )

    command("git", "add", "P3/SHA256SUMS.txt", cwd=work)
    command("git", "commit", "-m", "remove checksum entry", cwd=work)
    command("git", "push", "origin", "main", cwd=work)

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="path sets differ",
    ):
        remote_integrity.verify_remote(
            work,
            remote="origin",
            branch="main",
        )
