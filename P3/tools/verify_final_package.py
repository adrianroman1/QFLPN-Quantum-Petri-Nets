#!/usr/bin/env python3
"""Independent, fail-closed acceptance verifier for the complete P3 package.

Acceptance requires:
- all mandatory pre-integrity p3_validation stages to be successful;
- canonical V2 benchmark validation for the selected RUN_ID;
- canonical V3 validation with a complete LEGACY_96 or AB_192 matrix;
- consistent RUN_ID, workflow_run_id and source_commit provenance;
- a PASS evidence-consistency report;
- independently reconstructed MANIFEST.txt and SHA256SUMS.txt.

The global MANIFEST.txt and SHA256SUMS.txt files are excluded from their
own inventory to avoid self-referential checksums.

Integrity generation and final verification are performed directly by this
verifier and the p3_validation workflow. They are deliberately not required
as entries in ci-outcomes.json, because that file is created before those
integrity stages execute.
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

# Canonical stage identifiers recorded in ci-outcomes.json.
#
# These are stages that must have completed successfully before the
# integrity files are generated and before this final verifier runs.
#
# The following stages are intentionally NOT listed here:
# - p3_integrity_generate
# - p3_integrity_verify
# - p3_final_verification
#
# They cannot be mandatory entries in ci-outcomes.json because that file
# is produced before the integrity generation and final verification steps.
#
# Their actual operations remain mandatory:
# - verify_global_integrity() independently checks MANIFEST.txt and
#   SHA256SUMS.txt;
# - verify_package() invokes verify_global_integrity() before acceptance.
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
    "p3_artifact_upload",
)


class VerificationError(RuntimeError):
    """Raised when a mandatory P3 acceptance condition fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def regular_file(path: Path, label: str) -> None:
    require(not path.is_symlink(), f"{label} is a symlink: {path}")
    require(
        path.is_file(),
        f"{label} is missing or is not a regular file: {path}",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_relative_path(value: str) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False

    path = PurePosixPath(value)

    return (
        not path.is_absolute()
        and ".." not in path.parts
        and "." not in path.parts
        and path.as_posix() == value
        and value.startswith("P3/")
        and value.strip() == value
    )


def independent_inventory(root: Path) -> list[str]:
    """Return sorted repository-relative P3 file paths.

    Each inventory item is a path string, not a dictionary.
    Global integrity files are excluded to prevent self-reference.
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

    require(bool(entries), "MANIFEST.txt is empty")
    require(all(entries), "MANIFEST.txt contains empty entries")
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
        content.endswith("\n"),
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
    """Reconstruct and verify the complete global P3 integrity chain."""
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

    require(math.isfinite(result), f"{label} must be finite")
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
    """Verify the canonical p3_validation outcomes envelope."""
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
    """Run the canonical V2 validator and bind its result to RUN_ID."""
    p3 = root / "P3"
    csv_path = p3 / "benchmarks" / "benchmark_results_v2.csv"

    validator = load_module(
        p3 / "results" / "validate_benchmark.py",
        "p3_final_v2_validator",
    )

    regular_file(csv_path, "V2 canonical CSV")

    try:
        result = validator.validate(csv_path, expected=expected)
    except Exception as exc:
        raise VerificationError(
            f"Authoritative V2 validator failed: {exc}"
        ) from exc

    require(
        isinstance(result, dict),
        "V2 validator result is not an object",
    )
    require(
        result.get("schema") == "qflpn-benchmark-v2",
        "V2 validator schema mismatch",
    )
    require(
        result.get("validation") == "PASS"
        and result.get("all_records_valid") is True,
        "V2 authoritative validation did not PASS",
    )

    latest = result.get("latest_record")

    require(
        isinstance(latest, dict),
        "V2 validator latest_record is missing",
    )
    require(
        latest.get("run_id") == run_id,
        "V2 validator latest_record RUN_ID mismatch",
    )

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream, strict=True)
        rows = list(reader)

    matches = [
        row
        for row in rows
        if row.get("run_id") == run_id
    ]

    require(
        len(matches) == 1,
        f"V2 expected exactly one row for RUN_ID={run_id}; "
        f"got {len(matches)}",
    )

    row = matches[0]

    for csv_key, result_key in (
        ("dimension", "dimension"),
        ("non_zero_count", "nnz"),
    ):
        try:
            csv_value = int(row[csv_key])
            result_value = int(latest[result_key])
        except (KeyError, TypeError, ValueError) as exc:
            raise VerificationError(
                f"V2 invalid integer field: {csv_key}"
            ) from exc

        require(
            csv_value == result_value,
            f"V2 CSV/validator mismatch: {csv_key}",
        )

    for csv_key, result_key in (
        ("speedup", "speedup"),
        ("sequential_mean_ms", "sequential_mean_ms"),
        ("parallel_mean_ms", "parallel_mean_ms"),
        ("max_absolute_error", "max_error"),
    ):
        csv_value = finite_number(row.get(csv_key), csv_key)
        result_value = finite_number(latest.get(result_key), result_key)

        require(
            math.isclose(
                csv_value,
                result_value,
                rel_tol=1e-8,
                abs_tol=1e-12,
            ),
            f"V2 CSV/validator mismatch: {csv_key}",
        )

    return {
        "schema": "qflpn-benchmark-v2",
        "validation": "PASS",
        "run_id": run_id,
        "records": result.get("records"),
        "dimension": int(row["dimension"]),
        "non_zero_count": int(row["non_zero_count"]),
        "speedup": finite_number(row["speedup"], "V2 speedup"),
    }


def verify_v3(
    root: Path,
    run_id: str,
    source_commit: str,
    workflow_run_id: str | None,
) -> dict[str, Any]:
    """Run the authoritative V3 validator for the selected execution."""
    p3 = root / "P3"
    csv_path = p3 / "benchmarks" / "benchmark_results_v3.csv"

    validator = load_module(
        p3 / "results" / "validate_benchmark_v3.py",
        "p3_final_v3_validator",
    )

    regular_file(csv_path, "V3 canonical CSV")

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
        "V3 validator result is not an object",
    )
    require(
        result.get("schema") == "qflpn-benchmark-v3-validation-v2",
        "V3 validator schema mismatch",
    )
    require(
        result.get("validation") == "PASS"
        and result.get("all_records_valid") is True,
        "V3 authoritative validation did not PASS",
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

    expected_records = (
        96
        if contract == "LEGACY_96"
        else 192
    )

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
            policies == ["ROW_BOUNDARY_SCAN"],
            "LEGACY_96 must contain only ROW_BOUNDARY_SCAN",
        )
    else:
        require(
            set(policies)
            == {"ROW_BOUNDARY_SCAN", "BINARY_NNZ_SPLIT"},
            "AB_192 must contain both A/B split policies",
        )

    report_path = (
        p3 / "reports" / "benchmark-v3-validation.json"
    )
    report = load_json(
        report_path,
        "Persistent V3 validation report",
    )

    for key, expected_value in (
        ("schema", result["schema"]),
        ("validation", "PASS"),
        ("all_records_valid", True),
        ("run_id", run_id),
        ("commit_sha", source_commit),
        ("workflow_run_id", result.get("workflow_run_id")),
        ("run_contract", contract),
        ("expected_records", expected_records),
        ("validated_records", expected_records),
    ):
        require(
            report.get(key) == expected_value,
            f"Persistent V3 report mismatch: {key}",
        )

    checksum_path = (
        p3 / "reports" / "benchmark-v3-SHA256SUMS.txt"
    )
    regular_file(
        checksum_path,
        "V3 run-specific SHA256SUMS",
    )

    try:
        checksum_lines = checksum_path.read_text(
            encoding="ascii"
        ).splitlines()
    except (OSError, UnicodeError) as exc:
        raise VerificationError(
            f"Cannot read V3 checksum file: {exc}"
        ) from exc

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
        "V3 checksum entry is malformed",
    )
    assert match is not None

    require(
        sha256_file(csv_path) == match.group(1),
        "V3 canonical CSV SHA-256 mismatch",
    )

    return {
        "schema": result["schema"],
        "validation": "PASS",
        "run_id": run_id,
        "workflow_run_id": result.get("workflow_run_id"),
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
    """Independently rerun the cross-evidence verifier and check its report."""
    p3 = root / "P3"
    report_path = p3 / "reports" / "evidence-consistency.json"

    report = load_json(
        report_path,
        "P3 evidence consistency report",
    )

    require(
        report.get("schema") == "qflpn-p3-evidence-consistency-v2",
        "Evidence consistency schema mismatch",
    )
    require(
        report.get("validation") == "PASS",
        "Evidence consistency report is not PASS",
    )
    require(
        report.get("run_id") == run_id,
        "Evidence consistency RUN_ID mismatch",
    )
    require(
        report.get("source_commit") == source_commit,
        "Evidence consistency source_commit mismatch",
    )

    if workflow_run_id is not None:
        require(
            str(report.get("workflow_run_id"))
            == str(workflow_run_id),
            "Evidence consistency workflow_run_id mismatch",
        )

    module = load_module(
        p3 / "tools" / "verify_evidence_consistency.py",
        "p3_final_evidence_consistency",
    )

    verify_function = getattr(
        module,
        "verify_evidence",
        None,
    )

    require(
        callable(verify_function),
        "Evidence consistency module has no verify_evidence() function",
    )

    try:
        independent_result = verify_function(
            root,
            run_id=run_id,
            source_commit=source_commit,
            workflow_run_id=workflow_run_id,
        )
    except Exception as exc:
        raise VerificationError(
            f"Independent evidence consistency verification failed: {exc}"
        ) from exc

    require(
        isinstance(independent_result, dict),
        "Independent evidence verifier returned a non-object result",
    )
    require(
        independent_result.get("validation") == "PASS",
        "Independent evidence verifier did not PASS",
    )

    details = report.get("evidence")

    require(
        isinstance(details, dict),
        "Evidence consistency report has no evidence object",
    )

    for item in (
        "environment",
        "benchmark_v2",
        "benchmark_v3",
        "v3_authoritative_validator",
        "v3_persistent_report",
        "v3_checksums",
    ):
        require(
            details.get(item) == "PASS",
            f"Evidence consistency item failed: {item}",
        )

    return {
        "validation": "PASS",
        "run_id": run_id,
        "source_commit": source_commit,
        "workflow_run_id": workflow_run_id,
        "items": sorted(details),
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
    """Verify all acceptance gates for one P3 execution."""
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

    required_expected = {
        "dimension",
        "warmup_iterations",
        "measured_iterations",
        "threshold",
        "parallelism",
    }

    require(
        set(expected) == required_expected,
        "V2 expected-configuration keys mismatch: "
        f"expected={sorted(required_expected)}, "
        f"received={sorted(expected)}",
    )

    for key, value in expected.items():
        minimum = 0 if key == "warmup_iterations" else 1

        require(
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= minimum,
            f"Invalid V2 expected value: {key}",
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

    # These checks are mandatory and independent of ci-outcomes.json.
    # The verifier reconstructs the inventory and recalculates every
    # SHA-256 digest before it can return P3_ACCEPTED.
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
            "Independently verify the complete P3 V2/V3 package, "
            "provenance, p3_validation stages and global integrity."
        )
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
