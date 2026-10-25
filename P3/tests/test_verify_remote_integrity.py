from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from P3.tools import verify_remote_integrity as remote_integrity


RUN_ID = "p3-123456789-1"
SOURCE_COMMIT = "a" * 40
OTHER_RUN_ID = "p3-987654321-1"
OTHER_SOURCE_COMMIT = "b" * 40


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


def evidence_report(
    *,
    run_id: str = RUN_ID,
    source_commit: str = SOURCE_COMMIT,
    validation: str = "PASS",
) -> bytes:
    value = {
        "schema": "qflpn-p3-evidence-consistency-v1",
        "validation": validation,
        "run_id": run_id,
        "source_commit": source_commit,
        "evidence": {
            "environment": "PASS",
            "benchmark_csv": "PASS",
            "run_checksums": "PASS",
        },
        "verified_run_checksum_files": [
            "benchmark_results_v2.csv",
            "benchmark-report.json",
            "benchmark-report.md",
            "benchmark-report.txt",
            "validation-report.json",
        ],
        "csv_dimension": 100,
        "csv_nnz": 200,
    }
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def build_package(
    work: Path,
    *,
    run_id: str = RUN_ID,
    source_commit: str = SOURCE_COMMIT,
    validation: str = "PASS",
    include_evidence: bool = True,
) -> None:
    payloads = {
        "P3/reports/environment.txt": b"runner=linux\n",
        "P3/reports/benchmark-report.md": b"# Benchmark\n",
        "P3/benchmarks/benchmark_results_v2.csv": (
            f"run_id,dimension\n{run_id},100\n".encode("utf-8")
        ),
    }
    if include_evidence:
        payloads["P3/reports/evidence-consistency.json"] = evidence_report(
            run_id=run_id,
            source_commit=source_commit,
            validation=validation,
        )

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


@pytest.fixture
def remote_repository(tmp_path: Path) -> tuple[Path, Path]:
    work = tmp_path / "work"
    bare = tmp_path / "remote.git"
    work.mkdir()

    command("git", "init", "-b", "main", str(work))
    command("git", "init", "--bare", str(bare))

    command("git", "config", "user.name", "P3 Test", cwd=work)
    command(
        "git",
        "config",
        "user.email",
        "p3-test@example.invalid",
        cwd=work,
    )

    build_package(work)
    command("git", "add", "P3", cwd=work)
    command("git", "commit", "-m", "initial P3 evidence", cwd=work)
    command("git", "remote", "add", "origin", str(bare), cwd=work)
    command("git", "push", "-u", "origin", "main", cwd=work)

    return work, bare


def verify(work: Path, **overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "remote": "origin",
        "branch": "main",
        "run_id": RUN_ID,
        "source_commit": SOURCE_COMMIT,
    }
    arguments.update(overrides)
    return remote_integrity.verify_remote(work, **arguments)


def publish_changed_package(work: Path, message: str) -> None:
    command("git", "add", "-A", cwd=work)
    command("git", "commit", "-m", message, cwd=work)
    command("git", "push", "origin", "main", cwd=work)


def test_verify_remote_checks_every_blob_and_provenance(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    result = verify(work)

    assert result["schema"] == "qflpn-p3-remote-integrity-v2"
    assert result["validation"] == "PASS"
    assert result["manifest_entries"] == 4
    assert result["verified_remote_blobs"] == 4
    assert result["branch"] == "main"
    assert len(result["commit"]) == 40

    assert result["run_id"] == RUN_ID
    assert result["source_commit"] == SOURCE_COMMIT

    provenance = result["evidence_consistency"]
    assert provenance["validation"] == "PASS"
    assert provenance["run_id"] == RUN_ID
    assert provenance["source_commit"] == SOURCE_COMMIT
    assert provenance["status"] == "PASS"

    assert all(
        item["status"] == "PASS"
        for item in result["files"]
    )


def test_remote_publication_commit_is_not_source_commit(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    result = verify(work)

    # The source revision and the later publication commit have
    # different meanings and must not be conflated.
    assert result["commit"] != SOURCE_COMMIT
    assert result["source_commit"] == SOURCE_COMMIT


def test_verify_remote_rejects_different_run_id(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="RUN_ID mismatch",
    ):
        verify(work, run_id=OTHER_RUN_ID)


def test_verify_remote_rejects_different_source_commit(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="SOURCE_COMMIT mismatch",
    ):
        verify(work, source_commit=OTHER_SOURCE_COMMIT)


@pytest.mark.parametrize(
    ("run_id", "source_commit", "validation", "message"),
    [
        (OTHER_RUN_ID, SOURCE_COMMIT, "PASS", "RUN_ID mismatch"),
        (RUN_ID, OTHER_SOURCE_COMMIT, "PASS", "SOURCE_COMMIT mismatch"),
        (RUN_ID, SOURCE_COMMIT, "NOT_RUN", "not PASS"),
    ],
)
def test_verify_remote_rejects_invalid_provenance_in_published_report(
    remote_repository: tuple[Path, Path],
    run_id: str,
    source_commit: str,
    validation: str,
    message: str,
) -> None:
    work, _ = remote_repository

    build_package(
        work,
        run_id=run_id,
        source_commit=source_commit,
        validation=validation,
    )
    publish_changed_package(work, "publish invalid provenance")

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match=message,
    ):
        verify(work)


def test_verify_remote_rejects_missing_evidence_consistency_report(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    build_package(work, include_evidence=False)
    publish_changed_package(work, "remove evidence consistency report")

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="does not include",
    ):
        verify(work)


def test_verify_remote_fails_when_remote_blob_hash_is_wrong(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    target = work / "P3/reports/environment.txt"
    target.write_text("tampered environment\n", encoding="utf-8")
    publish_changed_package(work, "tamper evidence")

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="SHA-256 mismatch",
    ):
        verify(work)


def test_verify_remote_fails_when_manifest_blob_is_missing(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    (work / "P3/reports/environment.txt").unlink()
    publish_changed_package(work, "remove manifested file")

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="missing or is not a blob",
    ):
        verify(work)


def test_parse_manifest_rejects_duplicate_paths() -> None:
    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="duplicate",
    ):
        remote_integrity.parse_manifest(
            b"P3/a.txt\nP3/a.txt\n"
        )


def test_parse_manifest_rejects_unsorted_paths() -> None:
    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="not sorted",
    ):
        remote_integrity.parse_manifest(
            b"P3/z.txt\nP3/a.txt\n"
        )


def test_parse_manifest_rejects_missing_final_newline() -> None:
    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="final newline",
    ):
        remote_integrity.parse_manifest(b"P3/a.txt")


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
        "P3//double-separator.txt",
        " P3/leading-space.txt",
        "P3/trailing-space.txt ",
    ],
)
def test_validate_relative_path_rejects_unsafe_paths(path: str) -> None:
    with pytest.raises(remote_integrity.RemoteIntegrityError):
        remote_integrity.validate_relative_path(path)


def test_parse_checksums_rejects_invalid_digest() -> None:
    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="Malformed",
    ):
        remote_integrity.parse_checksums(
            b"not-a-sha256  P3/reports/report.txt\n"
        )


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


def test_parse_checksums_rejects_empty_inventory() -> None:
    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="no entries",
    ):
        remote_integrity.parse_checksums(b"\n")


def test_parse_checksums_rejects_manifest_checksum_set_mismatch(
    remote_repository: tuple[Path, Path],
) -> None:
    work, _ = remote_repository

    checksums = work / "P3/SHA256SUMS.txt"
    lines = checksums.read_text(encoding="ascii").splitlines()
    checksums.write_text(
        "\n".join(lines[:-1]) + "\n",
        encoding="ascii",
    )
    publish_changed_package(work, "remove checksum entry")

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="path sets differ",
    ):
        verify(work)


@pytest.mark.parametrize(
    ("run_id", "source_commit"),
    [
        ("", SOURCE_COMMIT),
        ("not-a-p3-run", SOURCE_COMMIT),
        ("p3-123-abc", SOURCE_COMMIT),
        (RUN_ID, ""),
        (RUN_ID, "A" * 40),
        (RUN_ID, "a" * 39),
        (RUN_ID, "g" * 40),
    ],
)
def test_verify_remote_rejects_invalid_expected_identity(
    remote_repository: tuple[Path, Path],
    run_id: str,
    source_commit: str,
) -> None:
    work, _ = remote_repository

    with pytest.raises(remote_integrity.RemoteIntegrityError):
        verify(
            work,
            run_id=run_id,
            source_commit=source_commit,
        )


def test_parse_evidence_consistency_rejects_invalid_json() -> None:
    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="invalid JSON",
    ):
        remote_integrity.parse_evidence_consistency(
            b"{invalid",
            expected_run_id=RUN_ID,
            expected_source_commit=SOURCE_COMMIT,
        )


def test_parse_evidence_consistency_rejects_wrong_schema() -> None:
    raw = json.dumps({
        "schema": "wrong-schema",
        "validation": "PASS",
        "run_id": RUN_ID,
        "source_commit": SOURCE_COMMIT,
    }).encode("utf-8")

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="schema mismatch",
    ):
        remote_integrity.parse_evidence_consistency(
            raw,
            expected_run_id=RUN_ID,
            expected_source_commit=SOURCE_COMMIT,
        )


def test_parse_evidence_consistency_rejects_non_object_json() -> None:
    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="JSON object",
    ):
        remote_integrity.parse_evidence_consistency(
            b"[]",
            expected_run_id=RUN_ID,
            expected_source_commit=SOURCE_COMMIT,
        )


def test_atomic_write_json_writes_valid_json(tmp_path: Path) -> None:
    destination = tmp_path / "reports" / "remote-integrity.json"
    value = {
        "schema": "qflpn-p3-remote-integrity-v2",
        "validation": "PASS",
        "run_id": RUN_ID,
    }

    remote_integrity.atomic_write_json(destination, value)

    assert json.loads(destination.read_text(encoding="utf-8")) == value
    assert destination.read_bytes().endswith(b"\n")


def test_atomic_write_json_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}\n", encoding="utf-8")
    link = tmp_path / "link.json"

    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are not supported on this platform")

    with pytest.raises(
        remote_integrity.RemoteIntegrityError,
        match="symlink",
    ):
        remote_integrity.atomic_write_json(link, {"validation": "PASS"})

    assert target.read_text(encoding="utf-8") == "{}\n"
