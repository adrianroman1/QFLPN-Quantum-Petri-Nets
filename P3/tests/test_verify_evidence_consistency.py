from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from P3.tools import verify_evidence_consistency as verifier


RUN_ID = "p3-12345-1"
SOURCE_COMMIT = "a" * 40


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def make_fixture(root: Path) -> None:
    p3 = root / "P3"
    raw = p3 / "results" / "raw" / RUN_ID
    raw.mkdir(parents=True)

    environment = {
        "schema": "qflpn-p3-environment-v1",
        "run_id": RUN_ID,
        "repository": {
            "commit": SOURCE_COMMIT,
            "remote_origin": "https://github.com/example/repo.git",
        },
        "benchmark": {
            "dimension": 100,
            "warmup_iterations": 2,
            "measured_iterations": 5,
            "threshold": 4096,
            "parallelism": 2,
        },
    }
    write_json(p3 / "reports" / "environment.json", environment)

    row = {
        "timestamp": "2026-10-25T12:00:00+00:00",
        "run_id": RUN_ID,
        "dimension": "100",
        "non_zero_count": "200",
        "warmup_iterations": "2",
        "measured_iterations": "5",
        "sequential_mean_ms": "10.0",
        "parallel_mean_ms": "5.0",
        "speedup": "2.0",
        "max_absolute_error": "0.0",
    }
    csv_path = p3 / "benchmarks" / "benchmark_results_v2.csv"
    csv_path.parent.mkdir(parents=True)
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)

    validation = {
        "schema": "qflpn-benchmark-v2",
        "validation": "PASS",
        "records": 1,
        "all_records_valid": True,
        "latest_record": {
            "row": 1,
            "run_id": RUN_ID,
            "dimension": 100,
            "nnz": 200,
            "speedup": 2.0,
            "sequential_mean_ms": 10.0,
            "parallel_mean_ms": 5.0,
            "max_error": 0.0,
        },
    }
    write_json(raw / "validation-report.json", validation)
    write_json(
        p3 / "reports" / "validation-report.json",
        validation,
    )

    java_report = {
        "run_id": RUN_ID,
        "validation": "PASS",
        "speedup": 2.0,
        "sequential_mean_ms": 10.0,
        "parallel_mean_ms": 5.0,
    }
    write_json(raw / "benchmark-report.json", java_report)

    (raw / "benchmark-report.txt").write_text(
        f"RUN_ID={RUN_ID}\nValidation=PASS\n",
        encoding="utf-8",
    )
    markdown = (
        "## QFLPN P3 benchmark summary\n\n"
        "- Validation: **PASS**\n"
        f"- Run ID: `{RUN_ID}`\n"
    )
    (raw / "benchmark-report.md").write_text(markdown, encoding="utf-8")
    (p3 / "reports" / "benchmark-report.md").write_text(
        markdown,
        encoding="utf-8",
    )

    checksum_names = [
        "benchmark-report.json",
        "benchmark-report.txt",
        "benchmark-report.md",
        "validation-report.json",
    ]
    lines = []
    for name in checksum_names:
        digest = hashlib.sha256((raw / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}\n")
    (raw / "SHA256SUMS.txt").write_text("".join(lines), encoding="ascii")


def run_check(root: Path) -> dict:
    return verifier.verify_evidence(
        root,
        run_id=RUN_ID,
        source_commit=SOURCE_COMMIT,
    )


def test_accepts_consistent_evidence(tmp_path: Path) -> None:
    make_fixture(tmp_path)
    result = run_check(tmp_path)

    assert result["validation"] == "PASS"
    assert result["run_id"] == RUN_ID
    assert result["source_commit"] == SOURCE_COMMIT
    assert result["csv_dimension"] == 100
    assert result["csv_nnz"] == 200


def test_rejects_wrong_source_commit(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    with pytest.raises(verifier.EvidenceError, match="SOURCE_COMMIT"):
        verifier.verify_evidence(
            tmp_path,
            run_id=RUN_ID,
            source_commit="b" * 40,
        )


def test_rejects_environment_run_id_mismatch(tmp_path: Path) -> None:
    make_fixture(tmp_path)
    path = tmp_path / "P3" / "reports" / "environment.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["run_id"] = "p3-wrong-run"
    write_json(path, data)

    with pytest.raises(verifier.EvidenceError, match="Environment RUN_ID"):
        run_check(tmp_path)


def test_rejects_csv_json_metric_mismatch(tmp_path: Path) -> None:
    make_fixture(tmp_path)
    path = tmp_path / "P3" / "results" / "raw" / RUN_ID / "validation-report.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["latest_record"]["speedup"] = 3.0
    write_json(path, data)

    with pytest.raises(verifier.EvidenceError, match="speedup mismatch"):
        run_check(tmp_path)


def test_rejects_java_report_run_id_mismatch(tmp_path: Path) -> None:
    make_fixture(tmp_path)
    path = tmp_path / "P3" / "results" / "raw" / RUN_ID / "benchmark-report.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["run_id"] = "p3-wrong-run"
    write_json(path, data)

    with pytest.raises(verifier.EvidenceError, match="Java JSON RUN_ID"):
        run_check(tmp_path)


def test_rejects_markdown_without_pass_marker(tmp_path: Path) -> None:
    make_fixture(tmp_path)
    path = tmp_path / "P3" / "results" / "raw" / RUN_ID / "benchmark-report.md"
    path.write_text(f"Run ID: {RUN_ID}\nValidation: FAIL\n", encoding="utf-8")

    with pytest.raises(verifier.EvidenceError, match="Markdown"):
        run_check(tmp_path)


def test_rejects_tampered_run_checksum(tmp_path: Path) -> None:
    make_fixture(tmp_path)
    path = tmp_path / "P3" / "results" / "raw" / RUN_ID / "benchmark-report.txt"
    path.write_text(f"RUN_ID={RUN_ID}\nTampered\n", encoding="utf-8")

    with pytest.raises(verifier.EvidenceError, match="SHA-256 mismatch"):
        run_check(tmp_path)


def test_rejects_duplicate_csv_run_id(tmp_path: Path) -> None:
    make_fixture(tmp_path)
    path = tmp_path / "P3" / "benchmarks" / "benchmark_results_v2.csv"

    with path.open("r", encoding="utf-8") as stream:
        content = stream.read()

    header, row = content.splitlines()
    path.write_text(f"{header}\n{row}\n{row}\n", encoding="utf-8")

    with pytest.raises(verifier.EvidenceError, match="exactly one CSV row"):
        run_check(tmp_path)
