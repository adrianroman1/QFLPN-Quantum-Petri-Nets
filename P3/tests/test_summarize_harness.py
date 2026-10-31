#!/usr/bin/env python3
"""Contract tests for P3/tools/summarize_harness.py (standard library only)."""

from __future__ import annotations

import csv
import importlib.util
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "P3" / "tools" / "summarize_harness.py"

SPEC = importlib.util.spec_from_file_location("qflpn_summarize_harness", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

RAW_HEADER = ["run_id", "commit_sha", "fork", "iteration", "workload", "n",
              "nnz", "strategy", "parallelism", "elapsed_ms"]
FORK_HEADER = ["run_id", "fork", "workload", "n", "nnz", "strategy",
               "parallelism", "bit_exact", "y_hash", "setup_ms",
               "peak_heap_after_build_bytes", "peak_heap_total_bytes",
               "max_heap_bytes", "processors", "java_version", "jvm_flags"]
STREAM_HEADER = ["run_id", "parallelism", "triad_gbs_best",
                 "triad_gbs_median", "array_doubles"]


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def make_run(
    tmp_path: Path,
    *,
    n: int = 10_000_000,
    forks: int = 5,
    iterations: int = 10,
    times: dict[tuple[str, int], float] | None = None,
    bit_exact: bool = True,
    with_env: bool = True,
) -> Path:
    times = times or {("SEQ", 1): 10.0, ("STATIC", 1): 10.2,
                      ("STATIC", 2): 5.5, ("FJ_PLAN_T4096", 1): 10.3,
                      ("FJ_PLAN_T4096", 2): 6.5}
    rng = random.Random(7)
    raw, fork_rows = [], []

    for fork in range(forks):
        for (strategy, p), base in times.items():
            fork_rows.append(["r1", fork, "UNIFORM_2", n, 2 * n, strategy, p,
                              str(bit_exact).lower(), "abc", 1.0, 1, 2, 3,
                              2, "21", "flags"])
            for it in range(iterations):
                value = base * (1.0 + 0.01 * rng.random())
                raw.append(["r1", "c0", fork, it, "UNIFORM_2", n, 2 * n,
                            strategy, p, f"{value:.6f}"])

    write_csv(tmp_path / "harness_raw_iterations.csv", RAW_HEADER, raw)
    write_csv(tmp_path / "harness_forks.csv", FORK_HEADER, fork_rows)
    write_csv(tmp_path / "harness_stream.csv", STREAM_HEADER,
              [["r1", 1, 15.0, 14.0, 1 << 24], ["r1", 2, 28.0, 26.0, 1 << 24]])
    write_csv(tmp_path / "harness_skipped.csv", ["item", "reason"], [])
    write_csv(tmp_path / "harness_preflight.csv",
              ["n", "workload", "nnz", "csr_bytes", "model_peak_bytes",
               "max_heap_bytes", "verdict", "reason"], [])

    if with_env:
        bases = []
        for strategy, _p in times:
            base = "FJ_PLAN" if strategy.startswith("FJ_PLAN") else strategy
            if base not in bases:
                bases.append(base)
        ps = sorted({p for (_s, p) in times if p >= 1})
        (tmp_path / "environment.json").write_text(json.dumps({
            "sizes": str(n), "workloads": "UNIFORM_2",
            "strategies": " ".join(bases),
            "parallelisms_run": ",".join(str(p) for p in ps),
            "thresholds": "4096",
        }), encoding="utf-8")

    return tmp_path


def criteria(result: dict) -> dict[str, str]:
    return {c["id"]: c["status"] for c in result["verdict"]["criteria"]}


def test_summary_statistics_and_speedup(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    result = MODULE.summarize(run)
    rows = {(r["strategy"], r["parallelism"]): r for r in result["rows"]}

    assert rows[("SEQ", 1)]["samples"] == 50
    assert rows[("SEQ", 1)]["speedup_vs_seq"] == 1.0
    assert 1.7 < rows[("STATIC", 2)]["speedup_vs_seq"] < 1.9
    assert abs(rows[("STATIC", 2)]["efficiency"]
               - rows[("STATIC", 2)]["speedup_vs_seq"] / 2) < 1e-12

    ci_low = rows[("STATIC", 2)]["median_ci_low_ms"]
    ci_high = rows[("STATIC", 2)]["median_ci_high_ms"]
    assert ci_low <= rows[("STATIC", 2)]["median_ms"] <= ci_high

    s_low = rows[("STATIC", 2)]["speedup_ci_low"]
    s_high = rows[("STATIC", 2)]["speedup_ci_high"]
    assert s_low <= rows[("STATIC", 2)]["speedup_vs_seq"] <= s_high


def test_bootstrap_is_deterministic(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    first = MODULE.summarize(run)["rows"]
    second = MODULE.summarize(run)["rows"]
    assert first == second


def test_all_criteria_pass_on_a_healthy_run(tmp_path: Path) -> None:
    result = MODULE.summarize(make_run(tmp_path))
    status = criteria(result)

    assert status["C1_SAMPLES_AT_LEAST_30"] == "PASS"
    assert status["C2_BITWISE_IDENTICAL_TO_SEQUENTIAL"] == "PASS"
    assert status["C3_OVERHEAD_AT_P1_AT_MOST_5_PERCENT"] == "PASS"
    assert status["C4_SPEEDUP_GT_1_AT_P2_N_GE_10M"] == "PASS"
    assert status["C5_NO_SIGNIFICANT_REGRESSION_AT_N_GE_1M"] == "PASS"
    assert status["C6_BANDWIDTH_CEILING_RECORDED"] == "PASS"
    assert status["C0_INPUT_DATA_PRESENT_AND_VALID"] == "PASS"
    assert status["C8_DECLARED_CONFIGURATIONS_COMPLETE"] == "PASS"
    assert result["verdict"]["overall"] == "PASS"


def test_bit_mismatch_fails(tmp_path: Path) -> None:
    result = MODULE.summarize(make_run(tmp_path, bit_exact=False))
    assert criteria(result)["C2_BITWISE_IDENTICAL_TO_SEQUENTIAL"] == "FAIL"
    assert result["verdict"]["overall"] == "FAIL"


def test_too_few_samples_fails(tmp_path: Path) -> None:
    result = MODULE.summarize(make_run(tmp_path, forks=2, iterations=10))
    assert criteria(result)["C1_SAMPLES_AT_LEAST_30"] == "FAIL"


def test_overhead_above_five_percent_fails(tmp_path: Path) -> None:
    run = make_run(tmp_path, times={("SEQ", 1): 10.0, ("STATIC", 1): 12.0})
    status = criteria(MODULE.summarize(run))
    assert status["C3_OVERHEAD_AT_P1_AT_MOST_5_PERCENT"] == "FAIL"


def test_single_core_data_is_partial_not_pass(tmp_path: Path) -> None:
    run = make_run(tmp_path, times={("SEQ", 1): 10.0, ("STATIC", 1): 10.1})
    result = MODULE.summarize(run)
    status = criteria(result)

    assert status["C4_SPEEDUP_GT_1_AT_P2_N_GE_10M"] == "NOT_EVALUATED"
    assert status["C5_NO_SIGNIFICANT_REGRESSION_AT_N_GE_1M"] == "NOT_EVALUATED"
    assert result["verdict"]["overall"] == "PARTIAL"


def test_significant_regression_is_reported(tmp_path: Path) -> None:
    run = make_run(tmp_path, times={("SEQ", 1): 10.0, ("STATIC", 1): 10.1,
                                    ("STATIC", 2): 15.0})
    status = criteria(MODULE.summarize(run))
    assert status["C5_NO_SIGNIFICANT_REGRESSION_AT_N_GE_1M"] == "FAIL"
    assert status["C4_SPEEDUP_GT_1_AT_P2_N_GE_10M"] == "FAIL"


def test_outputs_are_written(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    assert MODULE.main([str(run)]) == 0

    for name in ("harness_summary.csv", "harness_report.txt",
                 "harness_report.md", "harness_verdict.json"):
        assert (run / name).is_file(), name

    verdict = json.loads((run / "harness_verdict.json").read_text("utf-8"))
    assert verdict["overall"] in {"PASS", "PARTIAL", "FAIL"}

    with (run / "harness_summary.csv").open(newline="") as handle:
        header = next(csv.reader(handle))
    assert header == MODULE.SUMMARY_FIELDS


def test_cache_resident_note_is_emitted(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    # triad ceiling far below the model traffic -> efficiency above 1
    write_csv(run / "harness_stream.csv", STREAM_HEADER,
              [["r1", 1, 1.0, 1.0, 1 << 24], ["r1", 2, 1.0, 1.0, 1 << 24]])
    MODULE.main([str(run)])
    assert "cache resident" in (run / "harness_report.md").read_text("utf-8")


def test_missing_raw_data_is_fail_closed_not_an_exception(
        tmp_path: Path) -> None:
    result = MODULE.summarize(tmp_path)
    status = criteria(result)

    assert result["rows"] == []
    assert status["C0_INPUT_DATA_PRESENT_AND_VALID"] == "FAIL"
    assert status["C1_SAMPLES_AT_LEAST_30"] == "FAIL"
    assert result["verdict"]["overall"] == "FAIL"


def test_evaluate_with_zero_observations_never_passes() -> None:
    verdict = MODULE.evaluate([], [], [], [], [])
    status = {c["id"]: c["status"] for c in verdict["criteria"]}

    assert status["C1_SAMPLES_AT_LEAST_30"] == "FAIL"
    assert status["C0_INPUT_DATA_PRESENT_AND_VALID"] == "FAIL"
    assert verdict["overall"] == "FAIL"


def test_empty_raw_file_exits_with_status_2(tmp_path: Path) -> None:
    write_csv(tmp_path / "harness_raw_iterations.csv", RAW_HEADER, [])
    assert MODULE.main([str(tmp_path)]) == 2
    verdict = json.loads(
        (tmp_path / "harness_verdict.json").read_text("utf-8"))
    assert verdict["overall"] == "FAIL"


def test_raw_file_with_missing_columns_fails(tmp_path: Path) -> None:
    write_csv(tmp_path / "harness_raw_iterations.csv",
              ["run_id", "strategy"], [["r1", "SEQ"]])
    assert MODULE.main([str(tmp_path)]) == 2


def test_invalid_numbers_fail_input_validation(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    rows = MODULE.read_csv(run / "harness_raw_iterations.csv")
    rows[0]["elapsed_ms"] = "nan"
    rows[1]["elapsed_ms"] = "-3"
    rows[2]["elapsed_ms"] = "abc"
    write_csv(run / "harness_raw_iterations.csv", RAW_HEADER,
              [[r[h] for h in RAW_HEADER] for r in rows])

    status = criteria(MODULE.summarize(run))
    assert status["C0_INPUT_DATA_PRESENT_AND_VALID"] == "FAIL"
    assert MODULE.main([str(run)]) == 2


def test_duplicate_observations_fail_input_validation(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    rows = MODULE.read_csv(run / "harness_raw_iterations.csv")
    rows.append(dict(rows[0]))
    write_csv(run / "harness_raw_iterations.csv", RAW_HEADER,
              [[r[h] for h in RAW_HEADER] for r in rows])

    result = MODULE.summarize(run)
    assert criteria(result)["C0_INPUT_DATA_PRESENT_AND_VALID"] == "FAIL"


def test_a_declared_configuration_without_data_fails(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    env = json.loads((run / "environment.json").read_text("utf-8"))
    env["sizes"] = f"{env['sizes']} 20000000"      # declared, never measured
    (run / "environment.json").write_text(json.dumps(env), encoding="utf-8")

    result = MODULE.summarize(run)
    status = criteria(result)

    assert status["C8_DECLARED_CONFIGURATIONS_COMPLETE"] == "FAIL"
    assert result["verdict"]["overall"] == "FAIL"


def test_a_declared_configuration_skipped_with_a_reason_is_not_missing(
        tmp_path: Path) -> None:
    run = make_run(tmp_path)
    env = json.loads((run / "environment.json").read_text("utf-8"))
    env["sizes"] = f"{env['sizes']} 20000000"
    (run / "environment.json").write_text(json.dumps(env), encoding="utf-8")
    write_csv(run / "harness_skipped.csv", ["item", "reason"],
              [["n=20000000 workload=UNIFORM_2", "preflight refused"]])

    status = criteria(MODULE.summarize(run))
    assert status["C8_DECLARED_CONFIGURATIONS_COMPLETE"] == "PASS"


def test_without_environment_json_the_verdict_cannot_be_pass(
        tmp_path: Path) -> None:
    result = MODULE.summarize(make_run(tmp_path, with_env=False))
    status = criteria(result)

    assert status["C8_DECLARED_CONFIGURATIONS_COMPLETE"] == "NOT_EVALUATED"
    assert result["verdict"]["overall"] == "PARTIAL"


def test_strict_mode_requires_pass(tmp_path: Path) -> None:
    run = make_run(tmp_path, with_env=False)         # PARTIAL
    assert MODULE.main([str(run)]) == 0
    assert MODULE.main([str(run), "--strict"]) == 1


def test_threshold_sweep_labels_are_expected_per_threshold(
        tmp_path: Path) -> None:
    env = {"sizes": "1000", "workloads": "UNIFORM_2",
           "strategies": "SEQ FJ_PLAN", "parallelisms_run": "1,2",
           "thresholds": "256 4096"}
    expected = MODULE.expected_configurations(env, [])

    assert ("UNIFORM_2", 1000, "SEQ", 1) in expected
    assert ("UNIFORM_2", 1000, "FJ_PLAN_T256", 2) in expected
    assert ("UNIFORM_2", 1000, "FJ_PLAN_T4096", 1) in expected
    assert len(expected) == 1 + 2 * 2
