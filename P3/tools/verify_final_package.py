#!/usr/bin/env python3
"""Independent fail-closed verifier for the complete QFLPN P3 package.

The final acceptance gate verifies:
- successful mandatory p3_validation stages;
- authoritative V2 and V3 benchmark validators;
- V3 46-column CSV and complete 96/192 configuration matrix;
- run-specific evidence and checksums;
- independently reconstructed MANIFEST.txt and SHA256SUMS.txt.

The two global integrity files are excluded from their own inventory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

HEX64 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

GLOBAL_INTEGRITY_NAMES = {"MANIFEST.txt", "SHA256SUMS.txt"}
EXCLUDED_DIRS = {
    "target", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}

REQUIRED_PACKAGE_FILES = (
    "P3/pom.xml",
    "P3/results/run_benchmark.sh",
    "P3/results/validate_benchmark.py",
    "P3/results/validate_benchmark_v3.py",
    "P3/results/test_validate_benchmark.py",
    "P3/results/generate_benchmark_summary.py",
    "P3/benchmarks/benchmark_results_v2.csv",
    "P3/benchmarks/benchmark_results_v3.csv",
    "P3/reports/environment.txt",
    "P3/reports/environment.json",
    "P3/reports/benchmark-v3-validation.json",
    "P3/reports/evidence-consistency.json",
    "P3/reports/benchmark-validator-tests.log",
    "P3/reports/manifest-generator-tests.log",
    "P3/reports/final-package-verifier-tests.log",
    "P3/reports/python-validation-tests.log",
    "P3/reports/root-maven-validation.log",
    "P3/reports/p3-benchmark-execution.log",
)

REQUIRED_CI_STAGES = (
    "p3_environment",
    "p3_required_files",
    "p3_python_compile",
    "p3_benchmark_tests",
    "p3_manifest_tests",
    "p3_final_package_tests",
    "p3_python_tests",
    "p3_root_maven",
    "p3_benchmark",
    "p3_benchmark_v3",
    "p3_benchmark_summary",
    "p3_evidence_consistency",
    "p3_integrity_generate",
    "p3_display_manifest",
    "p3_display_sha256",
    "p3_display_all_text",
    "p3_artifact_upload",
)


class VerificationError(RuntimeError):
    """Raised when any mandatory P3 acceptance condition fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_relative_path(value: str) -> bool:
    if not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and path.as_posix() == value
        and value.startswith("P3/")
        and value.strip() == value
    )


def independent_inventory(root: Path) -> list[str]:
    p3_root = root / "P3"
    require(
        p3_root.is_dir() and not p3_root.is_symlink(),
        "P3 directory is missing or unsafe",
    )
    found: list[str] = []

    for current, directories, files in os.walk(
        p3_root, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        directories[:] = sorted(
            name for name in directories
            if name not in EXCLUDED_DIRS
            and not (current_path / name).is_symlink()
        )
        for name in sorted(files):
            path = current_path / name
            if name in GLOBAL_INTEGRITY_NAMES:
                continue
            if path.suffix.lower() in EXCLUDED_SUFFIXES:
                continue
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            require(safe_relative_path(relative),
                    f"Unsafe filesystem path: {relative}")
            found.append(relative)

    found.sort()
    require(len(found) == len(set(found)), "Duplicate inventory paths")
    return found


def parse_manifest(path: Path) -> list[str]:
    require(path.is_file() and not path.is_symlink(),
            "P3/MANIFEST.txt is missing or unsafe")
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise VerificationError(f"Cannot read MANIFEST.txt: {exc}") from exc

    require(content.endswith("\n"), "MANIFEST.txt lacks final newline")
    entries = content.splitlines()
    require(all(entries), "MANIFEST.txt contains empty entries")
    require(entries == sorted(entries), "MANIFEST.txt is not sorted")
    require(len(entries) == len(set(entries)), "MANIFEST.txt has duplicates")

    for entry in entries:
        require(safe_relative_path(entry), f"Unsafe manifest path: {entry}")
        require(PurePosixPath(entry).name not in GLOBAL_INTEGRITY_NAMES,
                f"Self-reference in MANIFEST.txt: {entry}")
    return entries


def parse_checksums(path: Path) -> dict[str, str]:
    require(path.is_file() and not path.is_symlink(),
            "P3/SHA256SUMS.txt is missing or unsafe")
    try:
        content = path.read_text(encoding="ascii")
    except (OSError, UnicodeError) as exc:
        raise VerificationError(f"Cannot read SHA256SUMS.txt: {exc}") from exc

    require(not content or content.endswith("\n"),
            "SHA256SUMS.txt lacks final newline")
    result: dict[str, str] = {}

    for number, line in enumerate(content.splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        require(match is not None, f"Malformed SHA256SUMS line {number}")
        assert match is not None
        digest, relative = match.groups()
        require(HEX64.fullmatch(digest) is not None,
                f"Invalid digest on line {number}")
        require(safe_relative_path(relative),
                f"Unsafe checksum path: {relative}")
        require(relative not in result, f"Duplicate checksum path: {relative}")
        result[relative] = digest

    require(list(result) == sorted(result),
            "SHA256SUMS.txt entries are not sorted")
    return result


def verify_global_integrity(root: Path) -> dict[str, int]:
    p3 = root / "P3"
    manifest = parse_manifest(p3 / "MANIFEST.txt")
    checksums = parse_checksums(p3 / "SHA256SUMS.txt")
    actual = independent_inventory(root)

    require(manifest == actual,
            "MANIFEST.txt differs from independently reconstructed inventory")
    require(set(checksums) == set(manifest),
            "MANIFEST and SHA256SUMS path sets differ")

    for relative in manifest:
        target = root / PurePosixPath(relative)
        require(target.is_file() and not target.is_symlink(),
                f"Manifest target missing or unsafe: {relative}")
        require(sha256_file(target) == checksums[relative],
                f"SHA-256 mismatch: {relative}")

    return {
        "manifest_entries": len(manifest),
        "sha256_entries_verified": len(checksums),
    }


def load_json(path: Path, label: str) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"{label} missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{label} invalid JSON: {exc}") from exc
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def finite_number(value: Any, label: str) -> float:
    require(not isinstance(value, bool), f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise VerificationError(f"{label} must be numeric") from exc
    require(math.isfinite(number), f"{label} must be finite")
    return number


def load_module(path: Path, module_name: str):
    require(path.is_file() and not path.is_symlink(),
            f"Authoritative validator missing: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None,
            f"Cannot load validator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def verify_v2(root: Path, run_id: str, expected: dict[str, int]) -> dict[str, Any]:
    p3 = root / "P3"
    csv_path = p3 / "benchmarks" / "benchmark_results_v2.csv"
    validator = load_module(
        p3 / "results" / "validate_benchmark.py",
        "p3_final_v2_validator",
    )
    raw = p3 / "results" / "raw" / run_id
    report = load_json(raw / "validation-report.json", "V2 validation report")

    require(report.get("schema") == "qflpn-benchmark-v2",
            "V2 validation report schema mismatch")
    require(report.get("validation") == "PASS",
            "V2 validation report is not PASS")
    require(report.get("all_records_valid") is True,
            "V2 validation report does not confirm all records valid")

    try:
        result = validator.validate(csv_path, expected=expected)
    except Exception as exc:
        raise VerificationError(f"Authoritative V2 validator failed: {exc}") from exc

    require(result.get("schema") == "qflpn-benchmark-v2",
            "V2 authoritative validator schema mismatch")
    require(result.get("validation") == "PASS"
            and result.get("all_records_valid") is True,
            "V2 authoritative validator did not PASS")

    latest = report.get("latest_record")
    require(isinstance(latest, dict), "V2 latest_record missing")
    require(latest.get("run_id") == run_id, "V2 report RUN_ID mismatch")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        rows = [row for row in reader if row.get("run_id") == run_id]
    require(len(rows) == 1, f"V2 expected one row for {run_id}; got {len(rows)}")
    row = rows[0]

    for csv_key, json_key in (
        ("dimension", "dimension"),
        ("non_zero_count", "nnz"),
        ("speedup", "speedup"),
        ("sequential_mean_ms", "sequential_mean_ms"),
        ("parallel_mean_ms", "parallel_mean_ms"),
        ("max_absolute_error", "max_error"),
    ):
        if csv_key in {"dimension", "non_zero_count"}:
            require(int(row[csv_key]) == int(latest.get(json_key, -1)),
                    f"V2 CSV/report mismatch: {csv_key}")
        else:
            require(math.isclose(
                finite_number(row[csv_key], csv_key),
                finite_number(latest.get(json_key), json_key),
                rel_tol=1e-8, abs_tol=1e-12,
            ), f"V2 CSV/report mismatch: {csv_key}")

    return {
        "schema": "qflpn-benchmark-v2",
        "run_id": run_id,
        "records": result.get("records"),
        "dimension": int(row["dimension"]),
        "non_zero_count": int(row["non_zero_count"]),
        "speedup": finite_number(row["speedup"], "V2 speedup"),
    }


def verify_v3(root: Path, run_id: str, commit_sha: str,
              workflow_run_id: str | None) -> dict[str, Any]:
    p3 = root / "P3"
    csv_path = p3 / "benchmarks" / "benchmark_results_v3.csv"
    validator = load_module(
        p3 / "results" / "validate_benchmark_v3.py",
        "p3_final_v3_validator",
    )

    try:
        result = validator.validate(
            csv_path,
            run_id=run_id,
            workflow_run_id=workflow_run_id,
            commit_sha=commit_sha,
        )
    except Exception as exc:
        raise VerificationError(f"Authoritative V3 validator failed: {exc}") from exc

    require(result.get("schema") == "qflpn-benchmark-v3-validation-v2",
            "V3 validator schema mismatch")
    require(result.get("validation") == "PASS",
            "V3 authoritative validation is not PASS")
    require(result.get("all_records_valid") is True,
            "V3 validator does not confirm all records valid")
    require(result.get("configuration_matrix_complete") is True,
            "V3 configuration matrix incomplete")
    require(result.get("run_id") == run_id, "V3 RUN_ID mismatch")
    require(result.get("commit_sha") == commit_sha, "V3 commit mismatch")
    require(result.get("run_contract") in {"LEGACY_96", "AB_192"},
            "V3 run contract is unsupported")

    report = load_json(
        p3 / "reports" / "benchmark-v3-validation.json",
        "Persistent V3 validation report",
    )
    require(report.get("validation") == "PASS",
            "Persistent V3 validation report is not PASS")
    require(report.get("run_id") == run_id, "Persistent V3 RUN_ID mismatch")
    require(report.get("commit_sha") == commit_sha,
            "Persistent V3 commit mismatch")
    require(report.get("run_contract") == result.get("run_contract"),
            "Persistent V3 contract mismatch")
    require(report.get("validated_records") == result.get("validated_records"),
            "Persistent V3 record count mismatch")

    return {
        "schema": result["schema"],
        "run_id": run_id,
        "run_contract": result["run_contract"],
        "validated_records": result["validated_records"],
        "split_policies": result["split_policies"],
    }


def verify_ci_outcomes(path: Path) -> dict[str, str]:
    outcomes = load_json(path, "CI outcomes JSON")
    for stage in REQUIRED_CI_STAGES:
        value = outcomes.get(stage)
        require(value == "success",
                f"Mandatory p3_validation stage {stage} failed: {value!r}")
    return {stage: "success" for stage in REQUIRED_CI_STAGES}


def verify_required_files(root: Path) -> None:
    missing = [
        name for name in REQUIRED_PACKAGE_FILES
        if not (root / name).is_file()
        or (root / name).is_symlink()
    ]
    require(not missing, "Required P3 files missing or unsafe: " + ", ".join(missing))


def verify_package(
    root: Path,
    run_id: str,
    expected: dict[str, int],
    outcomes_path: Path,
    *,
    source_commit: str,
    workflow_run_id: str | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    require(root.is_dir(), f"Repository root missing: {root}")
    require(RUN_ID_RE.fullmatch(run_id or "") is not None, "Invalid RUN_ID")
    require(re.fullmatch(r"[0-9a-f]{40}", source_commit or "") is not None,
            "Invalid SOURCE_COMMIT")

    # The outcomes file is external to P3 to avoid a self-referential manifest.
    outcomes = verify_ci_outcomes(outcomes_path)
    verify_required_files(root)

    v2 = verify_v2(root, run_id, expected)
    v3 = verify_v3(root, run_id, source_commit, workflow_run_id)

    evidence = load_json(
        root / "P3" / "reports" / "evidence-consistency.json",
        "Evidence consistency report",
    )
    require(evidence.get("validation") == "PASS",
            "Evidence consistency report is not PASS")
    require(evidence.get("run_id") == run_id,
            "Evidence consistency report RUN_ID mismatch")
    require(evidence.get("source_commit") == source_commit,
            "Evidence consistency report commit mismatch")

    integrity = verify_global_integrity(root)

    return {
        "verdict": "P3_ACCEPTED",
        "run_id": run_id,
        "source_commit": source_commit,
        "workflow_run_id": workflow_run_id,
        "integrity": integrity,
        "benchmark_v2": v2,
        "benchmark_v3": v3,
        "evidence_consistency": "PASS",
        "ci_stages": outcomes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify the complete P3 package."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--workflow-run-id")
    parser.add_argument("--outcomes-json", type=Path, required=True)
    parser.add_argument("--expected-n", type=int, required=True)
    parser.add_argument("--warmup", type=int, required=True)
    parser.add_argument("--iterations", type=int, required=True)
    parser.add_argument("--threshold", type=int, required=True)
    parser.add_argument("--parallelism", type=int, required=True)
    args = parser.parse_args()

    expected = {
        "dimension": args.expected_n,
        "warmup_iterations": args.warmup,
        "measured_iterations": args.iterations,
        "threshold": args.threshold,
        "parallelism": args.parallelism,
    }

    try:
        result = verify_package(
            args.root,
            args.run_id,
            expected,
            args.outcomes_json,
            source_commit=args.source_commit,
            workflow_run_id=args.workflow_run_id,
        )
    except Exception as exc:
        print(json.dumps({
            "verdict": "P3_REJECTED",
            "error": f"{type(exc).__name__}: {exc}",
        }, indent=2, allow_nan=False))
        return 1

    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
