#!/usr/bin/env python3
"""Publish the P3 verdict only when local and remote evidence both pass."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
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
    "P3/tools/write_github_summary.py",
    "P3/tools/compute_checksums.py",
    "P3/tools/verify_final_package.py",
    "P3/tests/test_record_environment.py",
    "P3/tests/test_verify_remote_integrity.py",
    "P3/tests/test_generate_benchmark_summary.py",
    "P3/tests/test_write_github_summary.py",
    "P3/reports/environment.json",
    "P3/reports/environment.txt",
    "P3/reports/benchmark-report.md",
    "P3/reports/validation-report.json",
    "P3/benchmarks/benchmark_results_v2.csv",
    "P3/MANIFEST.txt",
    "P3/SHA256SUMS.txt",
)


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


def verify_remote_result(
    remote: dict[str, Any],
    *,
    expected_branch: str,
) -> tuple[bool, str]:
    if remote.get("schema") != "qflpn-p3-remote-integrity-v1":
        return False, "Remote verification schema mismatch"

    if remote.get("validation") != "PASS":
        return False, "Remote integrity validation is not PASS"

    if remote.get("branch") != expected_branch:
        return False, "Remote verification branch mismatch"

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
    for item in files:
        if not isinstance(item, dict):
            return False, "Remote file result is malformed"
        path = item.get("path")
        digest = item.get("sha256")
        if (
            not isinstance(path, str)
            or not path.startswith("P3/")
            or item.get("status") != "PASS"
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
            or path in seen
        ):
            return False, "Remote per-file verification contains invalid data"
        seen.add(path)

    return True, "All remote manifest blobs were verified"


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
) -> str:
    root = root.resolve()
    verdict = load_json(verdict_path, "local final verdict")
    remote = load_json(remote_path, "remote integrity report")

    evidence = evidence_status(root)
    missing = [name for name, present, _ in evidence if not present]

    remote_ok, remote_reason = verify_remote_result(
        remote,
        expected_branch=branch,
    )

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

    decision = effective_verdict(
        verdict.get("verdict"),
        missing,
        remote_ok,
        benchmark.get("run_id"),
        run_id,
    )

    integrity = verdict.get("integrity")
    if not isinstance(integrity, dict):
        integrity = {}

    stages = verdict.get("ci_stages")
    if not isinstance(stages, dict):
        stages = {}

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
        f"- Remote result: **{'PASS' if remote_ok else 'FAIL'}**",
        f"- Detail: {remote_reason}",
        "",
        "## 3. Benchmark evidence",
        "",
        f"- Schema: `{benchmark.get('schema', 'UNAVAILABLE')}`",
        f"- RUN_ID: `{benchmark.get('run_id', 'UNAVAILABLE')}`",
        f"- Validation: `{benchmark.get('validation', 'UNAVAILABLE')}`",
        f"- Records: `{benchmark.get('records', 'UNAVAILABLE')}`",
        f"- Dimension: `{benchmark.get('dimension', 'UNAVAILABLE')}`",
        f"- Non-zero count: `{benchmark.get('non_zero_count', 'UNAVAILABLE')}`",
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
        "",
        "## 6. Final decision",
        "",
    ])

    if decision == "P3_ACCEPTED":
        output.extend([
            "**P3_ACCEPTED** — local package checks, benchmark evidence, "
            "mandatory files and every remote manifest blob passed.",
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
