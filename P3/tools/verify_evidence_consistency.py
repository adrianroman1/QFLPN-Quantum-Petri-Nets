#!/usr/bin/env python3
"""Fail-closed cross-validation of P3 V2 and V3 benchmark evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

V2_REQUIRED = {
    "timestamp", "run_id", "dimension", "non_zero_count",
    "warmup_iterations", "measured_iterations",
    "sequential_mean_ms", "parallel_mean_ms", "speedup",
    "max_absolute_error",
}

V3_REQUIRED = {
    "timestamp", "run_id", "workflow_run_id", "commit_sha",
    "benchmark_id", "workload_id", "matrix_family", "distribution",
    "dimension", "non_zero_count", "nnz_min_per_row",
    "nnz_avg_per_row", "nnz_max_per_row", "parallelism",
    "threshold_rows", "parallel_strategy", "split_policy",
    "warmup_iterations", "measured_iterations",
    "sequential_mean_ms", "sequential_median_ms",
    "sequential_stddev_ms", "sequential_min_ms",
    "sequential_max_ms", "parallel_mean_ms", "parallel_median_ms",
    "parallel_stddev_ms", "parallel_min_ms", "parallel_max_ms",
    "speedup", "sequential_rows_per_second",
    "parallel_rows_per_second", "sequential_nnz_per_second",
    "parallel_nnz_per_second", "sequential_expected_error",
    "parallel_expected_error", "max_absolute_error",
    "setup_time_ms", "cpu", "max_jvm_memory_bytes",
    "free_jvm_heap_bytes", "java_version", "operating_system",
    "status", "verdict", "notes",
}

V2_RUN_CHECKSUMS = {
    "benchmarks/benchmark_results_v2.csv",
    "results/raw/{run_id}/benchmark-report.json",
    "results/raw/{run_id}/benchmark-report.txt",
    "results/raw/{run_id}/benchmark-report.md",
    "results/raw/{run_id}/validation-report.json",
}

V3_RUN_CHECKSUMS = {
    "benchmarks/benchmark_results_v3.csv",
}

class EvidenceError(RuntimeError):
    """Raised when P3 evidence is missing, inconsistent, or unsafe."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def regular_file(path: Path, label: str) -> None:
    require(not path.is_symlink(), f"Symlink detected for {label}: {path}")
    require(path.is_file(), f"{label} is missing: {path}")


def read_json(path: Path, label: str) -> dict[str, Any]:
    regular_file(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{label} is invalid JSON: {exc}") from exc
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def finite(value: Any, label: str) -> float:
    require(not isinstance(value, bool), f"{label} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvidenceError(f"{label} must be numeric") from exc
    require(math.isfinite(result), f"{label} must be finite")
    return result


def same_number(left: Any, right: Any, label: str) -> None:
    a = finite(left, label)
    b = finite(right, label)
    require(
        math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-12),
        f"{label} mismatch: {a} != {b}",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_target(p3_root: Path, name: str) -> Path:
    require(bool(name), "Empty checksum path")
    require("\\" not in name, f"Backslash in checksum path: {name}")
    relative = PurePosixPath(name)
    require(not relative.is_absolute(), f"Absolute checksum path: {name}")
    require(
        all(part not in {"", ".", ".."} for part in relative.parts),
        f"Unsafe checksum path: {name}",
    )

    root = p3_root.resolve()
    target = p3_root.joinpath(*relative.parts)
    resolved = target.resolve()
    require(
        resolved != root and root in resolved.parents,
        f"Checksum path escapes P3 root: {name}",
    )

    current = p3_root
    for part in relative.parts:
        current = current / part
        require(not current.is_symlink(), f"Symlink in checksum path: {name}")

    regular_file(target, f"Checksum target {name}")
    return target


def verify_checksums(
    p3_root: Path,
    checksum_file: Path,
    expected_paths: set[str],
) -> list[str]:
    regular_file(checksum_file, "Run-specific SHA256SUMS.txt")
    try:
        lines = checksum_file.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as exc:
        raise EvidenceError(f"Cannot read run checksums: {exc}") from exc

    parsed: dict[str, str] = {}
    for number, line in enumerate(lines, start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        require(match is not None, f"Malformed checksum line {number}")
        assert match is not None
        digest, name = match.groups()
        require(name not in parsed, f"Duplicate checksum entry: {name}")
        parsed[name] = digest

    require(
        set(parsed) == expected_paths,
        "Run checksum path set mismatch; "
        f"missing={sorted(expected_paths - set(parsed))}; "
        f"unexpected={sorted(set(parsed) - expected_paths)}",
    )

    for name, expected in parsed.items():
        actual = sha256_file(safe_target(p3_root, name))
        require(actual == expected, f"SHA-256 mismatch: {name}")

    return sorted(parsed)


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    regular_file(path, "Canonical benchmark CSV")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            require(reader.fieldnames is not None, "CSV header is missing")
            missing = required - set(reader.fieldnames)
            require(not missing, f"CSV missing columns: {sorted(missing)}")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise EvidenceError(f"Cannot read benchmark CSV: {exc}") from exc

    require(bool(rows), f"CSV contains no records: {path}")
    return rows


def verify_v2(root: Path, run_id: str) -> dict[str, Any]:
    p3 = root / "P3"
    raw = p3 / "results" / "raw" / run_id
    csv_path = p3 / "benchmarks" / "benchmark_results_v2.csv"
    rows = read_csv(csv_path, V2_REQUIRED)
    matches = [row for row in rows if row.get("run_id") == run_id]
    require(len(matches) == 1, f"V2 expected one row for {run_id}; got {len(matches)}")
    row = matches[0]

    report = read_json(raw / "validation-report.json", "V2 validation report")
    require(report.get("schema") == "qflpn-benchmark-v2", "V2 schema mismatch")
    require(report.get("validation") == "PASS", "V2 validation is not PASS")
    require(report.get("all_records_valid") is True, "V2 records are not all valid")

    latest = report.get("latest_record")
    require(isinstance(latest, dict), "V2 latest_record missing")
    require(latest.get("run_id") == run_id, "V2 report RUN_ID mismatch")

    for csv_key, json_key in (
        ("dimension", "dimension"),
        ("non_zero_count", "nnz"),
        ("speedup", "speedup"),
        ("sequential_mean_ms", "sequential_mean_ms"),
        ("parallel_mean_ms", "parallel_mean_ms"),
        ("max_absolute_error", "max_error"),
    ):
        if csv_key in {"dimension", "non_zero_count"}:
            require(
                int(row[csv_key]) == int(latest.get(json_key, -1)),
                f"V2 CSV/report mismatch: {csv_key}",
            )
        else:
            same_number(latest.get(json_key), row[csv_key], f"V2 {csv_key}")

    java_report = read_json(raw / "benchmark-report.json", "V2 Java report")
    require(java_report.get("run_id") == run_id, "V2 Java report RUN_ID mismatch")
    require(java_report.get("validation") == "PASS", "V2 Java report is not PASS")

    text_path = raw / "benchmark-report.txt"
    regular_file(text_path, "V2 Java text report")
    require(f"RUN_ID={run_id}" in text_path.read_text(encoding="utf-8"),
            "V2 Java text report RUN_ID mismatch")

    markdown_path = raw / "benchmark-report.md"
    regular_file(markdown_path, "V2 run Markdown")
    markdown = markdown_path.read_text(encoding="utf-8")
    require(run_id in markdown, "V2 run Markdown RUN_ID mismatch")
    require("Validation: **PASS**" in markdown, "V2 run Markdown is not PASS")

    persistent_md = p3 / "reports" / "benchmark-report.md"
    regular_file(persistent_md, "V2 persistent Markdown")
    persistent_content = persistent_md.read_text(encoding="utf-8")
    require(run_id in persistent_content, "V2 persistent Markdown RUN_ID mismatch")
    require("Validation: **PASS**" in persistent_content,
            "V2 persistent Markdown is not PASS")

    persistent_json = read_json(
        p3 / "reports" / "validation-report.json",
        "V2 persistent validation JSON",
    )
    require(persistent_json.get("validation") == "PASS",
            "V2 persistent validation is not PASS")

    checksums = verify_checksums(
        p3,
        raw / "SHA256SUMS.txt",
        {item.format(run_id=run_id) for item in V2_RUN_CHECKSUMS},
    )

    return {
        "validation": "PASS",
        "schema": "qflpn-benchmark-v2",
        "run_id": run_id,
        "dimension": int(row["dimension"]),
        "nnz": int(row["non_zero_count"]),
        "verified_checksums": checksums,
    }


def verify_v3(
    root: Path,
    run_id: str,
    source_commit: str,
    workflow_run_id: str | None,
) -> dict[str, Any]:
    p3 = root / "P3"
    csv_path = p3 / "benchmarks" / "benchmark_results_v3.csv"
    rows = read_csv(csv_path, V3_REQUIRED)
    matches = [row for row in rows if row.get("run_id") == run_id]
    require(bool(matches), f"V3 has no rows for RUN_ID={run_id}")

    commits = {row["commit_sha"] for row in matches}
    workflows = {row["workflow_run_id"] for row in matches}
    require(commits == {source_commit}, "V3 CSV source commit mismatch")
    if workflow_run_id is not None:
        require(workflows == {str(workflow_run_id)}, "V3 workflow run ID mismatch")

    validator_path = p3 / "results" / "validate_benchmark_v3.py"
    regular_file(validator_path, "V3 authoritative validator")

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "p3_authoritative_v3_validator", validator_path
    )
    require(spec is not None and spec.loader is not None,
            "Cannot load V3 authoritative validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    try:
        result = module.validate(
            csv_path,
            run_id=run_id,
            workflow_run_id=workflow_run_id,
            commit_sha=source_commit,
        )
    except Exception as exc:
        raise EvidenceError(f"Authoritative V3 validation failed: {exc}") from exc

    require(
        result.get("schema") == "qflpn-benchmark-v3-validation-v2",
        "V3 validator returned unexpected schema",
    )
    require(result.get("validation") == "PASS", "V3 validator did not PASS")
    require(result.get("all_records_valid") is True, "V3 records are not all valid")
    require(result.get("configuration_matrix_complete") is True,
            "V3 configuration matrix is incomplete")
    require(result.get("run_id") == run_id, "V3 validator RUN_ID mismatch")
    require(result.get("run_contract") in {"LEGACY_96", "AB_192"},
            "Unsupported V3 run contract")

    report_path = p3 / "reports" / "benchmark-v3-validation.json"
    report = read_json(report_path, "Persistent V3 validation report")
    require(report.get("schema") == result["schema"], "V3 report schema mismatch")
    require(report.get("validation") == "PASS", "Persistent V3 report is not PASS")
    require(report.get("run_id") == run_id, "Persistent V3 report RUN_ID mismatch")
    require(report.get("commit_sha") == source_commit,
            "Persistent V3 report commit mismatch")
    require(report.get("validated_records") == result.get("validated_records"),
            "Persistent V3 report record count mismatch")
    require(report.get("run_contract") == result.get("run_contract"),
            "Persistent V3 report contract mismatch")

    checksum_path = p3 / "reports" / "benchmark-v3-SHA256SUMS.txt"
    verified = verify_checksums(
        p3,
        checksum_path,
        V3_RUN_CHECKSUMS,
    )

    return {
        "validation": "PASS",
        "schema": result["schema"],
        "run_id": run_id,
        "run_contract": result["run_contract"],
        "validated_records": result["validated_records"],
        "verified_checksums": verified,
    }


def verify_evidence(
    root: Path,
    *,
    run_id: str,
    source_commit: str,
    workflow_run_id: str | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    require(RUN_ID_RE.fullmatch(run_id or "") is not None, "RUN_ID is invalid")
    require(COMMIT_RE.fullmatch(source_commit or "") is not None,
            "SOURCE_COMMIT must be a full lowercase Git SHA")

    p3 = root / "P3"
    environment = read_json(
        p3 / "reports" / "environment.json",
        "Environment JSON",
    )
    require(environment.get("schema") == "qflpn-p3-environment-v1",
            "Environment schema mismatch")
    require(environment.get("run_id") == run_id, "Environment RUN_ID mismatch")
    repository = environment.get("repository")
    require(isinstance(repository, dict), "Environment repository missing")
    require(repository.get("commit") == source_commit,
            "Environment commit mismatch")

    v2 = verify_v2(root, run_id)
    v3 = verify_v3(root, run_id, source_commit, workflow_run_id)

    return {
        "schema": "qflpn-p3-evidence-consistency-v2",
        "validation": "PASS",
        "run_id": run_id,
        "source_commit": source_commit,
        "workflow_run_id": workflow_run_id,
        "evidence": {
            "environment": "PASS",
            "benchmark_v2": "PASS",
            "benchmark_v3": "PASS",
            "v3_authoritative_validator": "PASS",
            "v3_persistent_report": "PASS",
            "v3_checksums": "PASS",
        },
        "benchmark_v2": v2,
        "benchmark_v3": v3,
    }


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    require(not path.is_symlink(), f"Output must not be a symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n",
            dir=path.parent, prefix=f".{path.name}.",
            suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cross-validate P3 V2 and V3 evidence for one RUN_ID."
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--run-id", default=os.environ.get("RUN_ID"))
    parser.add_argument("--source-commit", default=os.environ.get("SOURCE_COMMIT"))
    parser.add_argument("--workflow-run-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("P3/reports/evidence-consistency.json"),
    )
    args = parser.parse_args()

    try:
        require(args.run_id, "--run-id or RUN_ID is required")
        require(args.source_commit, "--source-commit or SOURCE_COMMIT is required")
        result = verify_evidence(
            args.root,
            run_id=args.run_id,
            source_commit=args.source_commit,
            workflow_run_id=args.workflow_run_id,
        )
        atomic_write_json(args.json_output, result)
        print("P3_EVIDENCE_CONSISTENCY: PASS")
        print(f"P3_EVIDENCE_RUN_ID={args.run_id}")
        print(f"P3_EVIDENCE_SOURCE_COMMIT={args.source_commit}")
        print(f"P3_EVIDENCE_REPORT={args.json_output}")
        return 0
    except (EvidenceError, OSError, ValueError, TypeError, KeyError) as exc:
        print(
            f"P3_EVIDENCE_CONSISTENCY: FAIL: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
