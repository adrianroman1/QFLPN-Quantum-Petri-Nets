#!/usr/bin/env python3
"""Publish a structured, evidence-based QFLPN P3 GitHub Actions summary."""

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
    "P3/tools/compute_checksums.py",
    "P3/tools/verify_final_package.py",
    "P3/tools/write_github_summary.py",
    "P3/tests/test_compute_checksums.py",
    "P3/tests/test_verify_final_package.py",
    "P3/tests/test_write_github_summary.py",
    "P3/reports/environment.txt",
    "P3/MANIFEST.txt",
    "P3/SHA256SUMS.txt",
)


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object and reject malformed or non-object documents."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Cannot read verdict JSON: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid verdict JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise ValueError("Verdict JSON must contain a JSON object")

    return value


def evidence_status(root: Path) -> list[tuple[str, bool, int]]:
    """Return the presence and byte size of every mandatory evidence file."""
    result = []

    for relative in REQUIRED_EVIDENCE:
        path = root / relative
        present = path.is_file() and not path.is_symlink()
        size = path.stat().st_size if present else 0
        result.append((relative, present, size))

    return result


def format_ci_stages(value: Any) -> list[str]:
    """Render verifier CI stages without assuming their presence."""
    if not isinstance(value, dict):
        return [
            "| No CI-stage data supplied | **UNAVAILABLE** |",
        ]

    rows = []

    for name in sorted(value):
        status = value[name]
        normalized = str(status).strip().lower()

        if normalized == "success":
            rendered = "PASS"
        elif normalized:
            rendered = f"FAIL — `{status}`"
        else:
            rendered = "UNAVAILABLE"

        rows.append(f"| `{name}` | {rendered} |")

    return rows or ["| No CI stages recorded | **UNAVAILABLE** |"]


def format_environment(root: Path, maximum_lines: int = 60) -> list[str]:
    """Include a bounded environment excerpt when the file is available."""
    path = root / "P3/reports/environment.txt"

    if not path.is_file() or path.is_symlink():
        return [
            "**Environment report:** MISSING",
            "",
        ]

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return [
            f"**Environment report could not be read:** `{exc}`",
            "",
        ]

    selected = lines[:maximum_lines]
    output = [
        f"**Environment report:** PRESENT ({len(lines)} lines)",
        "",
        "```text",
        *selected,
    ]

    if len(lines) > maximum_lines:
        output.append(
            f"... {len(lines) - maximum_lines} additional lines "
            "remain in the evidence file."
        )

    output.extend(["```", ""])
    return output


def effective_verdict(
    declared_verdict: Any,
    missing_evidence: list[str],
) -> str:
    """Fail closed when the verifier verdict or mandatory evidence is invalid."""
    if declared_verdict != "P3_ACCEPTED":
        return "P3_REJECTED"

    if missing_evidence:
        return "P3_REJECTED"

    return "P3_ACCEPTED"


def build_summary(
    root: Path,
    verdict_path: Path,
    run_id: str,
) -> str:
    """Build the complete structured P3 validation summary."""
    root = root.resolve()
    verdict = load_json(verdict_path)

    evidence = evidence_status(root)
    missing = [
        name
        for name, present, _ in evidence
        if not present
    ]

    decision = effective_verdict(
        verdict.get("verdict", "P3_REJECTED"),
        missing,
    )

    integrity = verdict.get("integrity", {})
    benchmark = verdict.get("benchmark", {})
    ci_stages = verdict.get("ci_stages", {})

    if not isinstance(integrity, dict):
        integrity = {}

    if not isinstance(benchmark, dict):
        benchmark = {}

    output = [
        "# QFLPN P3 — FINAL VALIDATION SUMMARY",
        "",
        f"- Final verdict: **{decision}**",
        f"- Benchmark RUN_ID: `{run_id}`",
        f"- Repository root: `{root}`",
        "",
        "## 1. Independent integrity verification",
        "",
        f"- MANIFEST entries: "
        f"`{integrity.get('manifest_entries', 'UNAVAILABLE')}`",
        f"- SHA-256 entries verified: "
        f"`{integrity.get('sha256_entries_verified', 'UNAVAILABLE')}`",
        "",
        "## 2. Benchmark evidence",
        "",
        f"- Schema: `{benchmark.get('schema', 'UNAVAILABLE')}`",
        f"- RUN_ID: `{benchmark.get('run_id', 'UNAVAILABLE')}`",
        f"- Validation: `{benchmark.get('validation', 'UNAVAILABLE')}`",
        f"- Records: `{benchmark.get('records', 'UNAVAILABLE')}`",
        f"- Dimension: `{benchmark.get('dimension', 'UNAVAILABLE')}`",
        "",
        "## 3. Mandatory CI stages",
        "",
        "| Stage | Result |",
        "|---|---|",
        *format_ci_stages(ci_stages),
        "",
        "## 4. Mandatory evidence inventory",
        "",
        "| File | Status | Bytes |",
        "|---|---:|---:|",
    ]

    for name, present, size in evidence:
        status = "PRESENT" if present else "MISSING"
        output.append(
            f"| `{name}` | **{status}** | {size} |"
        )

    output.extend([
        "",
        f"- Mandatory files present: "
        f"**{len(evidence) - len(missing)}/{len(evidence)}**",
        f"- Mandatory files missing: **{len(missing)}**",
        "",
    ])

    if missing:
        output.extend([
            "**Missing mandatory evidence:**",
            "",
            *[f"- `{name}`" for name in missing],
            "",
        ])

    output.extend([
        "## 5. Execution environment",
        "",
        *format_environment(root),
        "## 6. Integrity publication",
        "",
        "- Complete `MANIFEST.txt` publication: handled by the "
        "dedicated workflow step.",
        "- Complete `SHA256SUMS.txt` publication: handled by the "
        "dedicated workflow step.",
        "- Original integrity files remain available in the P3 "
        "validation artifact.",
        "",
        "## 7. Final decision",
        "",
    ])

    if decision == "P3_ACCEPTED":
        output.extend([
            "**P3_ACCEPTED** — the independent verifier accepted "
            "the package and all mandatory evidence files are present.",
            "",
        ])
    else:
        output.extend([
            "**P3_REJECTED / INCOMPLETE EVIDENCE** — the package "
            "must not be treated as accepted.",
            "",
        ])

    if verdict.get("error"):
        output.extend([
            "### Verification error",
            "",
            "```text",
            str(verdict["error"]),
            "```",
            "",
        ])

    return "\n".join(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Publish a structured P3 GitHub Actions validation summary."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory.",
    )
    parser.add_argument(
        "--verdict-json",
        type=Path,
        required=True,
        help="JSON output produced by verify_final_package.py.",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Exact P3 benchmark RUN_ID.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Summary destination; defaults to GITHUB_STEP_SUMMARY.",
    )

    args = parser.parse_args()

    output_path = args.output

    if output_path is None:
        summary_environment = os.environ.get("GITHUB_STEP_SUMMARY")

        if not summary_environment:
            print(
                "P3_SUMMARY_ERROR: GITHUB_STEP_SUMMARY is not set",
                file=sys.stderr,
            )
            return 2

        output_path = Path(summary_environment)

    try:
        summary = build_summary(
            args.root,
            args.verdict_json,
            args.run_id,
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as stream:
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
