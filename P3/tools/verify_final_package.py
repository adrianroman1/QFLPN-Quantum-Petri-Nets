#!/usr/bin/env python3
"""Independent fail-closed verifier for the complete QFLPN P3 package.

Acceptance requires:
- mandatory p3_validation stages to have succeeded;
- canonical V2 benchmark validation;
- canonical V3 benchmark validation;
- complete V3 LEGACY_96 or AB_192 configuration matrix;
- matching RUN_ID, workflow_run_id and source commit provenance;
- consistent evidence reports;
- independently reconstructed MANIFEST.txt and SHA256SUMS.txt.

MANIFEST.txt and SHA256SUMS.txt are excluded from their own inventory.
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

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
WORKFLOW_ID_RE = re.compile(r"^[0-9]+$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

GLOBAL_INTEGRITY_NAMES = {"MANIFEST.txt", "SHA256SUMS.txt"}

EXCLUDED_DIRS = {
    "target",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

EXCLUDED_SUFFIXES = {".pyc", ".pyo"}

REQUIRED_PACKAGE_FILES = (
    "P3/pom.xml",
    "P3/results/run_benchmark.sh",
    "P3/results/validate_benchmark.py",
    "P3/results/validate_benchmark_v3.py",
    "P3/results/generate_benchmark_summary.py",
    "P3/tools/verify_evidence_consistency.py",
    "P3/tools/verify_final_package.py",
    "P3/tools/compute_checksums.py",
    "P3/tests/test_verify_evidence_consistency.py",
    "P3/tests/test_verify_final_package.py",
    "P3/tests/test_validate_benchmark_v3.py",
    "P3/benchmarks/benchmark_results_v2.csv",
    "P3/benchmarks/benchmark_results_v3.csv",
    "P3/reports/environment.json",
    "P3/reports/benchmark-v3-validation.json",
    "P3/reports/evidence-consistency.json",
)

# These are logical stage identifiers, not display names.
# The workflow must record them under the "stages" JSON object.
REQUIRED_CI_STAGES = (
    "p3_environment",
    "p3_required_files",
    "p3_python_compile",
    "p3_benchmark_tests",
    "p3_manifest_tests",
    "p3_final_package_tests",
    "p3_python_tests",
    "p3_root_maven",
    "p3_maven",
    "p3_benchmark_v2",
    "p3_benchmark_v2_validation",
    "p3_benchmark_v3",
    "p3_benchmark_v3_validation",
    "p3_benchmark_summary",
    "p3_evidence_consistency",
    "p3_integrity_generate",
    "p3_integrity_verify",
    "p3_final_verification",
    "p3_artifact_upload",
)


class VerificationError(RuntimeError):
    """Raised when a mandatory P3 acceptance condition fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def regular_file(path: Path, label: str) -> None:
    require(not path.is_symlink(), f"{label} is a symlink: {path}")
    require(path.is_file(), f"{label} is missing or not a regular file: {path}")


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
    """Return sorted repository-relative P3 file paths.

    The return type is deliberately list[str]. It is not a list of
    dictionaries containing path and digest fields.
    """
    root = Path(root).resolve()
    p3_root = root / "P3"

    require(
        p3_root.is_dir() and not p3_root.is_symlink(),
        "P3 directory is missing or unsafe",
    )

    found: list[str] = []

    for current, directories, files in os.walk(
        p3_root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)

        directories[:] = sorted(
            name
            for name in directories
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

            require(
                safe_relative_path(relative),
                f"Unsafe filesystem path: {relative}",
            )

            found.append(relative)

    found.sort()

    require(
        len(found) == len(set(found)),
        "Duplicate paths in independently reconstructed inventory",
    )

    return found


def parse_manifest(path: Path) -> list[str]:
    regular_file(path, "P3/MANIFEST.txt")

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise VerificationError(
            f"Cannot read MANIFEST.txt: {exc}"
        ) from exc

    require(
        content.endswith("\n"),
        "MANIFEST.txt must end with a newline",
    )

    entries = content.splitlines()

    require(
        all(entries),
        "MANIFEST.txt contains empty entries",
    )

    require(
        entries == sorted(entries),
        "MANIFEST.txt entries are not sorted",
    )

    require(
        len(entries) == len(set(entries)),
        "MANIFEST.txt contains duplicate paths",
    )

    for entry in entries:
        require(
            safe_relative_path(entry),
            f"Unsafe manifest path: {entry}",
        )

        require(
            PurePosixPath(entry).name not in GLOBAL_INTEGRITY_NAMES,
            f"MANIFEST self-reference detected: {entry}",
        )

    return entries


def parse_checksums(path: Path) -> dict[str, str]:
    regular_file(path, "P3/SHA256SUMS.txt")

    try:
        content = path.read_text(encoding="ascii")
    except (OSError, UnicodeError) as exc:
        raise VerificationError(
            f"Cannot read SHA256SUMS.txt: {exc}"
        ) from exc

    require(
        not content or content.endswith("\n"),
        "SHA256SUMS.txt must end with a newline",
    )

    result: dict[str, str] = {}

    for number, line in enumerate(content.splitlines(), start=1):
        match = re.fullmatch(
            r"([0-9a-f]{64})  ([^\r\n]+)",
            line,
        )

        require(
            match is not None,
            f"Malformed SHA256SUMS.txt line {number}",
        )

        assert match is not None

        digest, relative = match.groups()

        require(
            HEX64_RE.fullmatch(digest) is not None,
            f"Invalid SHA-256 digest on line {number}",
        )

        require(
            safe_relative_path(relative),
            f"Unsafe checksum path: {relative}",
        )

        require(
            relative not in result,
            f"Duplicate checksum path: {relative}",
        )

        result[relative] = digest

    require(
        list(result) == sorted(result),
        "SHA256SUMS.txt entries are not sorted",
    )

    return result


def verify_global_integrity(root: Path) -> dict[str, int]:
    root = Path(root).resolve()
    p3 = root / "P3"

    manifest = parse_manifest(p3 / "MANIFEST.txt")
    checksums = parse_checksums(p3 / "SHA256SUMS.txt")
    actual = independent_inventory(root)

    require(
        manifest == actual,
        "MANIFEST.txt differs from independently reconstructed inventory",
    )

    require(
        set(checksums) == set(manifest),
        "MANIFEST.txt and SHA256SUMS.txt path sets differ",
    )

    for relative in manifest:
        target = root / PurePosixPath(relative)

        regular_file(target, f"Manifest target {relative}")

        actual_digest = sha256_file(target)

        require(
            actual_digest == checksums[relative],
            f"SHA-256 mismatch: {relative}",
        )

    return {
        "manifest_entries": len(manifest),
        "sha256_entries_verified": len(checksums),
    }


def load_json(path: Path, label: str) -> dict[str, Any]:
    regular_file(path, label)

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(
            f"{label} contains invalid JSON: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"{label} must contain a JSON object",
    )

    return value


def finite_number(value: Any, label: str) -> float:
    require(
        not isinstance(value, bool),
        f"{label} must be numeric, not boolean",
    )

    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise VerificationError(
            f"{label} must be numeric"
        ) from exc

    require(
        math.isfinite(result),
        f"{label} must be finite",
    )

    return result


def load_module(path: Path, module_name: str):
    regular_file(path, f"Authoritative validator {path}")

    spec = importlib.util.spec_from_file_location(module_name, path)

    require(
        spec is not None and spec.loader is not None,
        f"Cannot load validator: {path}",
    )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


def verify_ci_outcomes(
    path: Path,
    expected_run_id: str,
    expected_commit: str,
    expected_workflow_run_id: str | None,
) -> dict[str, str]:
    """Validate the p3_validation outcomes envelope and all mandatory stages.

    Canonical structure:
    {
      "schema": "qflpn-p3-ci-outcomes-v1",
      "run_id": "...",
      "source_commit": "...",
      "workflow_run_id": "...",
      "stages": {
        "p3_environment": "success",
        ...
      }
    }
    """
    outcomes = load_json(path, "CI outcomes JSON")

    require(
        outcomes.get("schema") == "qflpn-p3-ci-outcomes-v1",
        "CI outcomes schema mismatch",
    )

    require(
        outcomes.get("run_id") == expected_run_id,
        "CI outcomes RUN_ID mismatch",
    )

    require(
        outcomes.get("source_commit") == expected_commit,
        "CI outcomes source_commit mismatch",
    )

    if expected_workflow_run_id is not None:
        require(
            str(outcomes.get("workflow_run_id"))
            == str(expected_workflow_run_id),
            "CI outcomes workflow_run_id mismatch",
        )

    stages = outcomes.get("stages")

    require(
        isinstance(stages, dict),
        "CI outcomes must contain a stages JSON object",
    )

    missing = [
        stage
        for stage in REQUIRED_CI_STAGES
        if stage not in stages
    ]

    require(
        not missing,
        "Missing mandatory p3_validation stages: "
        + ", ".join(missing),
    )

    failed = {
        stage: stages.get(stage)
        for stage in REQUIRED_CI_STAGES
        if stages.get(stage) != "success"
    }

    require(
        not failed,
        "Mandatory p3_validation stages did not succeed: "
        + json.dumps(failed, sort_keys=True),
    )

    return {
        stage: "success"
        for stage in REQUIRED_CI_STAGES
    }


def verify_required_files(root: Path) -> None:
    root = Path(root).resolve()

    missing = [
        relative
        for relative in REQUIRED_PACKAGE_FILES
        if not (root / relative).is_file()
        or (root / relative).is_symlink()
    ]

    require(
        not missing,
        "Required P3 package files missing or unsafe: "
        + ", ".join(missing),
    )


def verify_v2(
    root: Path,
    run_id: str,
    expected: dict[str, int],
) -> dict[str, Any]:
    p3 = root / "P3"
    csv_path = p3 / "benchmarks" / "benchmark_results_v2.csv"

    validator = load_module(
        p3 / "results" / "validate_benchmark.py",
        "p3_final_v2_validator",
    )

    raw = p3 / "results" / "raw" / run_id

    report = load_json(
        raw / "validation-report.json",
        "V2 validation report",
    )

    require(
        report.get("schema") == "qflpn-benchmark-v2",
        "V2 validation report schema mismatch",
    )

    require(
        report.get("validation") == "PASS",
        "V2 validation report is not PASS",
    )

    require(
        report.get("all_records_valid") is True,
        "V2 report does not confirm all records valid",
    )

    try:
        result = validator.validate(
            csv_path,
            expected=expected,
        )
    except Exception as exc:
        raise VerificationError(
            f"Authoritative V2 validator failed: {exc}"
        ) from exc

    require(
        isinstance(result, dict),
        "V2 validator did not return a JSON-compatible object",
    )

    require(
        result.get("schema") == "qflpn-benchmark-v2",
        "V2 authoritative validator schema mismatch",
    )

    require(
        result.get("validation") == "PASS"
        and result.get("all_records_valid") is True,
        "V2 authoritative validator did not PASS",
    )

    latest = report.get("latest_record")

    require(
        isinstance(latest, dict),
        "V2 validation report latest_record is missing",
    )

    require(
        latest.get("run_id") == run_id,
        "V2 validation report RUN_ID mismatch",
    )

    regular_file(csv_path, "V2 canonical CSV")

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream, strict=True)
        rows = [
            row
            for row in reader
            if row.get("run_id") == run_id
        ]

    require(
        len(rows) == 1,
        f"V2 expected exactly one row for {run_id}; got {len(rows)}",
    )

    row = rows[0]

    for csv_key, json_key in (
        ("dimension", "dimension"),
        ("non_zero_count", "nnz"),
    ):
        try:
            csv_value = int(row[csv_key])
            json_value = int(latest[json_key])
        except (KeyError, TypeError, ValueError) as exc:
            raise VerificationError(
                f"V2 invalid integer field: {csv_key}"
            ) from exc

        require(
            csv_value == json_value,
            f"V2 CSV/report mismatch: {csv_key}",
        )

    for csv_key, json_key in (
        ("speedup", "speedup"),
        ("sequential_mean_ms", "sequential_mean_ms"),
        ("parallel_mean_ms", "parallel_mean_ms"),
        ("max_absolute_error", "max_error"),
    ):
        require(
            math.isclose(
                finite_number(row.get(csv_key), csv_key),
                finite_number(latest.get(json_key), json_key),
                rel_tol=1e-8,
                abs_tol=1e-12,
            ),
            f"V2 CSV/report mismatch: {csv_key}",
        )

    return {
        "schema": "qflpn-benchmark-v2",
        "validation": "PASS",
        "run_id": run_id,
        "dimension": int(row["dimension"]),
        "non_zero_count": int(row["non_zero_count"]),
        "speedup": finite_number(row["speedup"], "V2 speedup"),
        "validator_records": result.get("records"),
    }


def verify_v3(
    root: Path,
    run_id: str,
    source_commit: str,
    workflow_run_id: str | None,
) -> dict[str, Any]:
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
            commit_sha=source_commit,
        )
    except Exception as exc:
        raise VerificationError(
            f"Authoritative V3 validator failed: {exc}"
        ) from exc

    require(
        isinstance(result, dict),
        "V3 validator did not return a result object",
    )

    require(
        result.get("schema") == "qflpn-benchmark-v3-validation-v2",
        "V3 validator schema mismatch",
    )

    require(
        result.get("validation") == "PASS",
        "V3 authoritative validation is not PASS",
    )

    require(
        result.get("all_records_valid") is True,
        "V3 validator does not confirm all records valid",
    )

    require(
        result.get("configuration_matrix_complete") is True,
        "V3 configuration matrix is incomplete",
    )

    require(
        result.get("run_id") == run_id,
        "V3 RUN_ID mismatch",
    )

    require(
        result.get("commit_sha") == source_commit,
        "V3 source commit mismatch",
    )

    if workflow_run_id is not None:
        require(
            str(result.get("workflow_run_id"))
            == str(workflow_run_id),
            "V3 workflow_run_id mismatch",
        )

    contract = result.get("run_contract")

    require(
        contract in {"LEGACY_96", "AB_192"},
        f"Unsupported V3 run contract: {contract!r}",
    )

    expected_records = 96 if contract == "LEGACY_96" else 192

    require(
        result.get("expected_records") == expected_records,
        "V3 expected_records does not match selected matrix contract",
    )

    require(
        result.get("validated_records") == expected_records,
        "V3 validated_records does not match selected matrix contract",
    )

    policies = result.get("split_policies")

    require(
        isinstance(policies, list) and bool(policies),
        "V3 split_policies is missing or invalid",
    )

    if contract == "LEGACY_96":
        require(
            len(policies) == 1,
            "LEGACY_96 must contain exactly one split policy",
        )
    else:
        require(
            set(policies) == {"ROW_BOUNDARY_SCAN", "BINARY_NNZ_SPLIT"},
            "AB_192 must contain both A/B split policies",
        )

    report_path = p3 / "reports" / "benchmark-v3-validation.json"

    report = load_json(
        report_path,
        "Persistent V3 validation report",
    )

    require(
        report.get("schema") == result["schema"],
        "Persistent V3 report schema mismatch",
    )

    require(
        report.get("validation") == "PASS",
        "Persistent V3 validation report is not PASS",
    )

    require(
        report.get("all_records_valid") is True,
        "Persistent V3 report does not confirm all records valid",
    )

    require(
        report.get("run_id") == run_id,
        "Persistent V3 report RUN_ID mismatch",
    )

    require(
        report.get("commit_sha") == source_commit,
        "Persistent V3 report commit mismatch",
    )

    require(
        report.get("workflow_run_id") == result.get("workflow_run_id"),
        "Persistent V3 report workflow_run_id mismatch",
    )

    require(
        report.get("run_contract") == contract,
        "Persistent V3 report contract mismatch",
    )

    require(
        report.get("expected_records") == expected_records,
        "Persistent V3 report expected record count mismatch",
    )

    require(
        report.get("validated_records") == expected_records,
        "Persistent V3 report validated record count mismatch",
    )

    checksum_path = p3 / "reports" / "benchmark-v3-SHA256SUMS.txt"

    regular_file(
        checksum_path,
        "V3 run-specific SHA256SUMS",
    )

    checksum_content = checksum_path.read_text(encoding="ascii")

    checksum_lines = checksum_content.splitlines()

    require(
        len(checksum_lines) == 1,
        "V3 run-specific checksum file must contain exactly one entry",
    )

    match = re.fullmatch(
        r"([0-9a-f]{64})  benchmarks/benchmark_results_v3\.csv",
        checksum_lines[0],
    )

    require(
        match is not None,
        "V3 run-specific checksum entry is malformed",
    )

    assert match is not None

    actual_digest = sha256_file(csv_path)

    require(
        actual_digest == match.group(1),
        "V3 canonical CSV SHA-256 mismatch",
    )

    return {
        "schema": result["schema"],
        "validation": "PASS",
        "run_id": run_id,
        "workflow_run_id": result["workflow_run_id"],
        "commit_sha": source_commit,
        "run_contract": contract,
        "expected_records": expected_records,
        "validated_records": expected_records,
        "split_policies": policies,
        "maximum_absolute_error": result.get(
            "maximum_absolute_error"
        ),
    }


def verify_evidence_consistency(
    root: Path,
    run_id: str,
    source_commit: str,
    workflow_run_id: str | None,
) -> dict[str, Any]:
    path = root / "P3" / "reports" / "evidence-consistency.json"

    evidence = load_json(
        path,
        "P3 evidence consistency report",
    )

    require(
        evidence.get("schema") == "qflpn-p3-evidence-consistency-v2",
        "Evidence consistency schema mismatch",
    )

    require(
        evidence.get("validation") == "PASS",
        "Evidence consistency report is not PASS",
    )

    require(
        evidence.get("run_id") == run_id,
        "Evidence consistency RUN_ID mismatch",
    )

    require(
        evidence.get("source_commit") == source_commit,
        "Evidence consistency source commit mismatch",
    )

    if workflow_run_id is not None:
        require(
            str(evidence.get("workflow_run_id"))
            == str(workflow_run_id),
            "Evidence consistency workflow_run_id mismatch",
        )

    details = evidence.get("evidence")

    require(
        isinstance(details, dict),
        "Evidence consistency report has no evidence object",
    )

    required_evidence = (
        "environment",
        "benchmark_v2",
        "benchmark_v3",
        "v3_authoritative_validator",
        "v3_persistent_report",
        "v3_checksums",
    )

    for name in required_evidence:
        require(
            details.get(name) == "PASS",
            f"Evidence consistency item failed: {name}",
        )

    return {
        "validation": "PASS",
        "run_id": run_id,
        "source_commit": source_commit,
        "workflow_run_id": workflow_run_id,
        "items": list(required_evidence),
    }


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

    require(
        root.is_dir(),
        f"Repository root does not exist: {root}",
    )

    require(
        RUN_ID_RE.fullmatch(run_id or "") is not None,
        "Invalid RUN_ID",
    )

    require(
        COMMIT_RE.fullmatch(source_commit or "") is not None,
        "Invalid SOURCE_COMMIT",
    )

    if workflow_run_id is not None:
        require(
            WORKFLOW_ID_RE.fullmatch(str(workflow_run_id)) is not None,
            "Invalid workflow_run_id",
        )

    outcomes = verify_ci_outcomes(
        Path(outcomes_path),
        expected_run_id=run_id,
        expected_commit=source_commit,
        expected_workflow_run_id=workflow_run_id,
    )

    verify_required_files(root)

    v2 = verify_v2(
        root,
        run_id,
        expected,
    )

    v3 = verify_v3(
        root,
        run_id,
        source_commit,
        workflow_run_id,
    )

    evidence = verify_evidence_consistency(
        root,
        run_id,
        source_commit,
        workflow_run_id,
    )

    integrity = verify_global_integrity(root)

    return {
        "verdict": "P3_ACCEPTED",
        "run_id": run_id,
        "source_commit": source_commit,
        "workflow_run_id": workflow_run_id,
        "benchmark_v2": v2,
        "benchmark_v3": v3,
        "evidence_consistency": evidence,
        "ci_stages": outcomes,
        "integrity": integrity,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Independently verify the complete P3 V2/V3 package "
            "and p3_validation evidence."
        )
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
    )

    parser.add_argument(
        "--run-id",
        required=True,
    )

    parser.add_argument(
        "--source-commit",
        required=True,
    )

    parser.add_argument(
        "--workflow-run-id",
    )

    parser.add_argument(
        "--outcomes-json",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--expected-n",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--warmup",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--iterations",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--threshold",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--parallelism",
        type=int,
        required=True,
    )

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
            root=args.root,
            run_id=args.run_id,
            expected=expected,
            outcomes_path=args.outcomes_json,
            source_commit=args.source_commit,
            workflow_run_id=args.workflow_run_id,
        )

    except Exception as exc:
        failure = {
            "verdict": "P3_REJECTED",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

        print(
            json.dumps(
                failure,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
