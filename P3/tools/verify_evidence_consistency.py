#!/usr/bin/env python3
"""Cross-validate all P3 benchmark evidence belonging to one RUN_ID."""

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
from pathlib import Path
from typing import Any

RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

CSV_REQUIRED = {
    "timestamp", "run_id", "dimension", "non_zero_count",
    "warmup_iterations", "measured_iterations",
    "sequential_mean_ms", "parallel_mean_ms", "speedup",
    "max_absolute_error",
}

RAW_CHECKSUM_FILES = {
    "benchmark-report.json",
    "benchmark-report.txt",
    "benchmark-report.md",
    "validation-report.json",
}


class EvidenceError(RuntimeError):
    """Raised when P3 evidence is missing, inconsistent, or unsafe."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def regular_file(path: Path, label: str) -> None:
    require(not path.is_symlink(), f"{label} must not be a symlink: {path}")
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


def same_number(
    left: Any,
    right: Any,
    label: str,
    *,
    rel_tol: float = 1e-8,
    abs_tol: float = 1e-12,
) -> None:
    a = finite(left, label)
    b = finite(right, label)
    require(
        math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol),
        f"{label} mismatch: {a} != {b}",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_run_checksums(run_dir: Path) -> list[str]:
    checksum_path = run_dir / "SHA256SUMS.txt"
    regular_file(checksum_path, "run-specific SHA256SUMS.txt")

    try:
        lines = checksum_path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as exc:
        raise EvidenceError(f"Cannot read run checksums: {exc}") from exc

    parsed: dict[str, str] = {}
    for number, line in enumerate(lines, start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        require(match is not None, f"Malformed run checksum line {number}")
        assert match is not None
        digest, name = match.groups()
        require(name not in parsed, f"Duplicate run checksum entry: {name}")
        parsed[name] = digest

    require(
        set(parsed) == RAW_CHECKSUM_FILES,
        "Run SHA256SUMS.txt must cover exactly the four run-specific reports",
    )

    for name, expected_digest in parsed.items():
        target = run_dir / name
        regular_file(target, f"Run evidence {name}")
        require(
            sha256_file(target) == expected_digest,
            f"Run-specific SHA-256 mismatch: {name}",
        )

    return sorted(parsed)


def load_csv_row(csv_path: Path, run_id: str) -> dict[str, str]:
    regular_file(csv_path, "Canonical benchmark CSV")

    try:
        with csv_path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as stream:
            reader = csv.DictReader(stream, strict=True)
            require(reader.fieldnames is not None, "CSV header is missing")
            missing = CSV_REQUIRED - set(reader.fieldnames)
            require(
                not missing,
                "CSV is missing required columns: " + ", ".join(sorted(missing)),
            )
            matches = [row for row in reader if row.get("run_id") == run_id]
    except (OSError, UnicodeError, csv.Error) as exc:
        raise EvidenceError(f"Cannot read benchmark CSV: {exc}") from exc

    require(
        len(matches) == 1,
        f"Expected exactly one CSV row for RUN_ID={run_id}; found {len(matches)}",
    )
    return matches[0]


def verify_evidence(
    root: Path,
    *,
    run_id: str,
    source_commit: str,
) -> dict[str, Any]:
    root = Path(root).resolve()

    require(
        isinstance(run_id, str) and RUN_ID_RE.fullmatch(run_id) is not None,
        "RUN_ID is invalid",
    )
    require(
        isinstance(source_commit, str)
        and COMMIT_RE.fullmatch(source_commit) is not None,
        "SOURCE_COMMIT must be a full 40-character lowercase Git SHA",
    )

    p3 = root / "P3"
    raw = p3 / "results" / "raw" / run_id

    environment = read_json(
        p3 / "reports" / "environment.json",
        "Environment JSON",
    )
    require(
        environment.get("schema") == "qflpn-p3-environment-v1",
        "Unsupported environment schema",
    )
    require(
        environment.get("run_id") == run_id,
        "Environment RUN_ID mismatch",
    )

    repository = environment.get("repository")
    require(isinstance(repository, dict), "Environment repository section missing")
    require(
        repository.get("commit") == source_commit,
        "Environment commit does not match SOURCE_COMMIT",
    )

    benchmark_config = environment.get("benchmark")
    require(
        isinstance(benchmark_config, dict),
        "Environment benchmark configuration missing",
    )

    csv_path = p3 / "benchmarks" / "benchmark_results_v2.csv"
    row = load_csv_row(csv_path, run_id)

    validation = read_json(
        raw / "validation-report.json",
        "Run validation JSON",
    )
    require(
        validation.get("schema") == "qflpn-benchmark-v2",
        "Validation JSON schema mismatch",
    )
    require(validation.get("validation") == "PASS", "CSV validation is not PASS")
    require(
        validation.get("all_records_valid") is True,
        "Validation JSON does not confirm all records valid",
    )

    latest = validation.get("latest_record")
    require(isinstance(latest, dict), "Validation JSON latest_record is missing")
    require(latest.get("run_id") == run_id, "Validation JSON RUN_ID mismatch")

    expected_config = {
        "dimension": "dimension",
        "warmup_iterations": "warmup_iterations",
        "measured_iterations": "measured_iterations",
    }
    for env_key, csv_key in expected_config.items():
        require(
            int(row[csv_key]) == int(benchmark_config[env_key]),
            f"Environment/CSV mismatch for {env_key}",
        )

    require(
        int(row["non_zero_count"]) == 2 * int(row["dimension"]),
        "CSV non_zero_count does not equal 2 * dimension",
    )
    require(
        int(latest.get("dimension", -1)) == int(row["dimension"]),
        "CSV/validation JSON dimension mismatch",
    )
    require(
        int(latest.get("nnz", -1)) == int(row["non_zero_count"]),
        "CSV/validation JSON NNZ mismatch",
    )

    metric_pairs = {
        "speedup": "speedup",
        "sequential_mean_ms": "sequential_mean_ms",
        "parallel_mean_ms": "parallel_mean_ms",
        "max_error": "max_absolute_error",
    }
    for json_key, csv_key in metric_pairs.items():
        same_number(
            latest.get(json_key),
            row[csv_key],
            f"CSV/validation JSON {csv_key}",
        )

    java_report = read_json(
        raw / "benchmark-report.json",
        "Java benchmark JSON",
    )
    require(java_report.get("run_id") == run_id, "Java JSON RUN_ID mismatch")
    require(
        java_report.get("validation") == "PASS",
        "Java benchmark JSON validation is not PASS",
    )

    # Cross-check numerical values when present in the Java JSON report.
    java_metric_pairs = {
        "speedup": "speedup",
        "sequential_mean_ms": "sequential_mean_ms",
        "parallel_mean_ms": "parallel_mean_ms",
    }
    for java_key, csv_key in java_metric_pairs.items():
        if java_key in java_report:
            same_number(
                java_report[java_key],
                row[csv_key],
                f"Java JSON {java_key}",
            )

    text_path = raw / "benchmark-report.txt"
    regular_file(text_path, "Java benchmark TXT")
    text_content = text_path.read_text(encoding="utf-8")
    require(
        f"RUN_ID={run_id}" in text_content,
        "Java benchmark TXT does not identify the current RUN_ID",
    )

    markdown_path = raw / "benchmark-report.md"
    regular_file(markdown_path, "Run benchmark Markdown")
    markdown = markdown_path.read_text(encoding="utf-8")
    require(run_id in markdown, "Run Markdown does not identify the current RUN_ID")
    require(
        "Validation: **PASS**" in markdown,
        "Run Markdown does not declare PASS",
    )

    persistent_markdown = p3 / "reports" / "benchmark-report.md"
    regular_file(persistent_markdown, "Persistent benchmark Markdown")
    persistent_content = persistent_markdown.read_text(encoding="utf-8")
    require(
        run_id in persistent_content,
        "Persistent Markdown does not identify the current RUN_ID",
    )
    require(
        "Validation: **PASS**" in persistent_content,
        "Persistent Markdown does not declare PASS",
    )

    persistent_validation = read_json(
        p3 / "reports" / "validation-report.json",
        "Persistent validation JSON",
    )
    require(
        persistent_validation.get("latest_record", {}).get("run_id") == run_id,
        "Persistent validation JSON RUN_ID mismatch",
    )

    verified_checksums = verify_run_checksums(raw)

    return {
        "schema": "qflpn-p3-evidence-consistency-v1",
        "validation": "PASS",
        "run_id": run_id,
        "source_commit": source_commit,
        "evidence": {
            "environment": "PASS",
            "csv": "PASS",
            "validation_json": "PASS",
            "java_benchmark_json": "PASS",
            "java_benchmark_txt": "PASS",
            "run_markdown": "PASS",
            "persistent_markdown": "PASS",
            "persistent_validation_json": "PASS",
            "run_checksums": "PASS",
        },
        "verified_run_checksum_files": verified_checksums,
        "csv_dimension": int(row["dimension"]),
        "csv_nnz": int(row["non_zero_count"]),
    }


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    require(not path.is_symlink(), f"Output must not be a symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
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
        description="Cross-validate all P3 evidence for one RUN_ID."
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--run-id", default=os.environ.get("RUN_ID"))
    parser.add_argument(
        "--source-commit",
        default=os.environ.get("SOURCE_COMMIT"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("P3/reports/evidence-consistency.json"),
    )
    args = parser.parse_args()

    try:
        require(args.run_id, "--run-id or RUN_ID is required")
        require(
            args.source_commit,
            "--source-commit or SOURCE_COMMIT is required",
        )
        result = verify_evidence(
            args.root,
            run_id=args.run_id,
            source_commit=args.source_commit,
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
