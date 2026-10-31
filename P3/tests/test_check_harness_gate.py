#!/usr/bin/env python3
"""Contract tests for P3/tools/check_harness_gate.py."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "P3" / "tools" / "check_harness_gate.py"

SPEC = importlib.util.spec_from_file_location("qflpn_check_harness_gate", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

ALL_IDS = MODULE.MANDATORY + MODULE.INFORMATIONAL


def write_sums(run: Path) -> None:
    lines = []
    for path in sorted(run.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.name}")
    (run / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", "utf-8")


def make_run(tmp_path: Path, statuses: dict[str, str] | None = None) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    status = {c: "PASS" for c in ALL_IDS}
    status.update(statuses or {})

    for name in MODULE.REQUIRED_FILES:
        if name not in ("SHA256SUMS.txt", "harness_verdict.json"):
            (run / name).write_text(f"content of {name}\n", "utf-8")

    (run / "harness_verdict.json").write_text(json.dumps({
        "overall": "PASS",
        "criteria": [{"id": k, "status": v, "detail": ""}
                     for k, v in status.items()],
    }), "utf-8")
    write_sums(run)
    return run


def test_healthy_run_passes(tmp_path: Path) -> None:
    ok, errors, warnings = MODULE.gate(make_run(tmp_path))
    assert ok and not errors and not warnings
    assert MODULE.main([str(tmp_path / "run")]) == 0


def test_each_mandatory_criterion_blocks(tmp_path: Path) -> None:
    for index, criterion in enumerate(MODULE.MANDATORY):
        case = tmp_path / f"case{index}"
        case.mkdir()
        run = make_run(case, {criterion: "FAIL"})
        assert MODULE.main([str(run)]) == 1, criterion


def test_not_evaluated_does_not_satisfy_a_mandatory_criterion(
        tmp_path: Path) -> None:
    run = make_run(tmp_path, {"C8_DECLARED_CONFIGURATIONS_COMPLETE":
                              "NOT_EVALUATED"})
    assert MODULE.main([str(run)]) == 1


def test_performance_failures_only_warn(tmp_path: Path) -> None:
    run = make_run(tmp_path, {
        "C3_OVERHEAD_AT_P1_AT_MOST_5_PERCENT": "FAIL",
        "C5_NO_SIGNIFICANT_REGRESSION_AT_N_GE_1M": "FAIL",
        "C4_SPEEDUP_GT_1_AT_P2_N_GE_10M": "NOT_EVALUATED"})
    ok, errors, warnings = MODULE.gate(run)
    assert ok and not errors
    assert len(warnings) == 2


def test_build_failure_marker_blocks(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    (run / "BUILD_FAILED.txt").write_text("BUILD_FAILED\n", "utf-8")
    write_sums(run)
    assert MODULE.main([str(run)]) == 1


def test_modified_artifact_is_detected(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    (run / "harness_summary.csv").write_text("tampered\n", "utf-8")
    ok, errors, _ = MODULE.gate(run)
    assert not ok
    assert any("SHA-256 mismatch" in e for e in errors)


def test_uncovered_and_missing_files_are_detected(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    (run / "extra.txt").write_text("not in the sums\n", "utf-8")
    ok, errors, _ = MODULE.gate(run)
    assert not ok
    assert any("not covered" in e for e in errors)

    (run / "extra.txt").unlink()
    (run / "harness_report.md").unlink()
    ok, errors, _ = MODULE.gate(run)
    assert not ok
    assert any("missing" in e for e in errors)


def test_missing_checksum_file_and_directory(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    (run / "SHA256SUMS.txt").unlink()
    assert MODULE.main([str(run)]) == 1
    assert MODULE.main([str(tmp_path / "does-not-exist")]) == 1
    assert MODULE.main([]) == 2


def test_malformed_and_duplicate_checksum_lines(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    sums = (run / "SHA256SUMS.txt")
    sums.write_text("garbage\n" + sums.read_text("utf-8"), "utf-8")
    ok, errors, _ = MODULE.gate(run)
    assert not ok and any("malformed" in e for e in errors)

    write_sums(run)
    first = (run / "SHA256SUMS.txt").read_text("utf-8").splitlines()[0]
    (run / "SHA256SUMS.txt").write_text(
        (run / "SHA256SUMS.txt").read_text("utf-8") + first + "\n", "utf-8")
    ok, errors, _ = MODULE.gate(run)
    assert not ok and any("duplicate" in e for e in errors)
