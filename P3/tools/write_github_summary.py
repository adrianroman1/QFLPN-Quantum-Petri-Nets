#!/usr/bin/env python3
"""Publish the P3 verdict only when local and remote evidence both pass."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


REQUIRED_EVIDENCE = (
    "P3/pom.xml",
    "P3/ACCEPTANCE_CHECKLIST.md",
    "P3/ACCEPTANCE_REPORT.md",
    "P3/INTEGRITY.md",
    "P3/P3_AUDIT_REPORT.md",
    "P3/VALIDATION_ALIGNMENT.md",
    "P3/VALIDATION_PROTOCOL.md",
    "P3/results/run_benchmark.sh",
    "P3/results/validate_benchmark.py",
    "P3/results/test_validate_benchmark.py",
    "P3/results/generate_benchmark_summary.py",
    "P3/tools/record_environment.py",
    "P3/tools/verify_remote_integrity.py",
    "P3/tools/verify_evidence_consistency.py",
    "P3/tools/write_github_summary.py",
    "P3/tools/compute_checksums.py",
    "P3/tools/verify_final_package.py",
    "P3/tests/test_record_environment.py",
    "P3/tests/test_verify_remote_integrity.py",
    "P3/tests/test_verify_evidence_consistency.py",
    "P3/tests/test_generate_benchmark_summary.py",
    "P3/tests/test_write_github_summary.py",
    "P3/reports/environment.json",
    "P3/reports/environment.txt",
    "P3/reports/benchmark-report.md",
    "P3/reports/validation-report.json",
    "P3/reports/evidence-consistency.json",
    "P3/benchmarks/benchmark_results_v2.csv",
    "P3/MANIFEST.txt",
    "P3/SHA256SUMS.txt",
)

HEX64 = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
REMOTE_SCHEMA = "qflpn-p3-remote-integrity-v2"
EVIDENCE_SCHEMA = "qflpn-p3-evidence-consistency-v1"


def load_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} is missing or unsafe: {path}")

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {label}: {exc}") from exc

    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")

    return value


def evidence_status(root: Path) -> list[tuple[str, bool, int]]:
    result = []

    for relative in REQUIRED_EVIDENCE:
        path = root / relative
        present = path.is_file() and not path.is_symlink()
        size = path.stat().st_size if present else 0
        result.append((relative, present, size))

    return result


def verify_environment(root: Path, run_id: str) -> None:
    data = load_json(
        root / "P3/reports/environment.json",
        "environment JSON",
    )

    if data.get("schema") != "qflpn-p3-environment-v1":
        raise ValueError("Environment JSON schema mismatch")

    if data.get("run_id") != run_id:
        raise ValueError("Environment JSON RUN_ID mismatch")

    text_path = root / "P3/reports/environment.txt"

    if text_path.is_symlink() or not text_path.is_file():
        raise ValueError("Environment TXT is missing or unsafe")

    content = text_path.read_text(encoding="utf-8")

    if f"RUN_ID: {run_id}" not in content:
        raise ValueError("Environment TXT RUN_ID mismatch")


def verify_evidence_consistency(root: Path, run_id: str) -> None:
    data = load_json(
        root / "P3/reports/evidence-consistency.json",
        "evidence consistency JSON",
    )

    if data.get("schema") != EVIDENCE_SCHEMA:
        raise ValueError("Evidence consistency schema mismatch")

    if data.get("validation") != "PASS":
        raise ValueError("Evidence consistency validation is not PASS")

    if data.get("run_id") != run_id:
        raise ValueError("Evidence consistency RUN_ID mismatch")

    source_commit = data.get("source_commit")
    if not isinstance(source_commit, str) or not re.fullmatch(
        r"[0-9a-f]{40}", source_commit
    ):
        raise ValueError("Evidence consistency SOURCE_COMMIT is invalid")

    evidence = data.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("Evidence consistency evidence inventory is invalid")

    required_keys = {
        "environment",
        "csv",
        "validation_json",
        "java_benchmark_json",
        "java_benchmark_txt",
        "run_markdown",
        "persistent_markdown",
        "persistent_validation_json",
        "run_checksums",
    }

    if set(evidence) != required_keys:
        raise ValueError("Evidence consistency inventory keys mismatch")

    for key in sorted(required_keys):
        item = evidence[key]
        if not isinstance(item, dict) or item.get("status") != "PASS":
            raise ValueError(
                f"Evidence consistency item is not PASS: {key}"
            )


def safe_manifest_path(value: str) -> bool:
    if not value or "\\" in value:
        return False

    path = PurePosixPath(value)

    return (
        not path.is_absolute()
        and ".." not in path.parts
        and path.as_posix() == value
        and value.startswith("P3/")
        and value.strip() == value
        and path.name not in {"MANIFEST.txt", "SHA256SUMS.txt"}
    )


def load_local_integrity_inventory(
    root: Path,
) -> tuple[list[str], dict[str, str]]:
    manifest_path = root / "P3/MANIFEST.txt"
    checksums_path = root / "P3/SHA256SUMS.txt"

    if (
        manifest_path.is_symlink()
        or not manifest_path.is_file()
        or checksums_path.is_symlink()
        or not checksums_path.is_file()
    ):
        raise ValueError("Global MANIFEST.txt or SHA256SUMS.txt is missing or unsafe")

    try:
        manifest_content = manifest_path.read_text(encoding="utf-8")
        checksum_content = checksums_path.read_text(encoding="ascii")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Cannot read local integrity inventory: {exc}") from exc

    if not manifest_content.endswith("\n"):
        raise ValueError("MANIFEST.txt lacks its final newline")

    manifest = manifest_content.splitlines()

    if not manifest or any(not item for item in manifest):
        raise ValueError("MANIFEST.txt is empty or contains blank entries")

    if manifest != sorted(manifest):
        raise ValueError("MANIFEST.txt entries are not sorted")

    if len(manifest) != len(set(manifest)):
        raise ValueError("MANIFEST.txt contains duplicate paths")

    for relative in manifest:
        if not safe_manifest_path(relative):
            raise ValueError(f"Unsafe MANIFEST.txt path: {relative!r}")

    if not checksum_content.endswith("\n"):
        raise ValueError("SHA256SUMS.txt lacks its final newline")

    checksums: dict[str, str] = {}

    for number, line in enumerate(checksum_content.splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)

        if match is None:
            raise ValueError(f"Malformed SHA256SUMS.txt line {number}")

        digest, relative = match.groups()

        if not safe_manifest_path(relative):
            raise ValueError(
                f"Unsafe SHA256SUMS.txt path on line {number}: {relative!r}"
            )

        if relative in checksums:
            raise ValueError(f"Duplicate SHA256SUMS.txt path: {relative}")

        checksums[relative] = digest

    if list(checksums) != sorted(checksums):
        raise ValueError("SHA256SUMS.txt entries are not sorted")

    if set(manifest) != set(checksums):
        missing = sorted(set(manifest) - set(checksums))
        extra = sorted(set(checksums) - set(manifest))
        raise ValueError(
            "MANIFEST.txt and SHA256SUMS.txt path sets differ; "
            f"missing_checksums={missing}; extra_checksums={extra}"
        )

    return manifest, checksums


def verify_remote_result(
    remote: dict[str, Any],
    *,
    expected_branch: str,
    expected_manifest: list[str] | None = None,
    expected_checksums: dict[str, str] | None = None,
    expected_run_id: str | None = None,
) -> tuple[bool, str]:
    if remote.get("schema") != REMOTE_SCHEMA:
        return False, "Remote verification schema mismatch"

    if remote.get("validation") != "PASS":
        return False, "Remote integrity validation is not PASS"

    if remote.get("branch") != expected_branch:
        return False, "Remote verification branch mismatch"

    if expected_run_id is not None and remote.get("run_id") != expected_run_id:
        return False, "Remote verification RUN_ID mismatch"

    commit = remote.get("commit")

    if not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None:
        return False, "Remote commit identifier is missing or malformed"

    count = remote.get("manifest_entries")
    verified = remote.get("verified_remote_blobs")

    if (
        not isinstance(count, int)
        or isinstance(count, bool)
        or count <= 0
        or not isinstance(verified, int)
        or isinstance(verified, bool)
        or verified != count
    ):
        return False, "Remote blob count does not match manifest count"

    files = remote.get("files")

    if not isinstance(files, list) or len(files) != count:
        return False, "Remote per-file verification list is incomplete"

    seen: set[str] = set()
    remote_checksums: dict[str, str] = {}

    for item in files:
        if not isinstance(item, dict):
            return False, "Remote file result is malformed"

        path = item.get("path")
        digest = item.get("sha256")

        if (
            not isinstance(path, str)
            or not safe_manifest_path(path)
            or item.get("status") != "PASS"
            or not isinstance(digest, str)
            or HEX64.fullmatch(digest) is None
            or path in seen
        ):
            return False, "Remote per-file verification contains invalid data"

        seen.add(path)
        remote_checksums[path] = digest

    if expected_manifest is not None:
        if seen != set(expected_manifest):
            missing = sorted(set(expected_manifest) - seen)
            extra = sorted(seen - set(expected_manifest))
            return (
                False,
                "Remote file list differs from local MANIFEST.txt; "
                f"missing={missing}; extra={extra}",
            )

    if expected_checksums is not None:
        if remote_checksums != expected_checksums:
            mismatches = sorted(
                path
                for path in set(remote_checksums) & set(expected_checksums)
                if remote_checksums[path] != expected_checksums[path]
            )
            missing = sorted(set(expected_checksums) - set(remote_checksums))
            extra = sorted(set(remote_checksums) - set(expected_checksums))

            return (
                False,
                "Remote SHA-256 inventory differs from local SHA256SUMS.txt; "
                f"mismatches={mismatches}; missing={missing}; extra={extra}",
            )

    return True, "All remote manifest paths and SHA-256 values match local integrity inventory"


def effective_verdict(
    local_verdict: Any,
    missing_evidence: list[str],
    remote_ok: bool,
    benchmark_run_id: Any,
    expected_run_id: str,
) -> str:
    if local_verdict != "P3_ACCEPTED":
        return "P3_REJECTED"

    if missing_evidence or not remote_ok:
        return "P3_REJECTED"

    if benchmark_run_id != expected_run_id:
        return "P3_REJECTED"

    return "P3_ACCEPTED"


def build_summary(
    root: Path,
    verdict_path: Path,
    remote_path: Path,
    run_id: str,
    branch: str,
    *,
    remote_required: bool = True,
) -> str:
    root = root.resolve()
    verdict = load_json(verdict_path, "local final verdict")
    remote = load_json(remote_path, "remote integrity report")

    evidence = evidence_status(root)
    missing = [name for name, present, _ in evidence if not present]

    benchmark = verdict.get("benchmark")
    if not isinstance(benchmark, dict):
        benchmark = {}

    try:
        verify_environment(root, run_id)
        environment_ok = True
    except (OSError, ValueError):
        environment_ok = False

    if not environment_ok:
        missing.append("P3/reports/environment.json or RUN_ID binding")

    try:
        verify_evidence_consistency(root, run_id)
        evidence_consistency_ok = True
    except (OSError, ValueError, TypeError):
        evidence_consistency_ok = False

    if not evidence_consistency_ok:
        missing.append("P3/reports/evidence-consistency.json or evidence binding")

    try:
        expected_manifest, expected_checksums = (
            load_local_integrity_inventory(root)
        )
        local_inventory_ok = True
    except (OSError, ValueError) as exc:
        expected_manifest = None
        expected_checksums = None
        local_inventory_ok = False
        missing.append(f"Local integrity inventory: {exc}")

    if remote_required:
        if local_inventory_ok:
            remote_ok, remote_reason = verify_remote_result(
                remote,
                expected_branch=branch,
                expected_manifest=expected_manifest,
                expected_checksums=expected_checksums,
                expected_run_id=run_id,
            )
        else:
            remote_ok = False
            remote_reason = "Remote comparison blocked by invalid local integrity inventory"

        decision = effective_verdict(
            verdict.get("verdict"),
            missing,
            remote_ok,
            benchmark.get("run_id"),
            run_id,
        )
    else:
        remote_ok = False
        remote_reason = (
            "Remote publication is not applicable to pull requests; "
            "local validation is reported separately"
        )

        local_ok = (
            verdict.get("verdict") == "P3_ACCEPTED"
            and not missing
            and benchmark.get("run_id") == run_id
            and local_inventory_ok
        )

        decision = (
            "P3_VALIDATED_PENDING_PUBLICATION"
            if local_ok
            else "P3_REJECTED"
        )

        if remote.get("schema") != REMOTE_SCHEMA:
            remote_reason = "Remote report schema is invalid"
            decision = "P3_REJECTED"
        elif remote.get("validation") != "NOT_APPLICABLE":
            remote_reason = "Pull request remote status must be NOT_APPLICABLE"
            decision = "P3_REJECTED"

    integrity = verdict.get("integrity")
    if not isinstance(integrity, dict):
        integrity = {}

    stages = verdict.get("ci_stages")
    if not isinstance(stages, dict):
        stages = {}

    benchmark_validation = (
        "PASS (independent final verifier)"
        if verdict.get("verdict") == "P3_ACCEPTED"
        and benchmark.get("schema") == "qflpn-benchmark-v2"
        and benchmark.get("run_id") == run_id
        else "UNAVAILABLE"
    )

    output = [
        "# QFLPN P3 — FINAL VALIDATION SUMMARY",
        "",
        f"- Final verdict: **{decision}**",
        f"- Benchmark RUN_ID: `{run_id}`",
        f"- Repository branch checked remotely: `{branch}`",
        "",
        "## 1. Local package verification",
        "",
        f"- Local verifier verdict: `{verdict.get('verdict', 'UNAVAILABLE')}`",
        f"- MANIFEST entries: `{integrity.get('manifest_entries', 'UNAVAILABLE')}`",
        f"- SHA-256 entries verified locally: "
        f"`{integrity.get('sha256_entries_verified', 'UNAVAILABLE')}`",
        "",
        "## 2. Remote repository verification",
        "",
        f"- Remote validation: `{remote.get('validation', 'UNAVAILABLE')}`",
        f"- Remote commit: `{remote.get('commit', 'UNAVAILABLE')}`",
        f"- Manifest entries: `{remote.get('manifest_entries', 'UNAVAILABLE')}`",
        f"- Remote blobs verified: "
        f"`{remote.get('verified_remote_blobs', 'UNAVAILABLE')}`",
        f"- Remote result: **{'PASS' if remote_ok else ('NOT APPLICABLE' if not remote_required else 'FAIL')}**",
        f"- Detail: {remote_reason}",
        "",
        "## 3. Benchmark evidence",
        "",
        f"- Schema: `{benchmark.get('schema', 'UNAVAILABLE')}`",
        f"- RUN_ID: `{benchmark.get('run_id', 'UNAVAILABLE')}`",
        f"- Validation: `{benchmark_validation}`",
        f"- Records: `{benchmark.get('records', 'UNAVAILABLE')}`",
        f"- Dimension: `{benchmark.get('dimension', 'UNAVAILABLE')}`",
        f"- Non-zero count: `{benchmark.get('non_zero_count', 'UNAVAILABLE')}`",
        f"- Speedup: `{benchmark.get('speedup', 'UNAVAILABLE')}`",
        f"- Maximum absolute error: `{benchmark.get('max_absolute_error', 'UNAVAILABLE')}`",
        "",
        "## 4. CI stages",
        "",
        "| Stage | Result |",
        "|---|---|",
    ]

    for name in sorted(stages):
        status = stages[name]
        output.append(
            f"| `{name}` | "
            f"{'PASS' if status == 'success' else f'FAIL — `{status}`'} |"
        )

    output.extend([
        "",
        "## 5. Mandatory evidence inventory",
        "",
        "| File | Status | Bytes |",
        "|---|---:|---:|",
    ])

    for name, present, size in evidence:
        output.append(
            f"| `{name}` | {'PRESENT' if present else '**MISSING**'} | {size} |"
        )

    output.extend([
        "",
        f"- Mandatory evidence files present: "
        f"**{len(evidence) - len([x for x in evidence if not x[1]])}/{len(evidence)}**",
        f"- Environment RUN_ID binding: **{'PASS' if environment_ok else 'FAIL'}**",
        f"- Evidence consistency: **{'PASS' if evidence_consistency_ok else 'FAIL'}**",
        f"- Local MANIFEST/SHA256SUMS consistency: **{'PASS' if local_inventory_ok else 'FAIL'}**",
        "",
        "## 6. Final decision",
        "",
    ])

    if decision == "P3_ACCEPTED":
        output.extend([
            "**P3_ACCEPTED** — local package checks, benchmark evidence, "
            "mandatory files and every remote manifest path and SHA-256 value passed.",
            "",
        ])
    elif decision == "P3_VALIDATED_PENDING_PUBLICATION":
        output.extend([
            "**P3_VALIDATED_PENDING_PUBLICATION** — local validation passed. "
            "Remote persistence and remote integrity must be verified by a branch workflow "
            "before P3_ACCEPTED can be granted.",
            "",
        ])
    else:
        output.extend([
            "**P3_REJECTED** — acceptance is not granted. At least one "
            "required local, benchmark, environment or remote condition failed.",
            "",
        ])

    if missing:
        output.extend(["### Missing or invalid evidence", ""])
        output.extend(f"- `{item}`" for item in missing)
        output.append("")

    if verdict.get("error"):
        output.extend([
            "### Local verification error",
            "",
            "```text",
            str(verdict["error"]),
            "```",
            "",
        ])

    return "\n".join(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish the evidence-bound P3 final GitHub summary."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--verdict-json", type=Path, required=True)
    parser.add_argument("--remote-integrity-json", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument(
        "--remote-not-required",
        action="store_true",
        help="Use a pending-publication verdict for pull requests.",
    )
    parser.add_argument("--output", type=Path)

    args = parser.parse_args()
    output_path = args.output

    if output_path is None:
        target = os.environ.get("GITHUB_STEP_SUMMARY")
        if not target:
            print(
                "P3_SUMMARY_ERROR: GITHUB_STEP_SUMMARY is not set",
                file=sys.stderr,
            )
            return 2
        output_path = Path(target)

    try:
        summary = build_summary(
            args.root,
            args.verdict_json,
            args.remote_integrity_json,
            args.run_id,
            args.branch,
            remote_required=not args.remote_not_required,
        )

        if output_path.is_symlink():
            raise ValueError("Summary output must not be a symlink")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(summary)
            stream.write("\n")

    except (OSError, ValueError, TypeError) as exc:
        print(
            f"P3_SUMMARY_ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    print("P3_GITHUB_SUMMARY_PUBLISHED")
    print(f"P3_SUMMARY_OUTPUT={output_path}")
    print(f"P3_SUMMARY_RUN_ID={args.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
