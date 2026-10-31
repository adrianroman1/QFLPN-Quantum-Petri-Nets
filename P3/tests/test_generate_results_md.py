#!/usr/bin/env python3
"""Contract tests for P3/tools/generate_results_md.py (standard library only)."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "P3" / "tools" / "generate_results_md.py"

SPEC = importlib.util.spec_from_file_location("qflpn_generate_results_md", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SUMMARY_HEADER = [
    "run_id", "workload", "n", "nnz", "strategy", "parallelism", "samples",
    "forks", "median_ms", "median_ci_low_ms", "median_ci_high_ms", "mean_ms",
    "stdev_ms", "min_ms", "max_ms", "speedup_vs_seq", "speedup_ci_low",
    "speedup_ci_high", "efficiency", "overhead_pct_vs_seq", "effective_gbs",
    "stream_gbs", "bandwidth_efficiency", "bit_exact",
]


def summary_row(run_id: str, n: int, strategy: str, p: int, samples: int,
                speedup: float) -> list:
    return [run_id, "UNIFORM_2", n, 2 * n, strategy, p, samples, 5, 5.0, 4.9,
            5.1, 5.0, 0.1, 4.8, 5.3, speedup, speedup - 0.05, speedup + 0.05,
            speedup / max(p, 1), 0.0, 10.0, 12.0, 0.8, "True"]


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def make_inputs(tmp_path: Path, *, v3_dimension: int = 4096):
    harness = tmp_path / "h3-test-run"
    harness.mkdir()
    write_csv(harness / "harness_summary.csv", SUMMARY_HEADER, [
        summary_row("h3-test-run", 1_000_000, "SEQ", 1, 50, 1.0),
        summary_row("h3-test-run", 1_000_000, "STATIC", 2, 50, 1.4),
        summary_row("h3-test-run", 2_000_000, "STATIC", 2, 10, 1.3),
    ])
    (harness / "harness_verdict.json").write_text(
        json.dumps({"overall": "PARTIAL", "criteria": []}), encoding="utf-8")

    v2 = tmp_path / "v2.csv"
    write_csv(v2, ["timestamp", "run_id", "dimension", "sequential_median_ms",
                   "parallel_median_ms", "speedup"],
              [["2026-10-27T00:47:28Z", "p3-111-1", 1_000_000, 2.59, 1.89,
                1.1770]])

    v3 = tmp_path / "v3.csv"
    write_csv(v3, ["run_id", "dimension", "speedup", "verdict"],
              [["p3-111-1", v3_dimension, 0.5, "REGRESSION"],
               ["p3-111-1", v3_dimension, 1.2, "IMPROVEMENT"]])

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "Results.md").write_text("HAND WRITTEN\n", encoding="utf-8")
    return harness, v2, v3, results_dir


def run_tool(tmp_path: Path, extra: list[str] | None = None, **kwargs):
    harness, v2, v3, results_dir = make_inputs(tmp_path, **kwargs)
    argv = ["--harness", str(harness), "--v2", str(v2), "--v3", str(v3),
            "--results-dir", str(results_dir)] + (extra or [])
    assert MODULE.main(argv) == 0
    return harness, results_dir


def test_outputs_exist_and_carry_run_ids(tmp_path: Path) -> None:
    harness, results_dir = run_tool(tmp_path)

    for name in ("Results.generated.md", "article_tables.md",
                 "article_tables.tex"):
        assert (harness / name).is_file(), name

    assert (results_dir / "Results.generated.md").is_file()

    text = (harness / "Results.generated.md").read_text("utf-8")
    assert "h3-test-run" in text
    assert "p3-111-1" in text

    tex = (harness / "article_tables.tex").read_text("utf-8")
    assert "h3-test-run".replace("_", "\\_") in tex
    assert "\\toprule" in tex


def test_hand_written_results_md_is_never_touched_by_default(
        tmp_path: Path) -> None:
    _, results_dir = run_tool(tmp_path)
    assert (results_dir / "Results.md").read_text("utf-8") == "HAND WRITTEN\n"


def test_results_md_is_overwritten_only_on_explicit_request(
        tmp_path: Path) -> None:
    _, results_dir = run_tool(tmp_path, ["--write-results-md"])
    assert "Generated from artifacts" in (
        results_dir / "Results.md").read_text("utf-8")


def test_evidence_levels(tmp_path: Path) -> None:
    levels = {r["n"]: r["level"] for r in MODULE.evidence_levels([
        {"run_id": "r", "n": "1000000", "strategy": "STATIC", "samples": "50"},
        {"run_id": "r", "n": "2000000", "strategy": "STATIC", "samples": "10"},
        {"run_id": "r", "n": "7000000", "strategy": "SEQ", "samples": "50"},
    ])}

    assert levels["1000000"] == "Measured"
    assert levels["2000000"] == "Not measured yet"      # fewer than 30
    assert levels["7000000"] == "Not measured yet"      # SEQ alone is not enough
    assert levels["30000000"] == "Scalable"
    assert levels["70000000"] == "Resource Envelope"
    assert levels["100000000"] == "Resource Envelope"


def test_small_v3_dimension_triggers_a_warning(tmp_path: Path) -> None:
    harness, _ = run_tool(tmp_path, v3_dimension=4096)
    text = (harness / "Results.generated.md").read_text("utf-8")
    assert "must not be used for performance claims" in text


def test_large_v3_dimension_has_no_warning(tmp_path: Path) -> None:
    harness, _ = run_tool(tmp_path, v3_dimension=1_000_000)
    text = (harness / "Results.generated.md").read_text("utf-8")
    assert "must not be used for performance claims" not in text


def test_envelope_model_matches_the_documented_formula() -> None:
    row = MODULE.envelope_rows([100_000_000])[0]

    assert row["nnz"] == 200_000_000
    assert row["csr_bytes"] == 12 * 200_000_000 + 4 * 100_000_001
    assert row["model_peak_bytes"] == (
        2 * row["csr_bytes"] + 24 * 100_000_000 + 64 * 1024 * 1024)
    assert row["fits_int_array"] is True


def test_uniform_100_at_100m_is_declared_infeasible(tmp_path: Path) -> None:
    harness, _ = run_tool(tmp_path)
    text = (harness / "Results.generated.md").read_text("utf-8")
    assert "10,000,000,000 entries" in text
    assert "not executable" in text


def test_no_timing_is_published_for_envelope_sizes(tmp_path: Path) -> None:
    harness, _ = run_tool(tmp_path)
    text = (harness / "Results.generated.md").read_text("utf-8")
    envelope = text.split("## Resource envelope")[1]
    assert "median ms" not in envelope


def test_no_latest_copy_flag_keeps_everything_inside_the_run_directory(
        tmp_path: Path) -> None:
    harness, results_dir = run_tool(tmp_path, ["--no-latest-copy"])

    assert (harness / "Results.generated.md").is_file()
    assert not (results_dir / "Results.generated.md").exists()
    assert (results_dir / "Results.md").read_text("utf-8") == "HAND WRITTEN\n"
