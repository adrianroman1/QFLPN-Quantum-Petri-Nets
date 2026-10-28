#!/usr/bin/env python3
"""Generate Results.generated.md and article tables from artifacts only.

Every number written by this tool is read from a CSV artifact and is
printed together with the run_id that produced it. Nothing is typed by hand.

Outputs (standard library only):
    <harness run dir>/Results.generated.md
    <harness run dir>/article_tables.md
    <harness run dir>/article_tables.tex
    P3/results/Results.generated.md        (latest copy)

The hand-written P3/results/Results.md is NEVER modified unless the caller
passes --write-results-md explicitly.

Evidence levels used by the project:
    Measured            >= 30 samples per configuration in a harness run
    Scalable            planned size, not measured yet
    Resource Envelope   memory model only, never timed (70M, 100M)
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

DECLARED_SIZES = [1_000_000, 2_000_000, 7_000_000, 10_000_000,
                  30_000_000, 70_000_000, 100_000_000]
ENVELOPE_ONLY = {70_000_000, 100_000_000}
INT_ARRAY_LIMIT = 2**31 - 1 - 8
SLACK_BYTES = 64 * 1024 * 1024
SMALL_DIMENSION_WARNING = 100_000
MIN_SAMPLES = 30


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def num(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return ""


def gib(value: float) -> str:
    return f"{value / 2**30:.2f}"


def envelope_rows(sizes: list[int]) -> list[dict[str, Any]]:
    rows = []
    for n in sizes:
        nnz = 2 * n
        csr = 12 * nnz + 4 * (n + 1)
        peak = 2 * csr + 24 * n + SLACK_BYTES
        rows.append({
            "n": n,
            "nnz": nnz,
            "csr_bytes": csr,
            "model_peak_bytes": peak,
            "min_heap_bytes": int(peak / 0.85),
            "fits_int_array": nnz <= INT_ARRAY_LIMIT,
        })
    return rows


def evidence_levels(summary: list[dict[str, str]]) -> list[dict[str, str]]:
    measured: dict[int, set[str]] = defaultdict(set)
    for row in summary:
        if row["strategy"] != "SEQ" and int(row["samples"]) >= MIN_SAMPLES:
            measured[int(row["n"])].add(row["run_id"])

    levels = []
    for n in DECLARED_SIZES:
        if n in ENVELOPE_ONLY:
            level = "Resource Envelope"
            detail = "memory model only; never timed"
        elif n in measured:
            level = "Measured"
            detail = ", ".join(sorted(measured[n]))
        elif n == 30_000_000:
            level = "Scalable"
            detail = "planned; no measured artifact yet"
        else:
            level = "Not measured yet"
            detail = "no harness artifact with >= 30 samples"
        levels.append({"n": str(n), "level": level, "detail": detail})
    return levels


def v2_history(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    history = []
    for row in rows:
        try:
            history.append({
                "run_id": row.get("run_id", ""),
                "timestamp": row.get("timestamp", ""),
                "dimension": row.get("dimension", ""),
                "sequential_median_ms": row["sequential_median_ms"],
                "parallel_median_ms": row["parallel_median_ms"],
                "speedup": row["speedup"],
            })
        except KeyError:
            continue
    return history


def v3_notice(rows: list[dict[str, str]]) -> tuple[str, list[str]]:
    if not rows:
        return "No V3 artifact found.", []
    dims = sorted({int(r["dimension"]) for r in rows if r.get("dimension")})
    speedups = [float(r["speedup"]) for r in rows if r.get("speedup")]
    verdicts: dict[str, int] = defaultdict(int)
    for r in rows:
        verdicts[r.get("verdict", "")] += 1
    runs = sorted({r.get("run_id", "") for r in rows})
    summary = (
        f"V3 artifact: {len(rows)} rows, {len(runs)} run_id(s) "
        f"({', '.join(runs)}); dimension(s): {dims}; "
        f"median speedup {statistics.median(speedups):.3f}; "
        f"verdicts: {dict(verdicts)}."
    )
    warnings = []
    if dims and max(dims) < SMALL_DIMENSION_WARNING:
        warnings.append(
            f"V3 was run at dimension {max(dims)} only. At this size the "
            "sequential kernel takes microseconds, so task dispatch "
            "dominates and the speedup column measures overhead, not "
            "scaling. V3 must not be used for performance claims; use the "
            "harness (N >= 1M) instead."
        )
    return summary, warnings


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def render_results(
    run_dir: Path,
    summary: list[dict[str, str]],
    verdict_text: str,
    v2: list[dict[str, str]],
    v3_summary: str,
    v3_warnings: list[str],
) -> str:
    run_ids = sorted({r["run_id"] for r in summary})
    out = [
        "# P3 results (generated)",
        "",
        "> Generated from artifacts by `P3/tools/generate_results_md.py`. "
        "Do not edit by hand. Every number carries its `run_id`.",
        "",
        f"- harness run(s): {', '.join(f'`{r}`' for r in run_ids) or 'none'}",
        f"- harness directory: `{run_dir.name}`",
        f"- harness verdict: **{verdict_text}**",
        "",
        "## Evidence levels",
        "",
        "| N | Level | Source run_id / note |",
        "|---:|---|---|",
    ]
    for row in evidence_levels(summary):
        out.append(f"| {row['n']} | {row['level']} | {row['detail']} |")

    out += ["", "## Harness results (N >= 1M, fork-based, raw data published)",
            "",
            "| run_id | workload | N | strategy | p | samples | median ms "
            "| CI95 | speedup | speedup CI95 | efficiency | bit exact |",
            "|---|---|---:|---|---:|---:|---:|---|---:|---|---:|---|"]
    for r in summary:
        out.append(
            f"| {r['run_id']} | {r['workload']} | {r['n']} | {r['strategy']} "
            f"| {r['parallelism']} | {r['samples']} | {num(r['median_ms'])} "
            f"| [{num(r['median_ci_low_ms'])}, {num(r['median_ci_high_ms'])}] "
            f"| {num(r['speedup_vs_seq'])} "
            f"| [{num(r['speedup_ci_low'])}, {num(r['speedup_ci_high'])}] "
            f"| {num(r['efficiency'])} | {r.get('bit_exact', '')} |")
    if not summary:
        out.append("| (no harness data) | | | | | | | | | | | |")

    out += ["", "## CI history of the V2 benchmark (N = 1M)", "",
            "| run_id | timestamp | N | sequential median ms "
            "| parallel median ms | speedup |",
            "|---|---|---:|---:|---:|---:|"]
    for h in v2:
        out.append(
            f"| {h['run_id']} | {h['timestamp']} | {h['dimension']} "
            f"| {num(h['sequential_median_ms'])} "
            f"| {num(h['parallel_median_ms'])} | {num(h['speedup'])} |")
    if not v2:
        out.append("| (no V2 data) | | | | | |")

    out += ["", "## V3 sensitivity matrix", "", v3_summary, ""]
    for warning in v3_warnings:
        out += [f"> **Warning:** {warning}", ""]

    out += ["## Resource envelope (model only, never timed)", "",
            "Workload UNIFORM_2 (2 stored entries per row). Peak model = "
            "2 x CSR payload + 24 B per row (x, y, reference) + 64 MiB.",
            "",
            "| N | NNZ | CSR payload GiB | modelled peak GiB "
            "| min heap GiB at the 85% rule | int-array limit |",
            "|---:|---:|---:|---:|---:|---|"]
    for e in envelope_rows([30_000_000, 70_000_000, 100_000_000]):
        out.append(
            f"| {e['n']} | {e['nnz']} | {gib(e['csr_bytes'])} "
            f"| {gib(e['model_peak_bytes'])} | {gib(e['min_heap_bytes'])} "
            f"| {'ok' if e['fits_int_array'] else 'EXCEEDED'} |")

    out += ["",
            "Per-row limit: with k stored entries per row a single Java "
            "array allows at most "
            f"{INT_ARRAY_LIMIT // 100:,} rows for k = 100 "
            f"(and {INT_ARRAY_LIMIT // 2:,} for k = 2). UNIFORM_100 at "
            "N = 100,000,000 would need 10,000,000,000 entries and is "
            "therefore not executable; it is reported as infeasible, not "
            "as PASS.", ""]
    return "\n".join(out) + "\n"


def render_article_md(
    summary: list[dict[str, str]], v2: list[dict[str, str]]
) -> str:
    out = ["# Article tables (generated from CSV; one run_id per row)", "",
           "## Table A. Parallel SpMV, harness runs", "",
           "| run_id | workload | N | strategy | p | median ms [CI95] "
           "| speedup [CI95] | efficiency |",
           "|---|---|---:|---|---:|---|---|---:|"]
    for r in summary:
        out.append(
            f"| {r['run_id']} | {r['workload']} | {r['n']} | {r['strategy']} "
            f"| {r['parallelism']} | {num(r['median_ms'])} "
            f"[{num(r['median_ci_low_ms'])}, {num(r['median_ci_high_ms'])}] "
            f"| {num(r['speedup_vs_seq'])} "
            f"[{num(r['speedup_ci_low'])}, {num(r['speedup_ci_high'])}] "
            f"| {num(r['efficiency'])} |")
    out += ["", "## Table B. V2 CI runs (N = 1M)", "",
            "| run_id | sequential ms | parallel ms | speedup |",
            "|---|---:|---:|---:|"]
    for h in v2:
        out.append(f"| {h['run_id']} | {num(h['sequential_median_ms'])} "
                   f"| {num(h['parallel_median_ms'])} | {num(h['speedup'])} |")
    return "\n".join(out) + "\n"


def latex_escape(text: str) -> str:
    return (text.replace("\\", "\\textbackslash{}")
            .replace("_", "\\_").replace("%", "\\%").replace("&", "\\&"))


def render_article_tex(
    summary: list[dict[str, str]], v2: list[dict[str, str]]
) -> str:
    lines = [
        "% Generated by P3/tools/generate_results_md.py - do not edit.",
        "\\begin{table}[ht]", "\\centering",
        "\\caption{Parallel SpMV, fork-based harness. "
        "Each row is traceable to its run\\_id.}",
        "\\begin{tabular}{llrlrrrr}", "\\toprule",
        "run\\_id & workload & $N$ & strategy & $p$ & "
        "median (ms) & speedup & eff. \\\\", "\\midrule",
    ]
    for r in summary:
        lines.append(
            f"{latex_escape(r['run_id'])} & {latex_escape(r['workload'])} "
            f"& {r['n']} & {latex_escape(r['strategy'])} "
            f"& {r['parallelism']} & {num(r['median_ms'])} "
            f"& {num(r['speedup_vs_seq'])} & {num(r['efficiency'])} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}", "",
              "\\begin{table}[ht]", "\\centering",
              "\\caption{V2 benchmark in CI ($N = 10^6$).}",
              "\\begin{tabular}{lrrr}", "\\toprule",
              "run\\_id & seq. (ms) & par. (ms) & speedup \\\\", "\\midrule"]
    for h in v2:
        lines.append(
            f"{latex_escape(h['run_id'])} & {num(h['sequential_median_ms'])} "
            f"& {num(h['parallel_median_ms'])} & {num(h['speedup'])} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    p3 = here.parent

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--harness", type=Path, required=True,
                        help="harness run directory")
    parser.add_argument("--v2", type=Path,
                        default=p3 / "benchmarks" / "benchmark_results_v2.csv")
    parser.add_argument("--v3", type=Path,
                        default=p3 / "benchmarks" / "benchmark_results_v3.csv")
    parser.add_argument("--results-dir", type=Path, default=p3 / "results")
    parser.add_argument("--write-results-md", action="store_true",
                        help="also overwrite P3/results/Results.md")
    args = parser.parse_args(argv)

    summary = read_csv(args.harness / "harness_summary.csv")
    verdict_path = args.harness / "harness_verdict.json"
    verdict_text = "unknown"
    if verdict_path.is_file():
        import json
        verdict_text = json.loads(
            verdict_path.read_text(encoding="utf-8")).get("overall", "unknown")

    v2 = v2_history(read_csv(args.v2))
    v3_summary, v3_warnings = v3_notice(read_csv(args.v3))

    results_md = render_results(
        args.harness, summary, verdict_text, v2, v3_summary, v3_warnings)

    (args.harness / "Results.generated.md").write_text(
        results_md, encoding="utf-8")
    (args.harness / "article_tables.md").write_text(
        render_article_md(summary, v2), encoding="utf-8")
    (args.harness / "article_tables.tex").write_text(
        render_article_tex(summary, v2), encoding="utf-8")

    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / "Results.generated.md").write_text(
        results_md, encoding="utf-8")

    if args.write_results_md:
        (args.results_dir / "Results.md").write_text(
            results_md, encoding="utf-8")

    print(f"wrote Results.generated.md, article_tables.md/.tex "
          f"for {args.harness.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
