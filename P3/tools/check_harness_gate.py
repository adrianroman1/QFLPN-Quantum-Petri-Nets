#!/usr/bin/env python3
"""Blocking gate for a P3 harness run directory (standard library only).

Used by the p3_validation workflow. It fails (exit status 1) when:
  - the build failed (BUILD_FAILED.txt) or harness_verdict.json is missing;
  - a MANDATORY criterion is not PASS:
        C0 input present and valid, C1 >= 30 samples,
        C2 bitwise identical to sequential,
        C7 skips documented, C8 declared configurations complete;
  - SHA256SUMS.txt is missing, malformed, incomplete or does not match.

Performance criteria (C3, C4, C5, C6) are reported as GitHub warnings but do
not block: shared CI runners are too noisy for performance gating. Final
performance verdicts must come from a dedicated multi-core machine.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

MANDATORY = (
    "C0_INPUT_DATA_PRESENT_AND_VALID",
    "C1_SAMPLES_AT_LEAST_30",
    "C2_BITWISE_IDENTICAL_TO_SEQUENTIAL",
    "C7_SKIPS_AND_PREFLIGHT_DOCUMENTED",
    "C8_DECLARED_CONFIGURATIONS_COMPLETE",
)
INFORMATIONAL = (
    "C3_OVERHEAD_AT_P1_AT_MOST_5_PERCENT",
    "C4_SPEEDUP_GT_1_AT_P2_N_GE_10M",
    "C5_NO_SIGNIFICANT_REGRESSION_AT_N_GE_1M",
    "C6_BANDWIDTH_CEILING_RECORDED",
)
REQUIRED_FILES = (
    "harness_raw_iterations.csv", "harness_forks.csv", "harness_summary.csv",
    "harness_report.md", "harness_report.txt", "harness_verdict.json",
    "environment.json", "MANIFEST.txt", "SHA256SUMS.txt",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_checksums(run_dir: Path) -> list[str]:
    errors: list[str] = []
    sums = run_dir / "SHA256SUMS.txt"

    if not sums.is_file():
        return ["SHA256SUMS.txt is missing"]

    listed: dict[str, str] = {}

    for number, line in enumerate(sums.read_text("utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)

        if match is None:
            errors.append(f"SHA256SUMS.txt line {number} is malformed")
            continue

        digest, name = match.groups()

        if name in listed:
            errors.append(f"duplicate checksum entry: {name}")

        if "/" in name or name.startswith(".."):
            errors.append(f"checksum entry escapes the run directory: {name}")
            continue

        listed[name] = digest

    present = {p.name for p in run_dir.iterdir()
               if p.is_file() and p.name != "SHA256SUMS.txt"}

    for name in sorted(present - set(listed)):
        errors.append(f"file not covered by SHA256SUMS.txt: {name}")

    for name, digest in sorted(listed.items()):
        target = run_dir / name

        if not target.is_file():
            errors.append(f"listed file is missing: {name}")
        elif sha256_file(target) != digest:
            errors.append(f"SHA-256 mismatch: {name}")

    return errors


def gate(run_dir: Path) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if (run_dir / "BUILD_FAILED.txt").exists():
        errors.append("BUILD_FAILED.txt present: the Java build failed")

    for name in REQUIRED_FILES:
        if not (run_dir / name).is_file():
            errors.append(f"required artifact missing: {name}")

    verdict_path = run_dir / "harness_verdict.json"
    if verdict_path.is_file():
        try:
            verdict = json.loads(verdict_path.read_text("utf-8"))
            status = {c["id"]: c["status"] for c in verdict["criteria"]}
        except (ValueError, KeyError, TypeError):
            errors.append("harness_verdict.json is unreadable")
            status = {}

        for criterion in MANDATORY:
            if status.get(criterion) != "PASS":
                errors.append(
                    f"{criterion} is {status.get(criterion, 'absent')}, "
                    "not PASS")

        for criterion in INFORMATIONAL:
            if status.get(criterion) == "FAIL":
                warnings.append(
                    f"{criterion} is FAIL (informational on shared runners)")

    if (run_dir / "SHA256SUMS.txt").is_file() or not errors:
        errors.extend(check_checksums(run_dir))

    return (not errors), errors, warnings


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    if len(args) != 1:
        print("usage: check_harness_gate.py <harness run dir>",
              file=sys.stderr)
        return 2

    run_dir = Path(args[0])

    if not run_dir.is_dir():
        print(f"::error::harness run directory not found: {run_dir}")
        return 1

    ok, errors, warnings = gate(run_dir)

    for warning in warnings:
        print(f"::warning::{warning}")

    for error in errors:
        print(f"::error::{error}")

    print("P3_HARNESS_GATE: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
