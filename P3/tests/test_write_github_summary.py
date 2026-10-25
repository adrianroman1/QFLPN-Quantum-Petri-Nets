from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from P3.tools import write_github_summary as summary


RUN_ID = "p3-12345-1"
BRANCH = "main"
SOURCE_COMMIT = "a" * 40


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def consistency_report(
    *,
    run_id: str = RUN_ID,
    source_commit: str = SOURCE_COMMIT,
    evidence: dict | None = None,
    validation: str = "PASS",
    schema: str = "qflpn-p3-evidence-consistency-v1",
) -> dict:
    if evidence is None:
        evidence = {
            key: "PASS"
            for key in summary.REQUIRED_CONSISTENCY_KEYS
        }

    return {
        "schema": schema,
        "validation": validation,
        "run_id": run_id,
        "source_commit": source_commit,
        "evidence": evidence,
        "verified_run_checksum_files": [
            "benchmarks/benchmark_results_v2.csv",
            f"results/raw/{run_id}/benchmark-report.json",
            f"results/raw/{run_id}/benchmark-report.txt",
            f"results/raw/{run_id}/benchmark-report.md",
            f"results/raw/{run_id}/validation-report.json",
        ],
        "csv_dimension": 1_000_000,
        "csv_nnz": 2_000_000,
    }


def create_required_evidence(root: Path) -> None:
    for relative in summary.REQUIRED_EVIDENCE:
        if relative in {
            "P3/MANIFEST.txt",
            "P3/SHA256SUMS.txt",
        }:
            continue

        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)

        if relative == "P3/reports/environment.json":
            write_json(
                path,
                {
                    "schema": "qflpn-p3-environment-v1",
                    "run_id": RUN_ID,
                    "repository": {
                        "commit": SOURCE_COMMIT,
                    },
                    "benchmark": {
                        "dimension": 1_000_000,
                        "warmup_iterations": 5,
                        "measured_iterations": 10,
                    },
                },
            )
        elif relative == "P3/reports/environment.txt":
            path.write_text(
                "QFLPN P3 EXECUTION ENVIRONMENT\n"
                f"RUN_ID: {RUN_ID}\n"
                f"SOURCE_COMMIT: {SOURCE_COMMIT}\n",
                encoding="utf-8",
            )
        else:
            path.write_text(
                "test evidence\n",
                encoding="utf-8",
            )

    write_json(
        root / "P3/reports/evidence-consistency.json",
        consistency_report(),
    )

    manifest_entries = sorted(
        relative
        for relative in summary.REQUIRED_EVIDENCE
        if relative not in {
            "P3/MANIFEST.txt",
            "P3/SHA256SUMS.txt",
        }
    )

    (root / "P3/MANIFEST.txt").write_text(
        "".join(f"{relative}\n" for relative in manifest_entries),
        encoding="utf-8",
    )

    checksum_lines = []
    for relative in manifest_entries:
        digest = hashlib.sha256(
            (root / relative).read_bytes()
        ).hexdigest()
        checksum_lines.append(f"{digest}  {relative}\n")

    (root / "P3/SHA256SUMS.txt").write_text(
        "".join(checksum_lines),
        encoding="ascii",
    )


def local_verdict() -> dict:
    return {
        "verdict": "P3_ACCEPTED",
        "integrity": {
            "manifest_entries": 29,
            "sha256_entries_verified": 29,
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
        "schema": summary.REMOTE_SCHEMA,
        "validation": "PASS",
        "remote": "origin",
        "branch": BRANCH,
        "run_id": RUN_ID,
        "commit": "d" * 40,
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


def remote_verdict_for_root(
    root: Path,
    **overrides,
) -> dict:
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
        "schema": summary.REMOTE_SCHEMA,
        "validation": "PASS",
        "remote": "origin",
        "branch": BRANCH,
        "run_id": RUN_ID,
        "commit": "d" * 40,
        "manifest_entries": len(manifest),
        "verified_remote_blobs": len(files),
        "files": files,
    }
    data.update(overrides)
    return data


def test_producer_string_statuses_are_accepted() -> None:
    evidence = {
        key: "PASS"
        for key in summary.REQUIRED_CONSISTENCY_KEYS
    }

    summary.verify_evidence_consistency(
        root_with_consistency_report(evidence=evidence),
        RUN_ID,
        SOURCE_COMMIT,
    )


def root_with_consistency_report(
    *,
    evidence: dict | None = None,
    source_commit: str = SOURCE_COMMIT,
    run_id: str = RUN_ID,
    validation: str = "PASS",
    schema: str = "qflpn-p3-evidence-consistency-v1",
) -> Path:
    import tempfile

    root = Path(tempfile.mkdtemp())
    report = root / "P3/reports/evidence-consistency.json"
    write_json(
        report,
        consistency_report(
            evidence=evidence,
            source_commit=source_commit,
            run_id=run_id,
            validation=validation,
            schema=schema,
        ),
    )
    return root


def test_object_status_representation_is_also_accepted() -> None:
    evidence = {
        key: {"status": "PASS"}
        for key in summary.REQUIRED_CONSISTENCY_KEYS
    }

    root = root_with_consistency_report(evidence=evidence)

    summary.verify_evidence_consistency(
        root,
        RUN_ID,
        SOURCE_COMMIT,
    )


@pytest.mark.parametrize(
    "bad_status",
    [
        "FAIL",
        "NOT_APPLICABLE",
        None,
        {},
        {"status": "FAIL"},
    ],
)
def test_evidence_consistency_rejects_non_pass_status(
    bad_status,
) -> None:
    evidence = {
        key: "PASS"
        for key in summary.REQUIRED_CONSISTENCY_KEYS
    }
    evidence["csv"] = bad_status

    root = root_with_consistency_report(evidence=evidence)

    with pytest.raises(ValueError, match="not PASS"):
        summary.verify_evidence_consistency(
            root,
            RUN_ID,
            SOURCE_COMMIT,
        )


def test_evidence_consistency_rejects_wrong_run_id() -> None:
    root = root_with_consistency_report(run_id="p3-other-1")

    with pytest.raises(ValueError, match="RUN_ID mismatch"):
        summary.verify_evidence_consistency(
            root,
            RUN_ID,
            SOURCE_COMMIT,
        )


def test_evidence_consistency_rejects_source_commit_mismatch() -> None:
    root = root_with_consistency_report(source_commit="b" * 40)

    with pytest.raises(ValueError, match="SOURCE_COMMIT"):
        summary.verify_evidence_consistency(
            root,
            RUN_ID,
            SOURCE_COMMIT,
        )


def test_evidence_consistency_rejects_wrong_schema() -> None:
    root = root_with_consistency_report(
        schema="qflpn-p3-evidence-consistency-v0"
    )

    with pytest.raises(ValueError, match="schema mismatch"):
        summary.verify_evidence_consistency(
            root,
            RUN_ID,
            SOURCE_COMMIT,
        )


def test_remote_result_accepts_complete_inventory() -> None:
    valid, reason = summary.verify_remote_result(
        remote_verdict(),
        expected_branch=BRANCH,
        expected_run_id=RUN_ID,
    )

    assert valid is True
    assert "All remote manifest paths" in reason


@pytest.mark.parametrize(
    ("overrides", "expected_branch"),
    [
        ({"validation": "FAIL"}, BRANCH),
        ({"branch": "fix/other"}, BRANCH),
        ({"run_id": "p3-other-1"}, BRANCH),
        ({"verified_remote_blobs": 1}, BRANCH),
        ({"manifest_entries": 3}, BRANCH),
        ({"files": []}, BRANCH),
        ({"commit": "not-a-commit"}, BRANCH),
        ({"commit": ""}, BRANCH),
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
    ],
)
def test_remote_result_rejects_invalid_inventory(
    overrides: dict,
    expected_branch: str,
) -> None:
    valid, _ = summary.verify_remote_result(
        remote_verdict(**overrides),
        expected_branch=expected_branch,
        expected_run_id=RUN_ID,
    )
    assert valid is False


def test_remote_result_rejects_old_schema() -> None:
    valid, reason = summary.verify_remote_result(
        remote_verdict(schema="qflpn-p3-remote-integrity-v1"),
        expected_branch=BRANCH,
    )

    assert valid is False
    assert "schema mismatch" in reason


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
    valid, reason = summary.verify_remote_result(
        remote_verdict(),
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
    assert "Evidence consistency: **PASS**" in rendered
    assert "Local MANIFEST/SHA256SUMS and file hashes: **PASS**" in rendered


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

    write_json(
        tmp_path / "P3/reports/environment.json",
        {
            "schema": "qflpn-p3-environment-v1",
            "run_id": "p3-another-run",
            "repository": {"commit": SOURCE_COMMIT},
        },
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
    assert "environment.json or RUN_ID/SOURCE_COMMIT binding" in rendered


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


def test_build_summary_rejects_local_checksum_tampering(
    tmp_path: Path,
) -> None:
    create_required_evidence(tmp_path)

    target = tmp_path / "P3/pom.xml"
    target.write_text("tampered\n", encoding="utf-8")

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
    assert "Local integrity inventory" in rendered


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
            "schema": summary.REMOTE_SCHEMA,
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

    (tmp_path / "P3/MANIFEST.txt").write_text(
        "P3/not-in-checksums.txt\n",
        encoding="utf-8",
    )

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
