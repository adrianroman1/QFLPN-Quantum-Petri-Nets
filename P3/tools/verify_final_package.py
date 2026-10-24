#!/usr/bin/env python3
"""Fail-closed independent final verifier for the QFLPN P3 package.

Integrity contract:
- P3/MANIFEST.txt: sorted repository-relative POSIX paths, one per line.
- P3/SHA256SUMS.txt: SHA-256 entries for exactly those paths.
- The two global integrity files are excluded from their own inventory.

Benchmark contract:
- qflpn-benchmark-v2, validated by P3/results/validate_benchmark.py.
- CSV and validation JSON must identify the same unique RUN_ID.
- Run-specific evidence checksums must match the generated evidence files.

CI contract:
- Every mandatory workflow stage must be recorded as "success".
- The outcomes JSON is supplied from RUNNER_TEMP, outside P3.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
P3 = ROOT / "P3"

HEX64 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

GLOBAL_INTEGRITY_NAMES = {
    "MANIFEST.txt",
    "SHA256SUMS.txt",
}

EXCLUDED_DIRS = {
    "target",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}

REQUIRED_PACKAGE_FILES = (
    "P3/pom.xml",
    "P3/results/run_benchmark.sh",
    "P3/results/validate_benchmark.py",
    "P3/results/test_validate_benchmark.py",
    "P3/results/generate_benchmark_summary.py",
    "P3/benchmarks/benchmark_results_v2.csv",
    "P3/reports/environment.txt",
    "P3/reports/benchmark-validator-tests.log",
    "P3/reports/manifest-generator-tests.log",
    "P3/reports/final-package-verifier-tests.log",
    "P3/reports/python-validation-tests.log",
    "P3/reports/root-maven-validation.log",
    "P3/reports/p3-benchmark-execution.log",
)

REQUIRED_RUN_FILES = (
    "benchmark-report.txt",
    "benchmark-report.md",
    "benchmark-report.json",
    "validation-report.json",
    "SHA256SUMS.txt",
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
    "p3_benchmark_summary",
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
    """Reconstruct P3 inventory without importing the generator."""
    p3_root = root / "P3"

    require(
        p3_root.is_dir() and not p3_root.is_symlink(),
        "P3 directory is missing or unsafe",
    )

    found: list[str] = []

    for current, directory_names, file_names in os.walk(
        p3_root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)

        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in EXCLUDED_DIRS
            and not (current_path / name).is_symlink()
        )

        for name in sorted(file_names):
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
                f"unsafe filesystem path discovered: {relative}",
            )

            found.append(relative)

    found.sort()

    require(
        len(found) == len(set(found)),
        "independent filesystem inventory contains duplicate paths",
    )

    return found


def parse_manifest(path: Path) -> list[str]:
    try:
        raw = path.read_bytes()
        content = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise VerificationError(
            f"cannot read UTF-8 MANIFEST.txt: {exc}"
        ) from exc

    require(content.endswith("\n"), "MANIFEST.txt lacks final newline")

    entries = content.splitlines()

    require(
        all(entries),
        "MANIFEST.txt contains an empty path entry",
    )

    require(
        entries == sorted(entries),
        "MANIFEST.txt paths are not sorted",
    )

    require(
        len(entries) == len(set(entries)),
        "MANIFEST.txt contains duplicate paths",
    )

    for entry in entries:
        require(
            safe_relative_path(entry),
            f"unsafe or noncanonical manifest path: {entry}",
        )

        require(
            PurePosixPath(entry).name not in GLOBAL_INTEGRITY_NAMES,
            f"self-referential global integrity path: {entry}",
        )

    return entries


def parse_checksums(path: Path) -> dict[str, str]:
    try:
        content = path.read_text(encoding="ascii")
    except (OSError, UnicodeError) as exc:
        raise VerificationError(
            f"cannot read ASCII SHA256SUMS.txt: {exc}"
        ) from exc

    require(
        not content or content.endswith("\n"),
        "SHA256SUMS.txt lacks final newline",
    )

    result: dict[str, str] = {}

    for number, line in enumerate(content.splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)

        require(
            match is not None,
            f"malformed SHA256SUMS.txt line {number}",
        )

        assert match is not None
        digest, relative = match.groups()

        require(
            HEX64.fullmatch(digest) is not None,
            f"invalid SHA-256 digest on line {number}",
        )

        require(
            safe_relative_path(relative),
            f"unsafe checksum path on line {number}: {relative}",
        )

        require(
            relative not in result,
            f"duplicate checksum path: {relative}",
        )

        result[relative] = digest

    require(
        list(result) == sorted(result),
        "SHA256SUMS.txt entries are not sorted",
    )

    return result


def verify_global_integrity(root: Path) -> dict[str, int]:
    manifest_path = root / "P3" / "MANIFEST.txt"
    checksums_path = root / "P3" / "SHA256SUMS.txt"

    require(
        manifest_path.is_file() and not manifest_path.is_symlink(),
        "P3/MANIFEST.txt is missing or unsafe",
    )

    require(
        checksums_path.is_file() and not checksums_path.is_symlink(),
        "P3/SHA256SUMS.txt is missing or unsafe",
    )

    manifest = parse_manifest(manifest_path)
    checksums = parse_checksums(checksums_path)
    actual = independent_inventory(root)

    require(
        manifest == actual,
        "MANIFEST.txt does not match independently reconstructed P3 inventory",
    )

    require(
        set(checksums) == set(manifest),
        "MANIFEST.txt and SHA256SUMS.txt path sets differ",
    )

    for relative in manifest:
        target = root / PurePosixPath(relative)

        require(
            target.is_file() and not target.is_symlink(),
            f"manifest target is missing or unsafe: {relative}",
        )

        actual_digest = sha256_file(target)

        require(
            actual_digest == checksums[relative],
            f"SHA-256 mismatch: {relative}",
        )

    return {
        "manifest_entries": len(manifest),
        "sha256_entries_verified": len(checksums),
    }


def verify_required_files(root: Path) -> None:
    missing = [
        relative
        for relative in REQUIRED_PACKAGE_FILES
        if not (root / relative).is_file()
    ]

    require(
        not missing,
        "required P3 package files are missing: " + ", ".join(missing),
    )


def load_json(path: Path, label: str) -> dict[str, Any]:
    require(
        path.is_file() and not path.is_symlink(),
        f"{label} is missing",
    )

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(
            f"{label} is invalid JSON: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"{label} must be a JSON object",
    )

    return value


def finite_number(value: Any, label: str) -> float:
    """Convert a finite numeric value, including a CSV numeric string.

    csv.DictReader returns strings for every CSV field. Reject booleans,
    empty strings, non-numeric strings, NaN and positive/negative infinity.
    """
    require(
        not isinstance(value, bool),
        f"{label} must be numeric",
    )

    require(
        isinstance(value, (int, float, str)),
        f"{label} must be numeric",
    )

    if isinstance(value, str):
        normalized = value.strip()

        require(
            bool(normalized),
            f"{label} must be numeric",
        )

        try:
            result = float(normalized)
        except ValueError as exc:
            raise VerificationError(
                f"{label} must be numeric"
            ) from exc
    else:
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


def verify_benchmark(
    root: Path,
    run_id: str,
    expected: dict[str, int],
) -> dict[str, Any]:
    require(
        isinstance(run_id, str)
        and RUN_ID_RE.fullmatch(run_id) is not None,
        "RUN_ID contains unsupported characters",
    )

    csv_path = (
        root
        / "P3"
        / "benchmarks"
        / "benchmark_results_v2.csv"
    )

    validator_path = (
        root
        / "P3"
        / "results"
        / "validate_benchmark.py"
    )

    report_path = (
        root
        / "P3"
        / "results"
        / "raw"
        / run_id
        / "validation-report.json"
    )

    require(
        csv_path.is_file() and not csv_path.is_symlink(),
        "canonical benchmark V2 CSV is missing",
    )

    require(
        validator_path.is_file() and not validator_path.is_symlink(),
        "canonical benchmark validator is missing",
    )

    # Load the authoritative production validator.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "p3_authoritative_benchmark_validator",
        validator_path,
    )

    require(
        spec is not None and spec.loader is not None,
        "cannot load authoritative P3 benchmark validator",
    )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    # Identify the requested RUN_ID from the canonical CSV before
    # resolving its run-specific report directory. This produces a useful
    # RUN_ID failure instead of incorrectly reporting a missing report.
    try:
        with csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            reader = csv.DictReader(stream, strict=True)
            fieldnames = reader.fieldnames
            csv_rows = list(reader)

        if fieldnames is not None and "run_id" in fieldnames:
            available_run_ids = [
                row.get("run_id")
                for row in csv_rows
                if row.get("run_id") not in (None, "")
            ]

            require(
                run_id in available_run_ids,
                "RUN_ID does not exist in canonical benchmark CSV: "
                f"{run_id}; available RUN_ID values: "
                f"{sorted(set(available_run_ids))}",
            )
    except (OSError, UnicodeError, csv.Error) as exc:
        raise VerificationError(
            f"cannot read canonical benchmark CSV: {exc}"
        ) from exc

    # The production validator raises its own ValidationError (a
    # ValueError subclass). Convert it to VerificationError so the
    # independent package verifier always has one fail-closed error type.
    try:
        result = module.validate(csv_path, expected=expected)
    except Exception as exc:
        raise VerificationError(
            f"authoritative benchmark validation failed: {exc}"
        ) from exc

    require(
        result.get("schema") == "qflpn-benchmark-v2",
        "benchmark validator returned an unexpected schema",
    )

    require(
        result.get("validation") == "PASS"
        and result.get("all_records_valid") is True,
        "authoritative benchmark validator did not return PASS",
    )

    report = load_json(
        report_path,
        "run-specific validation-report.json",
    )

    require(
        report.get("schema") == "qflpn-benchmark-v2",
        "validation-report.json schema mismatch",
    )

    require(
        report.get("validation") == "PASS",
        "validation-report.json does not report PASS",
    )

    require(
        report.get("all_records_valid") is True,
        "validation-report.json does not confirm all records valid",
    )

    records = report.get("records")

    require(
        isinstance(records, int)
        and not isinstance(records, bool)
        and records >= 1,
        "validation-report.json has an invalid records count",
    )

    latest = report.get("latest_record")

    require(
        isinstance(latest, dict),
        "validation-report.json latest_record is missing",
    )

    require(
        latest.get("run_id") == run_id,
        "validation-report.json RUN_ID does not match workflow RUN_ID",
    )

    try:
        with csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            reader = csv.DictReader(stream, strict=True)

            require(
                reader.fieldnames is not None,
                "benchmark CSV header is missing",
            )

            matching_rows = [
                row
                for row in reader
                if row.get("run_id") == run_id
            ]
    except (OSError, UnicodeError, csv.Error) as exc:
        raise VerificationError(
            f"cannot read canonical benchmark CSV: {exc}"
        ) from exc

    require(
        len(matching_rows) == 1,
        f"expected exactly one benchmark CSV row for RUN_ID={run_id}; "
        f"found {len(matching_rows)}",
    )

    row = matching_rows[0]

    try:
        csv_dimension = int(row["dimension"])
        csv_nnz = int(row["non_zero_count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise VerificationError(
            f"CSV dimension or non_zero_count is invalid: {exc}"
        ) from exc

    require(
        latest.get("dimension") == csv_dimension,
        "CSV/JSON dimension mismatch",
    )

    require(
        latest.get("nnz") == csv_nnz,
        "CSV/JSON non_zero_count mismatch",
    )

    comparisons = (
        ("speedup", "speedup"),
        ("sequential_mean_ms", "sequential_mean_ms"),
        ("parallel_mean_ms", "parallel_mean_ms"),
        ("max_error", "max_absolute_error"),
    )

    for report_key, csv_key in comparisons:
        left = finite_number(
            latest.get(report_key),
            f"JSON {report_key}",
        )

        right = finite_number(
            row.get(csv_key),
            f"CSV {csv_key}",
        )

        require(
            math.isclose(
                left,
                right,
                rel_tol=1e-8,
                abs_tol=1e-12,
            ),
            f"CSV/JSON mismatch for {csv_key}",
        )

    require(
        records == result.get("records"),
        "validation JSON record count differs from authoritative CSV validation",
    )

    run_directory = (
        root
        / "P3"
        / "results"
        / "raw"
        / run_id
    )

    for filename in REQUIRED_RUN_FILES:
        path = run_directory / filename

        require(
            path.is_file()
            and not path.is_symlink()
            and path.stat().st_size > 0,
            f"run-specific evidence is missing or empty: {filename}",
        )

    # Validate the run-specific checksum file created by run_benchmark.sh.
    run_checksums_path = run_directory / "SHA256SUMS.txt"

    try:
        checksum_lines = run_checksums_path.read_text(
            encoding="ascii"
        ).splitlines()
    except (OSError, UnicodeError) as exc:
        raise VerificationError(
            f"cannot read run-specific SHA256SUMS.txt: {exc}"
        ) from exc

    run_checksums: dict[str, str] = {}

    for number, line in enumerate(checksum_lines, start=1):
        match = re.fullmatch(
            r"([0-9a-f]{64})  ([^\r\n]+)",
            line,
        )

        require(
            match is not None,
            f"malformed run-specific checksum line {number}",
        )

        assert match is not None

        digest, relative = match.groups()

        require(
            relative not in run_checksums,
            f"duplicate run-specific checksum: {relative}",
        )

        run_checksums[relative] = digest

    expected_run_paths = {
        "benchmarks/benchmark_results_v2.csv",
        f"results/raw/{run_id}/benchmark-report.json",
        f"results/raw/{run_id}/benchmark-report.md",
        f"results/raw/{run_id}/benchmark-report.txt",
        f"results/raw/{run_id}/validation-report.json",
    }

    require(
        set(run_checksums) == expected_run_paths,
        "run-specific SHA256SUMS.txt does not contain the exact expected evidence set",
    )

    p3_root = root / "P3"

    for relative, expected_digest in run_checksums.items():
        path = p3_root / PurePosixPath(relative)

        require(
            path.is_file() and not path.is_symlink(),
            f"run checksum target is missing or unsafe: {relative}",
        )

        require(
            sha256_file(path) == expected_digest,
            f"run-specific SHA-256 mismatch: {relative}",
        )

    return {
        "run_id": run_id,
        "schema": "qflpn-benchmark-v2",
        "records": records,
        "dimension": csv_dimension,
        "non_zero_count": csv_nnz,
        "speedup": finite_number(row.get("speedup"), "CSV speedup"),
        "max_absolute_error": finite_number(
            row.get("max_absolute_error"),
            "CSV max_absolute_error",
        ),
    }


def verify_ci_outcomes(path: Path) -> dict[str, str]:
    outcomes = load_json(path, "CI outcomes JSON")

    for stage in REQUIRED_CI_STAGES:
        value = outcomes.get(stage)

        require(
            value == "success",
            f"mandatory CI stage {stage} did not succeed: {value!r}",
        )

    return {
        stage: str(outcomes[stage])
        for stage in REQUIRED_CI_STAGES
    }


def verify_package(
    root: Path,
    run_id: str,
    expected: dict[str, int],
    outcomes_path: Path,
) -> dict[str, Any]:
    root = Path(root).resolve()

    require(
        root.is_dir(),
        f"repository root does not exist: {root}",
    )

    # Check CI outcomes first. When an earlier workflow stage fails,
    # downstream stages may be skipped and benchmark artifacts may not
    # exist. Reporting the failed mandatory stage is more accurate than
    # misdiagnosing the resulting missing CSV/report as the root cause.
    outcomes = verify_ci_outcomes(outcomes_path)

    # With the mandatory CI chain successful, validate benchmark evidence
    # and then the complete package and its independently reconstructed
    # global integrity inventory.
    benchmark = verify_benchmark(
        root,
        run_id,
        expected,
    )

    verify_required_files(root)

    integrity = verify_global_integrity(root)

    return {
        "verdict": "P3_ACCEPTED",
        "integrity": integrity,
        "benchmark": benchmark,
        "ci_stages": outcomes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify the complete QFLPN P3 package."
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
            args.root,
            args.run_id,
            expected,
            args.outcomes_json,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "verdict": "P3_REJECTED",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                indent=2,
                allow_nan=False,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            indent=2,
            allow_nan=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
