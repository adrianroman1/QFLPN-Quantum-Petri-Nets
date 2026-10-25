from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from P3.tools import verify_evidence_consistency as verifier


RUN_ID = "p3-12345-1"
SOURCE_COMMIT = "a" * 40

CSV_RELATIVE = Path("benchmarks/benchmark_results_v2.csv")
RAW_RELATIVE = Path("results/raw") / RUN_ID

CHECKSUM_RELATIVE_PATHS = (
    CSV_RELATIVE,
    RAW_RELATIVE / "benchmark-report.json",
    RAW_RELATIVE / "benchmark-report.txt",
    RAW_RELATIVE / "benchmark-report.md",
    RAW_RELATIVE / "validation-report.json",
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_fixture(root: Path) -> None:
    """Create a complete, internally consistent P3 evidence fixture."""
    p3 = root / "P3"
    raw = p3 / RAW_RELATIVE

    raw.mkdir(parents=True)

    environment = {
        "schema": "qflpn-p3-environment-v1",
        "run_id": RUN_ID,
        "repository": {
            "commit": SOURCE_COMMIT,
            "remote_origin": (
                "https://github.com/adrianroman1/"
                "QFLPN-Quantum-Petri-Nets.git"
            ),
            "commit_dirty": False,
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

    csv_path = p3 / CSV_RELATIVE
    csv_path.parent.mkdir(parents=True, exist_ok=True)

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
    write_json(p3 / "reports" / "validation-report.json", validation)

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

    (raw / "benchmark-report.md").write_text(
        markdown,
        encoding="utf-8",
    )
    (p3 / "reports" / "benchmark-report.md").write_text(
        markdown,
        encoding="utf-8",
    )

    # Match run_benchmark.sh: paths are relative to the P3 directory,
    # and the canonical CSV is included alongside all four raw reports.
    checksum_lines = []
    for relative_path in CHECKSUM_RELATIVE_PATHS:
        target = p3 / relative_path
        checksum_lines.append(
            f"{sha256(target)}  {relative_path.as_posix()}\n"
        )

    (raw / "SHA256SUMS.txt").write_text(
        "".join(checksum_lines),
        encoding="ascii",
    )


def run_check(root: Path) -> dict:
    return verifier.verify_evidence(
        root,
        run_id=RUN_ID,
        source_commit=SOURCE_COMMIT,
    )


def test_accepts_consistent_evidence(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    result = run_check(tmp_path)

    assert result["schema"] == "qflpn-p3-evidence-consistency-v1"
    assert result["validation"] == "PASS"
    assert result["run_id"] == RUN_ID
    assert result["source_commit"] == SOURCE_COMMIT
    assert result["csv_dimension"] == 100
    assert result["csv_nnz"] == 200
    assert result["evidence"]["environment"] == "PASS"
    assert result["evidence"]["csv"] == "PASS"
    assert result["evidence"]["run_checksums"] == "PASS"
    assert len(result["verified_run_checksum_files"]) == 5


def test_rejects_invalid_run_id(tmp_path: Path) -> None:
    with pytest.raises(verifier.EvidenceError, match="RUN_ID is invalid"):
        verifier.verify_evidence(
            tmp_path,
            run_id="../invalid",
            source_commit=SOURCE_COMMIT,
        )


@pytest.mark.parametrize(
    "commit",
    [
        "a" * 39,
        "A" * 40,
        "g" * 40,
        "not-a-commit",
    ],
)
def test_rejects_invalid_source_commit(
    tmp_path: Path,
    commit: str,
) -> None:
    with pytest.raises(verifier.EvidenceError, match="SOURCE_COMMIT"):
        verifier.verify_evidence(
            tmp_path,
            run_id=RUN_ID,
            source_commit=commit,
        )


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


def test_rejects_environment_commit_mismatch(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    path = tmp_path / "P3" / "reports" / "environment.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["repository"]["commit"] = "b" * 40
    write_json(path, data)

    with pytest.raises(verifier.EvidenceError, match="Environment commit"):
        run_check(tmp_path)


def test_rejects_missing_environment_file(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    (tmp_path / "P3" / "reports" / "environment.json").unlink()

    with pytest.raises(verifier.EvidenceError, match="Environment JSON"):
        run_check(tmp_path)


def test_rejects_csv_json_metric_mismatch(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    path = (
        tmp_path / "P3" / RAW_RELATIVE / "validation-report.json"
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    data["latest_record"]["speedup"] = 3.0
    write_json(path, data)

    with pytest.raises(verifier.EvidenceError, match="speedup mismatch"):
        run_check(tmp_path)


def test_rejects_csv_dimension_mismatch(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    path = tmp_path / "P3" / CSV_RELATIVE
    rows = list(csv.DictReader(path.open(encoding="utf-8")))

    rows[0]["dimension"] = "101"

    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(verifier.EvidenceError):
        run_check(tmp_path)


def test_rejects_wrong_csv_nnz(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    path = tmp_path / "P3" / CSV_RELATIVE
    rows = list(csv.DictReader(path.open(encoding="utf-8")))

    rows[0]["non_zero_count"] = "199"

    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(verifier.EvidenceError, match="non_zero_count"):
        run_check(tmp_path)


def test_rejects_java_report_run_id_mismatch(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    path = tmp_path / "P3" / RAW_RELATIVE / "benchmark-report.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["run_id"] = "p3-wrong-run"
    write_json(path, data)

    with pytest.raises(verifier.EvidenceError, match="Java JSON RUN_ID"):
        run_check(tmp_path)


def test_rejects_java_report_non_pass(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    path = tmp_path / "P3" / RAW_RELATIVE / "benchmark-report.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["validation"] = "FAIL"
    write_json(path, data)

    with pytest.raises(verifier.EvidenceError, match="validation is not PASS"):
        run_check(tmp_path)


def test_rejects_markdown_without_pass_marker(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    path = tmp_path / "P3" / RAW_RELATIVE / "benchmark-report.md"
    path.write_text(
        f"Run ID: {RUN_ID}\nValidation: FAIL\n",
        encoding="utf-8",
    )

    with pytest.raises(verifier.EvidenceError, match="Markdown"):
        run_check(tmp_path)


def test_rejects_persistent_markdown_for_another_run(
    tmp_path: Path,
) -> None:
    make_fixture(tmp_path)

    path = tmp_path / "P3" / "reports" / "benchmark-report.md"
    path.write_text(
        "Validation: **PASS**\nRun ID: `p3-old-run`\n",
        encoding="utf-8",
    )

    with pytest.raises(verifier.EvidenceError, match="Persistent Markdown"):
        run_check(tmp_path)


def test_rejects_persistent_validation_for_another_run(
    tmp_path: Path,
) -> None:
    make_fixture(tmp_path)

    path = tmp_path / "P3" / "reports" / "validation-report.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["latest_record"]["run_id"] = "p3-old-run"
    write_json(path, data)

    with pytest.raises(verifier.EvidenceError, match="Persistent validation JSON RUN_ID"):
        run_check(tmp_path)


def test_rejects_duplicate_csv_run_id(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    path = tmp_path / "P3" / CSV_RELATIVE
    with path.open("r", encoding="utf-8") as stream:
        content = stream.read()

    header, row = content.splitlines()
    path.write_text(
        f"{header}\n{row}\n{row}\n",
        encoding="utf-8",
    )

    with pytest.raises(verifier.EvidenceError, match="exactly one CSV row"):
        run_check(tmp_path)


def test_rejects_missing_raw_checksum_entry(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    checksum = tmp_path / "P3" / RAW_RELATIVE / "SHA256SUMS.txt"
    lines = checksum.read_text(encoding="ascii").splitlines()
    checksum.write_text("\n".join(lines[:-1]) + "\n", encoding="ascii")

    with pytest.raises(verifier.EvidenceError, match="exactly the five runner"):
        run_check(tmp_path)


def test_rejects_tampered_run_checksum_target(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    path = tmp_path / "P3" / RAW_RELATIVE / "benchmark-report.txt"
    path.write_text(
        f"RUN_ID={RUN_ID}\nTampered\n",
        encoding="utf-8",
    )

    with pytest.raises(verifier.EvidenceError, match="SHA-256 mismatch"):
        run_check(tmp_path)


def test_rejects_checksum_path_traversal(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    checksum = tmp_path / "P3" / RAW_RELATIVE / "SHA256SUMS.txt"
    lines = checksum.read_text(encoding="ascii").splitlines()

    digest = lines[0].split("  ", 1)[0]
    lines[0] = f"{digest}  ../outside.csv"
    checksum.write_text("\n".join(lines) + "\n", encoding="ascii")

    with pytest.raises(verifier.EvidenceError):
        run_check(tmp_path)


def test_rejects_symlinked_checksum_target(tmp_path: Path) -> None:
    make_fixture(tmp_path)

    p3 = tmp_path / "P3"
    target = p3 / RAW_RELATIVE / "benchmark-report.txt"
    original = target.read_text(encoding="utf-8")

    target.unlink()
    outside = tmp_path / "outside.txt"
    outside.write_text(original, encoding="utf-8")
    target.symlink_to(outside)

    with pytest.raises(verifier.EvidenceError, match="Symlink"):
        run_check(tmp_path)


def test_atomic_write_json_creates_valid_report(tmp_path: Path) -> None:
    output = tmp_path / "P3" / "reports" / "evidence-consistency.json"
    payload = {
        "schema": "qflpn-p3-evidence-consistency-v1",
        "validation": "PASS",
        "run_id": RUN_ID,
    }

    verifier.atomic_write_json(output, payload)

    assert output.is_file()
    assert json.loads(output.read_text(encoding="utf-8")) == payload


def test_atomic_write_json_refuses_symlink(tmp_path: Path) -> None:
    destination = tmp_path / "evidence.json"
    destination.write_text("{}", encoding="utf-8")

    link = tmp_path / "linked-evidence.json"
    link.symlink_to(destination)

    with pytest.raises(verifier.EvidenceError, match="symlink"):
        verifier.atomic_write_json(link, {"validation": "PASS"})
