#!/usr/bin/env python3
"""Summarize a P3 parallel SpMV harness run (standard library only).

Input directory (produced by P3/results/run_parallel_harness.sh):
    harness_raw_iterations.csv   one row per timed multiplication
    harness_forks.csv            one row per (fork, strategy, parallelism)
    harness_stream.csv           memory-bandwidth ceiling (triad), optional
    harness_preflight.csv        preflight decisions, optional
    harness_skipped.csv          explicitly skipped configurations, optional

Output (written into the same directory):
    harness_summary.csv   statistics per configuration
    harness_report.txt    plain-text report
    harness_report.md     Markdown report
    harness_verdict.json  machine-readable criteria and overall verdict

Nothing is invented: a criterion that cannot be evaluated on the machine
that produced the data (for example speedup with a single core) is reported
as NOT_EVALUATED, never as PASS.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

MIN_SAMPLES = 30
OVERHEAD_LIMIT_PCT = 5.0
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20261029
LARGE_N = 1_000_000
SPEEDUP_N = 10_000_000

SUMMARY_FIELDS = [
    "run_id", "workload", "n", "nnz", "strategy", "parallelism",
    "samples", "forks", "median_ms", "median_ci_low_ms", "median_ci_high_ms",
    "mean_ms", "stdev_ms", "min_ms", "max_ms",
    "speedup_vs_seq", "speedup_ci_low", "speedup_ci_high",
    "efficiency", "overhead_pct_vs_seq",
    "effective_gbs", "stream_gbs", "bandwidth_efficiency", "bit_exact",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return math.nan
    position = fraction * (len(sorted_values) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return sorted_values[low]
    weight = position - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def bootstrap_median_ci(
    values: list[float], rng: random.Random
) -> tuple[float, float]:
    if len(values) < 2:
        value = values[0] if values else math.nan
        return value, value
    medians = []
    size = len(values)
    for _ in range(BOOTSTRAP_RESAMPLES):
        sample = [values[rng.randrange(size)] for _ in range(size)]
        medians.append(statistics.median(sample))
    medians.sort()
    return percentile(medians, 0.025), percentile(medians, 0.975)


CACHE_NOTE = (
    "bw eff above 1.0 means the working set (matrix + vectors) is at least "
    "partly cache resident, so the DRAM triad ceiling does not apply to that "
    "row; read bandwidth efficiency only at sizes well above the last-level "
    "cache (7M rows and above)."
)


def cache_resident_rows(rows: list[dict[str, Any]]) -> bool:
    return any(
        isinstance(r["bandwidth_efficiency"], float)
        and not math.isnan(r["bandwidth_efficiency"])
        and r["bandwidth_efficiency"] > 1.0
        for r in rows
    )


def fmt(value: float, digits: int = 4) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return f"{value:.{digits}f}"


# ---------------------------------------------------------------------------
# core computation
# ---------------------------------------------------------------------------

def summarize(run_dir: Path) -> dict[str, Any]:
    raw = read_csv(run_dir / "harness_raw_iterations.csv")
    forks = read_csv(run_dir / "harness_forks.csv")
    stream = read_csv(run_dir / "harness_stream.csv")
    skipped = read_csv(run_dir / "harness_skipped.csv")
    preflight = read_csv(run_dir / "harness_preflight.csv")

    if not raw:
        raise SystemExit(f"No raw iteration data in {run_dir}")

    rng = random.Random(BOOTSTRAP_SEED)

    groups: dict[tuple, dict[tuple, float]] = defaultdict(dict)
    meta: dict[tuple, dict[str, Any]] = {}

    for row in raw:
        key = (row["workload"], int(row["n"]), row["strategy"],
               int(row["parallelism"]))
        slot = (int(row["fork"]), int(row["iteration"]))
        groups[key][slot] = float(row["elapsed_ms"])
        meta[key] = {"run_id": row["run_id"], "nnz": int(row["nnz"])}

    bit_exact: dict[tuple, bool] = defaultdict(lambda: True)
    for row in forks:
        key = (row["workload"], int(row["n"]), row["strategy"],
               int(row["parallelism"]))
        if row["bit_exact"].strip().lower() != "true":
            bit_exact[key] = False
        else:
            bit_exact[key] = bit_exact[key]

    stream_gbs = {int(r["parallelism"]): float(r["triad_gbs_best"])
                  for r in stream}

    def stream_for(parallelism: int) -> float:
        usable = [p for p in stream_gbs if p <= parallelism]
        return stream_gbs[max(usable)] if usable else math.nan

    rows: list[dict[str, Any]] = []

    for key in sorted(groups):
        workload, n, strategy, parallelism = key
        slots = groups[key]
        values = [slots[s] for s in sorted(slots)]
        median = statistics.median(values)
        ci_low, ci_high = bootstrap_median_ci(values, rng)
        stdev = statistics.stdev(values) if len(values) > 1 else 0.0
        nnz = meta[key]["nnz"]

        seq_slots = groups.get((workload, n, "SEQ", 1), {})
        paired = [seq_slots[s] / slots[s]
                  for s in slots if s in seq_slots and slots[s] > 0]
        seq_median = (statistics.median(list(seq_slots.values()))
                      if seq_slots else math.nan)

        if strategy == "SEQ" or not paired:
            speedup = 1.0 if strategy == "SEQ" else math.nan
            s_low = s_high = speedup
        else:
            speedup = seq_median / median
            s_low, s_high = bootstrap_median_ci(paired, rng)

        efficiency = (speedup / parallelism
                      if not math.isnan(speedup) else math.nan)
        overhead = ((median / seq_median - 1.0) * 100.0
                    if strategy != "SEQ" and not math.isnan(seq_median)
                    else 0.0 if strategy == "SEQ" else math.nan)

        # Traffic model: values 8 + column 4 per entry, row pointer 4 per
        # row, x streamed once 8 per row, y written once 8 per row.
        bytes_moved = 12.0 * nnz + 4.0 * (n + 1) + 16.0 * n
        effective = bytes_moved / (median * 1e6)
        ceiling = stream_for(parallelism)
        band_eff = (effective / ceiling
                    if ceiling and not math.isnan(ceiling) else math.nan)

        rows.append({
            "run_id": meta[key]["run_id"],
            "workload": workload,
            "n": n,
            "nnz": nnz,
            "strategy": strategy,
            "parallelism": parallelism,
            "samples": len(values),
            "forks": len({s[0] for s in slots}),
            "median_ms": median,
            "median_ci_low_ms": ci_low,
            "median_ci_high_ms": ci_high,
            "mean_ms": statistics.fmean(values),
            "stdev_ms": stdev,
            "min_ms": min(values),
            "max_ms": max(values),
            "speedup_vs_seq": speedup,
            "speedup_ci_low": s_low,
            "speedup_ci_high": s_high,
            "efficiency": efficiency,
            "overhead_pct_vs_seq": overhead,
            "effective_gbs": effective,
            "stream_gbs": ceiling,
            "bandwidth_efficiency": band_eff,
            "bit_exact": bit_exact[key] if forks else "",
        })

    verdict = evaluate(rows, forks, stream, skipped, preflight)

    return {
        "rows": rows,
        "verdict": verdict,
        "stream": stream,
        "skipped": skipped,
        "preflight": preflight,
        "forks": forks,
    }


def evaluate(
    rows: list[dict[str, Any]],
    forks: list[dict[str, str]],
    stream: list[dict[str, str]],
    skipped: list[dict[str, str]],
    preflight: list[dict[str, str]],
) -> dict[str, Any]:
    criteria: list[dict[str, str]] = []

    def add(cid: str, status: str, detail: str) -> None:
        criteria.append({"id": cid, "status": status, "detail": detail})

    # C1: sample size
    short = [r for r in rows if r["samples"] < MIN_SAMPLES]
    add("C1_SAMPLES_AT_LEAST_30",
        "FAIL" if short else "PASS",
        f"{len(short)} configuration(s) below {MIN_SAMPLES} samples"
        if short else f"all configurations have >= {MIN_SAMPLES} samples")

    # C2: bit-exact reproducibility
    if forks:
        bad = sorted({(r["workload"], r["n"], r["strategy"], r["parallelism"])
                      for r in rows if r["bit_exact"] is False})
        add("C2_BITWISE_IDENTICAL_TO_SEQUENTIAL",
            "FAIL" if bad else "PASS",
            f"mismatch in {bad}" if bad
            else "every strategy reproduced the sequential bits in every fork")
    else:
        add("C2_BITWISE_IDENTICAL_TO_SEQUENTIAL", "NOT_EVALUATED",
            "harness_forks.csv missing")

    # C3: overhead control at p = 1 for N >= 1M
    control = [r for r in rows
               if r["strategy"] != "SEQ" and r["parallelism"] == 1
               and r["n"] >= LARGE_N]
    if control:
        over = [r for r in control
                if r["overhead_pct_vs_seq"] > OVERHEAD_LIMIT_PCT]
        worst = max(control, key=lambda r: r["overhead_pct_vs_seq"])
        add("C3_OVERHEAD_AT_P1_AT_MOST_5_PERCENT",
            "FAIL" if over else "PASS",
            "worst: {} {} n={} overhead={:.1f}%".format(
                worst["strategy"], worst["workload"], worst["n"],
                worst["overhead_pct_vs_seq"])
            + (f"; {len(over)} configuration(s) above {OVERHEAD_LIMIT_PCT}%"
               if over else ""))
    else:
        add("C3_OVERHEAD_AT_P1_AT_MOST_5_PERCENT", "NOT_EVALUATED",
            f"no p=1 strategy rows with n >= {LARGE_N}")

    # C4: speedup > 1 at p = 2, N >= 10M (lower CI bound)
    p2 = [r for r in rows if r["strategy"] != "SEQ"
          and r["parallelism"] == 2 and r["n"] >= SPEEDUP_N]
    if p2:
        best = max(p2, key=lambda r: r["speedup_ci_low"])
        ok = best["speedup_ci_low"] > 1.0
        add("C4_SPEEDUP_GT_1_AT_P2_N_GE_10M",
            "PASS" if ok else "FAIL",
            "best: {} {} n={} speedup={:.3f} CI95=[{:.3f}, {:.3f}]".format(
                best["strategy"], best["workload"], best["n"],
                best["speedup_vs_seq"], best["speedup_ci_low"],
                best["speedup_ci_high"]))
    else:
        add("C4_SPEEDUP_GT_1_AT_P2_N_GE_10M", "NOT_EVALUATED",
            "no p=2 rows with n >= 10M; this needs a machine with at least "
            "2 cores and the 10M size")

    # C5: no unexplained regression (CI entirely below 1) at p >= 2, N >= 1M
    regress = [r for r in rows if r["strategy"] != "SEQ"
               and r["parallelism"] >= 2 and r["n"] >= LARGE_N
               and r["speedup_ci_high"] < 1.0]
    parallel_rows = [r for r in rows if r["strategy"] != "SEQ"
                     and r["parallelism"] >= 2 and r["n"] >= LARGE_N]
    if parallel_rows:
        add("C5_NO_SIGNIFICANT_REGRESSION_AT_N_GE_1M",
            "FAIL" if regress else "PASS",
            "; ".join("{} {} n={} p={} speedup CI95 high={:.3f}".format(
                r["strategy"], r["workload"], r["n"], r["parallelism"],
                r["speedup_ci_high"]) for r in regress)
            if regress else "no configuration is significantly slower")
    else:
        add("C5_NO_SIGNIFICANT_REGRESSION_AT_N_GE_1M", "NOT_EVALUATED",
            "no p >= 2 rows (single-core machine or filtered)")

    # C6: bandwidth ceiling recorded
    add("C6_BANDWIDTH_CEILING_RECORDED",
        "PASS" if stream else "NOT_EVALUATED",
        f"{len(stream)} triad measurement(s)" if stream
        else "harness_stream.csv missing")

    # C7: skipped configurations documented
    reasons = [r for r in skipped if r.get("reason")]
    blocked = [r for r in preflight if r.get("verdict") == "SKIP"]
    add("C7_SKIPS_AND_PREFLIGHT_DOCUMENTED",
        "PASS" if (reasons or blocked or not skipped) else "FAIL",
        f"{len(skipped)} skipped configuration(s) with reasons, "
        f"{len(blocked)} preflight refusal(s)")

    statuses = {c["status"] for c in criteria}
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "NOT_EVALUATED" in statuses:
        overall = "PARTIAL"
    else:
        overall = "PASS"

    return {"overall": overall, "criteria": criteria}


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

def write_outputs(run_dir: Path, result: dict[str, Any]) -> None:
    rows = result["rows"]
    verdict = result["verdict"]

    with (run_dir / "harness_summary.csv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                k: (fmt(v, 6) if isinstance(v, float) else v)
                for k, v in row.items()
            })

    (run_dir / "harness_verdict.json").write_text(
        json.dumps(verdict, indent=2) + "\n", encoding="utf-8")

    run_id = rows[0]["run_id"]
    header = (f"P3 parallel SpMV harness report\nrun_id: {run_id}\n"
              f"overall verdict: {verdict['overall']}\n")

    lines = [header, "Criteria:"]
    for c in verdict["criteria"]:
        lines.append(f"  [{c['status']:13}] {c['id']}: {c['detail']}")

    lines.append("\nResults (median ms, 95% bootstrap CI, speedup vs SEQ):")
    for r in rows:
        lines.append(
            "  {w:10} n={n:>9} {s:8} p={p} samples={k:>3} "
            "median={m} CI=[{lo}, {hi}] speedup={sp} eff={ef} "
            "overhead%={ov} GB/s={gb} bw_eff={be} bit_exact={bx}".format(
                w=r["workload"], n=r["n"], s=r["strategy"],
                p=r["parallelism"], k=r["samples"],
                m=fmt(r["median_ms"]), lo=fmt(r["median_ci_low_ms"]),
                hi=fmt(r["median_ci_high_ms"]),
                sp=fmt(r["speedup_vs_seq"], 3), ef=fmt(r["efficiency"], 3),
                ov=fmt(r["overhead_pct_vs_seq"], 1),
                gb=fmt(r["effective_gbs"], 2),
                be=fmt(r["bandwidth_efficiency"], 3), bx=r["bit_exact"]))
    if cache_resident_rows(rows):
        lines.append("\nNote: " + CACHE_NOTE)
    (run_dir / "harness_report.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")

    md = [f"# P3 parallel SpMV harness report", "",
          f"- run_id: `{run_id}`",
          f"- overall verdict: **{verdict['overall']}**", "",
          "## Criteria", "",
          "| Criterion | Status | Detail |", "|---|---|---|"]
    for c in verdict["criteria"]:
        md.append(f"| {c['id']} | {c['status']} | {c['detail']} |")

    md += ["", "## Results", "",
           "| workload | n | strategy | p | samples | median ms "
           "| CI95 low | CI95 high | speedup | speedup CI95 | eff "
           "| overhead % | GB/s | bw eff | bit exact |",
           "|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|"]
    for r in rows:
        md.append(
            "| {w} | {n} | {s} | {p} | {k} | {m} | {lo} | {hi} | {sp} "
            "| [{sl}, {sh}] | {ef} | {ov} | {gb} | {be} | {bx} |".format(
                w=r["workload"], n=r["n"], s=r["strategy"],
                p=r["parallelism"], k=r["samples"],
                m=fmt(r["median_ms"]), lo=fmt(r["median_ci_low_ms"]),
                hi=fmt(r["median_ci_high_ms"]),
                sp=fmt(r["speedup_vs_seq"], 3),
                sl=fmt(r["speedup_ci_low"], 3),
                sh=fmt(r["speedup_ci_high"], 3),
                ef=fmt(r["efficiency"], 3),
                ov=fmt(r["overhead_pct_vs_seq"], 1),
                gb=fmt(r["effective_gbs"], 2),
                be=fmt(r["bandwidth_efficiency"], 3), bx=r["bit_exact"]))
    md += ["", "Traffic model for GB/s: 12 B per stored entry, 4 B per row "
           "pointer, 8 B for x and 8 B for y per row (x assumed streamed "
           "once). `bw eff` divides it by the best STREAM-like triad "
           "measured at the same or the nearest lower parallelism.", ""]
    if cache_resident_rows(rows):
        md += [f"> **Note:** {CACHE_NOTE}", ""]

    if result["skipped"]:
        md += ["## Skipped configurations", "",
               "| item | reason |", "|---|---|"]
        for r in result["skipped"]:
            md.append(f"| {r.get('item', '')} | {r.get('reason', '')} |")
        md.append("")

    (run_dir / "harness_report.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)

    result = summarize(args.run_dir)
    write_outputs(args.run_dir, result)
    print(f"overall verdict: {result['verdict']['overall']}")
    for c in result["verdict"]["criteria"]:
        print(f"  [{c['status']}] {c['id']}: {c['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
