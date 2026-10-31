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

Fail-closed rules:
    - no observations, a missing or malformed raw file, non-numeric or
      non-positive timings, or duplicated observations -> C0 FAIL;
    - a configuration declared in environment.json (and not skipped with a
      reason) that has no observations -> C8 FAIL;
    - without environment.json completeness cannot be proven -> C8
      NOT_EVALUATED, so the overall verdict can never be PASS;
    - exit status 2 when the input data are absent or invalid.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
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

RAW_FIELDS = ["run_id", "commit_sha", "fork", "iteration", "workload", "n",
              "nnz", "strategy", "parallelism", "elapsed_ms"]

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

    env = read_environment(run_dir)
    problems: list[str] = []

    if not (run_dir / "harness_raw_iterations.csv").is_file():
        problems.append("harness_raw_iterations.csv is missing")
    elif raw:
        missing_cols = [c for c in RAW_FIELDS if c not in raw[0]]
        if missing_cols:
            problems.append(f"raw CSV lacks columns {missing_cols}")
            raw = []

    if not raw:
        if not problems:
            problems.append("no raw iteration observations")
        return {
            "rows": [],
            "verdict": evaluate([], forks, stream, skipped, preflight,
                                problems=problems, env=env, observed=set()),
            "stream": stream, "skipped": skipped, "preflight": preflight,
            "forks": forks,
        }

    rng = random.Random(BOOTSTRAP_SEED)

    groups: dict[tuple, dict[tuple, float]] = defaultdict(dict)
    meta: dict[tuple, dict[str, Any]] = {}
    seen: set[tuple] = set()

    for line, row in enumerate(raw, start=2):
        try:
            key = (row["workload"], int(row["n"]), row["strategy"],
                   int(row["parallelism"]))
            slot = (int(row["fork"]), int(row["iteration"]))
            elapsed = float(row["elapsed_ms"])
            nnz = int(row["nnz"])
        except (TypeError, ValueError):
            problems.append(f"raw line {line}: non-numeric field")
            continue

        if not math.isfinite(elapsed) or elapsed <= 0.0:
            problems.append(f"raw line {line}: invalid elapsed_ms {elapsed}")
            continue

        identity = key + slot
        if identity in seen:
            problems.append(f"raw line {line}: duplicate observation {identity}")
            continue

        seen.add(identity)
        groups[key][slot] = elapsed
        meta[key] = {"run_id": row["run_id"], "nnz": nnz}

    if not groups:
        problems.append("no valid observation remained after validation")
        return {
            "rows": [],
            "verdict": evaluate([], forks, stream, skipped, preflight,
                                problems=problems, env=env, observed=set()),
            "stream": stream, "skipped": skipped, "preflight": preflight,
            "forks": forks,
        }

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

    verdict = evaluate(rows, forks, stream, skipped, preflight,
                       problems=problems, env=env, observed=set(groups))

    return {
        "rows": rows,
        "verdict": verdict,
        "stream": stream,
        "skipped": skipped,
        "preflight": preflight,
        "forks": forks,
    }


def read_environment(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "environment.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def expected_configurations(
    env: dict[str, Any], skipped: list[dict[str, str]]
) -> set[tuple]:
    """Configurations the run declared and did not skip with a reason."""
    skipped_n: set[int] = set()
    skipped_nw: set[tuple[int, str]] = set()

    for row in skipped:
        item = row.get("item", "")
        n_match = re.search(r"n=(\d+)", item)
        w_match = re.search(r"workload=(\w+)", item)
        if n_match and w_match:
            skipped_nw.add((int(n_match.group(1)), w_match.group(1)))
        elif n_match:
            skipped_n.add(int(n_match.group(1)))

    sizes = [int(t) for t in str(env.get("sizes", "")).split()]
    workloads = str(env.get("workloads", "")).split()
    strategies = str(env.get("strategies", "")).upper().split()
    parallelisms = [int(t) for t in
                    str(env.get("parallelisms_run", "")).split(",") if t]
    thresholds = str(env.get("thresholds", "4096")).split() or ["4096"]

    expected: set[tuple] = set()
    for n in sizes:
        for w in workloads:
            if n in skipped_n or (n, w) in skipped_nw:
                continue
            for strategy in strategies:
                if strategy == "SEQ":
                    expected.add((w, n, "SEQ", 1))
                elif strategy == "FJ_PLAN":
                    for p in parallelisms:
                        for t in thresholds:
                            expected.add((w, n, f"FJ_PLAN_T{t}", p))
                else:
                    for p in parallelisms:
                        expected.add((w, n, strategy, p))
    return expected


def evaluate(
    rows: list[dict[str, Any]],
    forks: list[dict[str, str]],
    stream: list[dict[str, str]],
    skipped: list[dict[str, str]],
    preflight: list[dict[str, str]],
    problems: list[str] | None = None,
    env: dict[str, Any] | None = None,
    observed: set[tuple] | None = None,
) -> dict[str, Any]:
    criteria: list[dict[str, str]] = []
    problems = problems or []
    observed = observed if observed is not None else {
        (r["workload"], r["n"], r["strategy"], r["parallelism"])
        for r in rows}

    def add(cid: str, status: str, detail: str) -> None:
        criteria.append({"id": cid, "status": status, "detail": detail})

    # C0: input present and valid (fail-closed)
    if not rows or problems:
        shown = "; ".join(problems[:5]) if problems else "no observations"
        more = f" (+{len(problems) - 5} more)" if len(problems) > 5 else ""
        add("C0_INPUT_DATA_PRESENT_AND_VALID", "FAIL", shown + more)
    else:
        add("C0_INPUT_DATA_PRESENT_AND_VALID", "PASS",
            f"{len(rows)} configuration(s), all observations valid, "
            "no duplicates")

    # C1: sample size (an empty data set is never a PASS)
    short = [r for r in rows if r["samples"] < MIN_SAMPLES]
    if not rows:
        add("C1_SAMPLES_AT_LEAST_30", "FAIL", "no configuration has data")
    else:
        add("C1_SAMPLES_AT_LEAST_30",
            "FAIL" if short else "PASS",
            f"{len(short)} configuration(s) below {MIN_SAMPLES} samples"
            if short else f"all configurations have >= {MIN_SAMPLES} samples")

    # C8: every declared configuration is present
    if env is None:
        add("C8_DECLARED_CONFIGURATIONS_COMPLETE", "NOT_EVALUATED",
            "environment.json missing or unreadable: completeness cannot "
            "be proven")
    else:
        expected = expected_configurations(env, skipped)
        absent = sorted(expected - observed)
        if not expected:
            add("C8_DECLARED_CONFIGURATIONS_COMPLETE", "FAIL",
                "environment.json declares no configuration")
        elif absent:
            add("C8_DECLARED_CONFIGURATIONS_COMPLETE", "FAIL",
                f"{len(absent)} of {len(expected)} declared configuration(s) "
                f"have no observations, e.g. {absent[:3]}")
        else:
            add("C8_DECLARED_CONFIGURATIONS_COMPLETE", "PASS",
                f"all {len(expected)} declared configuration(s) observed")

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
    parser.add_argument("--strict", action="store_true",
                        help="exit with status 1 unless the verdict is PASS")
    args = parser.parse_args(argv)

    result = summarize(args.run_dir)

    if result["rows"]:
        write_outputs(args.run_dir, result)
    else:
        (args.run_dir).mkdir(parents=True, exist_ok=True)
        (args.run_dir / "harness_verdict.json").write_text(
            json.dumps(result["verdict"], indent=2) + "\n", encoding="utf-8")

    verdict = result["verdict"]
    print(f"overall verdict: {verdict['overall']}")
    for c in verdict["criteria"]:
        print(f"  [{c['status']}] {c['id']}: {c['detail']}")

    status = {c["id"]: c["status"] for c in verdict["criteria"]}
    if status.get("C0_INPUT_DATA_PRESENT_AND_VALID") == "FAIL":
        print("INPUT_DATA_INVALID: no verdict can be derived from these data",
              file=sys.stderr)
        return 2

    if args.strict and verdict["overall"] != "PASS":
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
