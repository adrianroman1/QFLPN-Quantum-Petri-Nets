from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from P3.tools import write_github_summary as summary


RUN_ID = "p3-12345-1"
BRANCH = "main"


def create_required_evidence(root: Path) -> None:
    for relative in summary.REQUIRED_EVIDENCE:
        if relative in {"P3/MANIFEST.txt", "P3/SHA256SUMS.txt"}:
            continue

        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)

        if relative.endswith("environment.json"):
            path.write_text(
                json.dumps({
                    "schema": "qflpn-p3-environment-v1",
                    "run_id": RUN_ID,
                }),
                encoding="utf-8",
            )
        elif relative.endswith("environment.txt"):
            path.write_text(
                f"QFLPN P3 EXECUTION ENVIRONMENT\nRUN_ID: {RUN_ID}\n",
                encoding="utf-8",
            )
        else:
            path.write_text("test evidence\n", encoding="utf-8")

    manifest_entries = sorted(
        relative
        for relative in summary.REQUIRED_EVIDENCE
        if relative not in {"P3/MANIFEST.txt", "P3/SHA256SUMS.txt"}
    )

    manifest_path = root / "P3/MANIFEST.txt"
    manifest_path.write_text(
        "".join(f"{relative}\n" for relative in manifest_entries),
        encoding="utf-8",
    )

    checksum_lines = []

    for relative in manifest_entries:
        digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        checksum_lines.append(f"{digest}  {relative}\n")

    (root / "P3/SHA256SUMS.txt").write_text(
        "".join(checksum_lines),
        encoding="ascii",
    )


def local_verdict() -> dict:
    return {
        "verdict": "P3_ACCEPTED",
        "integrity": {
            "manifest_entries": 25,
            "sha256_entries_verified": 25,
        },
        "benchmark": {
            "schema": "qflpn-benchmark-v2",
            "run_id": RUN_ID,
            "records": 1,
            "dimension": 1_000_000,
            "non_zero_count": 2_000_000,
            "speedup": 2.0,
            "max_absolute_error": 1e-12,
        },
        "ci_stages": {
            "p3_benchmark": "success",
            "p3_integrity_generate": "success",
        },
    }


def remote_verdict(**overrides) -> dict:
    data = {
        "schema": "qflpn-p3-remote-integrity-v1",
        "validation": "PASS",
        "remote": "origin",
        "branch": BRANCH,
        "commit": "a" * 40,
        "manifest_entries": 2,
        "verified_remote_blobs": 2,
        "files": [
            {
                "path": "P3/a.txt",
                "sha256": "b" * 64,
                "status": "PASS",
            },
            {
                "path": "P3/b.txt",
                "sha256": "c" * 64,
                "status": "PASS",
            },
        ],
    }
    data.update(overrides)
    return data


def remote_verdict_for_root(root: Path, **overrides) -> dict:
    manifest, checksums = summary.load_local_integrity_inventory(root)

    files = [
        {
            "path": relative,
            "sha256": checksums[relative],
            "status": "PASS",
        }
        for relative in manifest
    ]

    data = {
        "schema": "qflpn-p3-remote-integrity-v1",
        "validation": "PASS",
        "remote": "origin",
        "branch": BRANCH,
        "commit": "a" * 40,
        "manifest_entries": len(manifest),
        "verified_remote_blobs": len(files),
        "files": files,
    }
    data.update(overrides)
    return data


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def test_remote_result_accepts_complete_inventory() -> None:
    valid, reason = summary.verify_remote_result(
        remote_verdict(),
        expected_branch=BRANCH,
    )

    assert valid is True
    assert "All remote manifest paths" in reason


@pytest.mark.parametrize(
    ("overrides", "expected_branch"),
    [
        ({"validation": "FAIL"}, BRANCH),
        ({"branch": "fix/other"}, BRANCH),
        ({"verified_remote_blobs": 1}, BRANCH),
        ({"manifest_entries": 3}, BRANCH),
        ({"files": []}, BRANCH),
        (
            {
                "files": [
                    {
                        "path": "P3/a.txt",
                        "sha256": "x",
                        "status": "PASS",
                    }
                ]
            },
            BRANCH,
        ),
        ({"commit": "not-a-commit"}, BRANCH),
        ({"commit": ""}, BRANCH),
    ],
)
def test_remote_result_rejects_invalid_inventory(
    overrides: dict,
    expected_branch: str,
) -> None:
    valid, _ = summary.verify_remote_result(
        remote_verdict(**overrides),
        expected_branch=expected_branch,
    )
    assert valid is False


def test_remote_result_rejects_manifest_path_set_mismatch() -> None:
    remote = remote_verdict(
        files=[
            {
                "path": "P3/other.txt",
                "sha256": "b" * 64,
                "status": "PASS",
            },
            {
                "path": "P3/b.txt",
                "sha256": "c" * 64,
                "status": "PASS",
            },
        ]
    )

    valid, reason = summary.verify_remote_result(
        remote,
        expected_branch=BRANCH,
        expected_manifest=["P3/a.txt", "P3/b.txt"],
    )

    assert valid is False
    assert "differs from local MANIFEST.txt" in reason


def test_remote_result_rejects_checksum_mismatch() -> None:
    remote = remote_verdict()

    valid, reason = summary.verify_remote_result(
        remote,
        expected_branch=BRANCH,
        expected_manifest=["P3/a.txt", "P3/b.txt"],
        expected_checksums={
            "P3/a.txt": "d" * 64,
            "P3/b.txt": "c" * 64,
        },
    )

    assert valid is False
    assert "differs from local SHA256SUMS.txt" in reason


def test_effective_verdict_requires_every_gate() -> None:
    assert summary.effective_verdict(
        "P3_ACCEPTED", [], True, RUN_ID, RUN_ID
    ) == "P3_ACCEPTED"

    assert summary.effective_verdict(
        "P3_REJECTED", [], True, RUN_ID, RUN_ID
    ) == "P3_REJECTED"

    assert summary.effective_verdict(
        "P3_ACCEPTED", ["P3/file.txt"], True, RUN_ID, RUN_ID
    ) == "P3_REJECTED"

    assert summary.effective_verdict(
        "P3_ACCEPTED", [], False, RUN_ID, RUN_ID
    ) == "P3_REJECTED"

    assert summary.effective_verdict(
        "P3_ACCEPTED", [], True, "p3-other-run", RUN_ID
    ) == "P3_REJECTED"


def test_build_summary_accepts_local_and_remote_pass(
    tmp_path: Path,
) -> None:
    create_required_evidence(tmp_path)

    local_path = write_json(
        tmp_path / "local-verdict.json",
        local_verdict(),
    )
    remote_path = write_json(
        tmp_path / "remote-verdict.json",
        remote_verdict_for_root(tmp_path),
    )

    rendered = summary.build_summary(
        tmp_path,
        local_path,
        remote_path,
        RUN_ID,
        BRANCH,
    )

    assert "Final verdict: **P3_ACCEPTED**" in rendered
    assert "Remote result: **PASS**" in rendered
    assert "Remote blobs verified:" in rendered
    assert "Validation: `PASS (independent final verifier)`" in rendered
    assert "P3/MANIFEST.txt" in rendered
    assert "P3/SHA256SUMS.txt" in rendered


def test_build_summary_rejects_remote_failure(
    tmp_path: Path,
) -> None:
    create_required_evidence(tmp_path)

    local_path = write_json(
        tmp_path / "local-verdict.json",
        local_verdict(),
    )
    remote_path = write_json(
        tmp_path / "remote-verdict.json",
        remote_verdict_for_root(tmp_path, validation="FAIL"),
    )

    rendered = summary.build_summary(
        tmp_path,
        local_path,
        remote_path,
        RUN_ID,
        BRANCH,
    )

    assert "Final verdict: **P3_REJECTED**" in rendered
    assert "Remote result: **FAIL**" in rendered


def test_build_summary_rejects_missing_mandatory_evidence(
    tmp_path: Path,
) -> None:
    create_required_evidence(tmp_path)
    (tmp_path / "P3/reports/benchmark-report.md").unlink()

    local_path = write_json(
        tmp_path / "local-verdict.json",
        local_verdict(),
    )
    remote_path = write_json(
        tmp_path / "remote-verdict.json",
        remote_verdict_for_root(tmp_path),
    )

    rendered = summary.build_summary(
        tmp_path,
        local_path,
        remote_path,
        RUN_ID,
        BRANCH,
    )

    assert "Final verdict: **P3_REJECTED**" in rendered
    assert "P3/reports/benchmark-report.md" in rendered


def test_build_summary_rejects_environment_run_id_mismatch(
    tmp_path: Path,
) -> None:
    create_required_evidence(tmp_path)

    environment_json = tmp_path / "P3/reports/environment.json"
    environment_json.write_text(
        json.dumps({
            "schema": "qflpn-p3-environment-v1",
            "run_id": "p3-another-run",
        }),
        encoding="utf-8",
    )

    local_path = write_json(
        tmp_path / "local-verdict.json",
        local_verdict(),
    )
    remote_path = write_json(
        tmp_path / "remote-verdict.json",
        remote_verdict_for_root(tmp_path),
    )

    rendered = summary.build_summary(
        tmp_path,
        local_path,
        remote_path,
        RUN_ID,
        BRANCH,
    )

    assert "Final verdict: **P3_REJECTED**" in rendered
    assert "environment.json or RUN_ID binding" in rendered


def test_build_summary_rejects_benchmark_run_id_mismatch(
    tmp_path: Path,
) -> None:
    create_required_evidence(tmp_path)

    verdict = local_verdict()
    verdict["benchmark"]["run_id"] = "p3-another-run"

    local_path = write_json(
        tmp_path / "local-verdict.json",
        verdict,
    )
    remote_path = write_json(
        tmp_path / "remote-verdict.json",
        remote_verdict_for_root(tmp_path),
    )

    rendered = summary.build_summary(
        tmp_path,
        local_path,
        remote_path,
        RUN_ID,
        BRANCH,
    )

    assert "Final verdict: **P3_REJECTED**" in rendered


def test_pull_request_reports_pending_publication(
    tmp_path: Path,
) -> None:
    create_required_evidence(tmp_path)

    local_path = write_json(
        tmp_path / "local-verdict.json",
        local_verdict(),
    )
    remote_path = write_json(
        tmp_path / "remote-verdict.json",
        {
            "schema": "qflpn-p3-remote-integrity-v1",
            "validation": "NOT_APPLICABLE",
            "branch": "pull_request",
            "manifest_entries": 0,
            "verified_remote_blobs": 0,
            "files": [],
            "reason": "PR publication is read-only",
        },
    )

    rendered = summary.build_summary(
        tmp_path,
        local_path,
        remote_path,
        RUN_ID,
        BRANCH,
        remote_required=False,
    )

    assert (
        "Final verdict: **P3_VALIDATED_PENDING_PUBLICATION**"
        in rendered
    )
    assert "Remote result: **NOT APPLICABLE**" in rendered
    assert "Remote publication is not applicable" in rendered


def test_pull_request_rejects_invalid_remote_status(
    tmp_path: Path,
) -> None:
    create_required_evidence(tmp_path)

    local_path = write_json(
        tmp_path / "local-verdict.json",
        local_verdict(),
    )
    remote_path = write_json(
        tmp_path / "remote-verdict.json",
        remote_verdict_for_root(tmp_path, validation="PASS"),
    )

    rendered = summary.build_summary(
        tmp_path,
        local_path,
        remote_path,
        RUN_ID,
        BRANCH,
        remote_required=False,
    )

    assert "Final verdict: **P3_REJECTED**" in rendered


def test_build_summary_rejects_invalid_local_integrity_inventory(
    tmp_path: Path,
) -> None:
    create_required_evidence(tmp_path)

    manifest = tmp_path / "P3/MANIFEST.txt"
    manifest.write_text("P3/not-in-checksums.txt\n", encoding="utf-8")

    local_path = write_json(
        tmp_path / "local-verdict.json",
        local_verdict(),
    )
    remote_path = write_json(
        tmp_path / "remote-verdict.json",
        remote_verdict(),
    )

    rendered = summary.build_summary(
        tmp_path,
        local_path,
        remote_path,
        RUN_ID,
        BRANCH,
    )

    assert "Final verdict: **P3_REJECTED**" in rendered
    assert "Local integrity inventory" in rendered
