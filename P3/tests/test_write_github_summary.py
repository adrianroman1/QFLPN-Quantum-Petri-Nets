"""Regression tests for the P3 GitHub Actions summary publisher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "write_github_summary.py"
)

SPEC = importlib.util.spec_from_file_location(
    "p3_write_github_summary",
    MODULE_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


RUN_ID = "p3-test-100-1"


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write a JSON fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def create_evidence_tree(root: Path) -> None:
    """Create all mandatory evidence files declared by the publisher."""
    for relative in MODULE.REQUIRED_EVIDENCE:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)

        if relative.endswith("environment.txt"):
            path.write_text(
                "Python: 3.12\nJava: 21\nOS: Linux\n",
                encoding="utf-8",
            )
        else:
            path.write_text(
                f"test evidence: {relative}\n",
                encoding="utf-8",
            )


def create_verdict(
    path: Path,
    *,
    verdict: str = "P3_ACCEPTED",
) -> None:
    """Create a representative independent-verifier JSON document."""
    write_json(
        path,
        {
            "verdict": verdict,
            "integrity": {
                "manifest_entries": 20,
                "sha256_entries_verified": 20,
            },
            "benchmark": {
                "schema": "qflpn-benchmark-v2",
                "run_id": RUN_ID,
                "validation": "PASS",
                "records": 1,
                "dimension": 1_000_000,
            },
            "ci_stages": {
                "p3_environment": "success",
                "p3_integrity_generate": "success",
                "p3_benchmark": "success",
            },
        },
    )


def test_load_json_reads_valid_object(tmp_path: Path) -> None:
    path = tmp_path / "verdict.json"
    create_verdict(path)

    result = MODULE.load_json(path)

    assert result["verdict"] == "P3_ACCEPTED"
    assert result["integrity"]["manifest_entries"] == 20


def test_load_json_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{invalid json", encoding="utf-8")

    try:
        MODULE.load_json(path)
    except ValueError as exc:
        assert "Invalid verdict JSON" in str(exc)
    else:
        raise AssertionError("Invalid JSON was accepted")


def test_load_json_rejects_non_object_document(
    tmp_path: Path,
) -> None:
    path = tmp_path / "array.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    try:
        MODULE.load_json(path)
    except ValueError as exc:
        assert "JSON object" in str(exc)
    else:
        raise AssertionError("A JSON array was accepted")


def test_load_json_rejects_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"

    try:
        MODULE.load_json(path)
    except ValueError as exc:
        assert "Cannot read verdict JSON" in str(exc)
    else:
        raise AssertionError("A missing verdict file was accepted")


def test_evidence_status_reports_all_present_files(
    tmp_path: Path,
) -> None:
    create_evidence_tree(tmp_path)

    statuses = MODULE.evidence_status(tmp_path)

    assert len(statuses) == len(MODULE.REQUIRED_EVIDENCE)
    assert all(present for _, present, _ in statuses)
    assert all(size > 0 for _, _, size in statuses)


def test_evidence_status_reports_missing_file(
    tmp_path: Path,
) -> None:
    create_evidence_tree(tmp_path)

    missing_relative = MODULE.REQUIRED_EVIDENCE[0]
    (tmp_path / missing_relative).unlink()

    statuses = MODULE.evidence_status(tmp_path)
    status_map = {
        name: present
        for name, present, _ in statuses
    }

    assert status_map[missing_relative] is False


def test_evidence_status_does_not_accept_symlink(
    tmp_path: Path,
) -> None:
    create_evidence_tree(tmp_path)

    relative = MODULE.REQUIRED_EVIDENCE[0]
    target = tmp_path / "outside-evidence.txt"
    target.write_text("external", encoding="utf-8")

    evidence = tmp_path / relative
    evidence.unlink()
    evidence.symlink_to(target)

    statuses = MODULE.evidence_status(tmp_path)
    status_map = {
        name: present
        for name, present, _ in statuses
    }

    assert status_map[relative] is False


def test_format_ci_stages_marks_success_as_pass() -> None:
    rows = MODULE.format_ci_stages(
        {
            "p3_environment": "success",
            "p3_benchmark": "success",
        }
    )

    assert len(rows) == 2
    assert all("PASS" in row for row in rows)


def test_format_ci_stages_marks_failure() -> None:
    rows = MODULE.format_ci_stages(
        {
            "p3_benchmark": "failure",
        }
    )

    assert len(rows) == 1
    assert "FAIL" in rows[0]
    assert "failure" in rows[0]


def test_format_ci_stages_handles_empty_mapping() -> None:
    rows = MODULE.format_ci_stages({})

    assert rows
    assert "UNAVAILABLE" in rows[0]


def test_format_ci_stages_handles_non_mapping() -> None:
    rows = MODULE.format_ci_stages(None)

    assert rows
    assert "UNAVAILABLE" in rows[0]


def test_format_environment_includes_report(
    tmp_path: Path,
) -> None:
    report = tmp_path / "P3/reports/environment.txt"
    report.parent.mkdir(parents=True)
    report.write_text(
        "Python: 3.12\nJava: 21\n",
        encoding="utf-8",
    )

    lines = MODULE.format_environment(tmp_path)

    rendered = "\n".join(lines)

    assert "PRESENT" in rendered
    assert "Python: 3.12" in rendered
    assert "Java: 21" in rendered


def test_format_environment_limits_number_of_lines(
    tmp_path: Path,
) -> None:
    report = tmp_path / "P3/reports/environment.txt"
    report.parent.mkdir(parents=True)
    report.write_text(
        "\n".join(f"line-{index}" for index in range(100)),
        encoding="utf-8",
    )

    lines = MODULE.format_environment(
        tmp_path,
        maximum_lines=10,
    )

    rendered = "\n".join(lines)

    assert "line-0" in rendered
    assert "line-9" in rendered
    assert "line-10" not in rendered
    assert "90 additional lines" in rendered


def test_format_environment_reports_missing_file(
    tmp_path: Path,
) -> None:
    lines = MODULE.format_environment(tmp_path)

    assert "MISSING" in "\n".join(lines)


def test_build_summary_contains_verdict_and_run_id(
    tmp_path: Path,
) -> None:
    create_evidence_tree(tmp_path)

    verdict_path = tmp_path / "verdict.json"
    create_verdict(verdict_path)

    summary = MODULE.build_summary(
        tmp_path,
        verdict_path,
        RUN_ID,
    )

    assert "# QFLPN P3 — FINAL VALIDATION SUMMARY" in summary
    assert "**P3_ACCEPTED**" in summary
    assert RUN_ID in summary


def test_build_summary_contains_integrity_metrics(
    tmp_path: Path,
) -> None:
    create_evidence_tree(tmp_path)

    verdict_path = tmp_path / "verdict.json"
    create_verdict(verdict_path)

    summary = MODULE.build_summary(
        tmp_path,
        verdict_path,
        RUN_ID,
    )

    assert "MANIFEST entries" in summary
    assert "20" in summary
    assert "SHA-256 entries verified" in summary


def test_build_summary_contains_benchmark_information(
    tmp_path: Path,
) -> None:
    create_evidence_tree(tmp_path)

    verdict_path = tmp_path / "verdict.json"
    create_verdict(verdict_path)

    summary = MODULE.build_summary(
        tmp_path,
        verdict_path,
        RUN_ID,
    )

    assert "qflpn-benchmark-v2" in summary
    assert "1,000,000" in summary or "1000000" in summary
    assert "p3_benchmark" in summary


def test_build_summary_contains_evidence_inventory(
    tmp_path: Path,
) -> None:
    create_evidence_tree(tmp_path)

    verdict_path = tmp_path / "verdict.json"
    create_verdict(verdict_path)

    summary = MODULE.build_summary(
        tmp_path,
        verdict_path,
        RUN_ID,
    )

    for relative in MODULE.REQUIRED_EVIDENCE:
        assert relative in summary

    assert "Mandatory files present" in summary
    assert "Mandatory files missing" in summary


def test_build_summary_reports_missing_evidence(
    tmp_path: Path,
) -> None:
    create_evidence_tree(tmp_path)

    missing_relative = MODULE.REQUIRED_EVIDENCE[0]
    (tmp_path / missing_relative).unlink()

    verdict_path = tmp_path / "verdict.json"
    create_verdict(verdict_path)

    summary = MODULE.build_summary(
        tmp_path,
        verdict_path,
        RUN_ID,
    )

    assert missing_relative in summary
    assert "MISSING" in summary
    assert "P3_REJECTED / INCOMPLETE EVIDENCE" in summary


def test_build_summary_rejects_unknown_verdict(
    tmp_path: Path,
) -> None:
    create_evidence_tree(tmp_path)

    verdict_path = tmp_path / "verdict.json"
    create_verdict(verdict_path, verdict="UNKNOWN")

    summary = MODULE.build_summary(
        tmp_path,
        verdict_path,
        RUN_ID,
    )

    assert "P3_REJECTED" in summary


def test_build_summary_includes_verification_error(
    tmp_path: Path,
) -> None:
    create_evidence_tree(tmp_path)

    verdict_path = tmp_path / "verdict.json"
    write_json(
        verdict_path,
        {
            "verdict": "P3_REJECTED",
            "error": "Integrity verification failed",
        },
    )

    summary = MODULE.build_summary(
        tmp_path,
        verdict_path,
        RUN_ID,
    )

    assert "Verification error" in summary
    assert "Integrity verification failed" in summary


def test_main_writes_summary_to_explicit_output(
    tmp_path: Path,
) -> None:
    create_evidence_tree(tmp_path)

    verdict_path = tmp_path / "verdict.json"
    create_verdict(verdict_path)

    output_path = tmp_path / "reports/summary.md"

    result = MODULE.main(
        [
            "--root",
            str(tmp_path),
            "--verdict-json",
            str(verdict_path),
            "--run-id",
            RUN_ID,
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert output_path.is_file()

    content = output_path.read_text(encoding="utf-8")

    assert "QFLPN P3" in content
    assert RUN_ID in content


def test_main_returns_error_for_missing_verdict(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "summary.md"

    result = MODULE.main(
        [
            "--root",
            str(tmp_path),
            "--verdict-json",
            str(tmp_path / "missing.json"),
            "--run-id",
            RUN_ID,
            "--output",
            str(output_path),
        ]
    )

    assert result == 1
    assert not output_path.exists()
