"""Regression tests for the paired P2 benchmark evidence contract."""

from __future__ import annotations

import csv
import importlib.util
import json
import statistics
import sys
from pathlib import Path

import pytest

P2_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = P2_ROOT / "benchmarks"

if str(BENCHMARKS_DIR) not in sys.path:
    sys.path.insert(0, str(BENCHMARKS_DIR))

VALIDATOR_PATH = BENCHMARKS_DIR / "validate_benchmark.py"

SPEC = importlib.util.spec_from_file_location(
    "p2_benchmark_validator",
    VALIDATOR_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load P2 benchmark validator.")

VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

OPERATIONS = VALIDATOR.EXPECTED_OPERATIONS
CSV_FIELDS = VALIDATOR.CSV_FIELDS


def make_test_contract(
    tmp_path: Path,
    artifacts: dict[str, str] | None = None,
):
    """Build a validated contract using the canonical P2 benchmark config."""
    canonical_config = json.loads(
        (BENCHMARKS_DIR / "benchmark_config.json").read_text(
            encoding="utf-8"
        )
    )
    canonical_config["output_directory"] = tmp_path.name

    if artifacts is not None:
        canonical_config["artifacts"] = artifacts

    config_path = tmp_path / "test_benchmark_config.json"
    config_path.write_text(
        json.dumps(canonical_config, indent=2),
        encoding="utf-8",
    )

    return VALIDATOR.load_benchmark_contract(
        config_path,
        p2_root=tmp_path.parent,
    )


def make_stats(values: list[int]) -> dict:
    median = statistics.median(values)

    return {
        "minimum_ns": min(values),
        "median_ns": median,
        "mean_ns": statistics.mean(values),
        "maximum_ns": max(values),
        "standard_deviation_ns": statistics.pstdev(values),
        "samples": len(values),
        "operations_per_second": 1_000_000_000.0 / median,
    }


def make_operation(name: str) -> dict:
    production_times = [1000 + index for index in range(30)]
    independent_times = [1100 + index for index in range(30)]

    production = make_stats(production_times)
    independent = make_stats(independent_times)

    differences = [
        independent_time - production_time
        for production_time, independent_time in zip(
            production_times,
            independent_times,
        )
    ]

    wins = sum(
        production_time < independent_time
        for production_time, independent_time in zip(
            production_times,
            independent_times,
        )
    )

    ties = sum(
        production_time == independent_time
        for production_time, independent_time in zip(
            production_times,
            independent_times,
        )
    )

    paired_samples = []

    for index, (production_ns, independent_ns) in enumerate(
        zip(production_times, independent_times)
    ):
        paired_samples.append({
            "sample_index": index + 1,
            "first_execution": (
                "production" if index % 2 == 0 else "independent"
            ),
            "production_ns": production_ns,
            "independent_ns": independent_ns,
            "difference_independent_minus_production_ns": (
                independent_ns - production_ns
            ),
        })

    ratio = independent["median_ns"] / production["median_ns"]

    reduction = (
        (independent["median_ns"] - production["median_ns"])
        / independent["median_ns"]
        * 100.0
    )

    return {
        "operation": name,
        "warmups": 5,
        "repetitions": 30,

        # Legacy production fields retained for CSV compatibility.
        "minimum_ns": production["minimum_ns"],
        "median_ns": production["median_ns"],
        "mean_ns": production["mean_ns"],
        "maximum_ns": production["maximum_ns"],
        "standard_deviation_ns": (
            production["standard_deviation_ns"]
        ),
        "operations_per_second": (
            production["operations_per_second"]
        ),
        "numerical_error": 0.0,
        "numerical_tolerance": 1e-12,
        "passed": True,

        "production": production,
        "independent": independent,

        "paired_comparison": {
            "median_difference_independent_minus_production_ns": (
                statistics.median(differences)
            ),
            "production_win_count": wins,
            "tie_count": ties,
            "production_win_rate_percent": (
                wins / 30 * 100.0
            ),
            "independent_over_production_median_ratio": ratio,
            "production_reduction_percent_vs_independent": reduction,
        },

        "independent_numerical_error": 0.0,
        "independent_passed": True,
        "paired_samples": paired_samples,

        "world_record": {
            "display": VALIDATOR.EXPECTED_WORLD_RECORD_DISPLAY,
            "status": VALIDATOR.EXPECTED_WORLD_RECORD_STATUS,
            "verified_value_ns": None,
            "source": None,
            "reason": (
                "No verified directly comparable operation-level record."
            ),
        },
    }


def make_report() -> dict:
    rows = [
        make_operation(name)
        for name in OPERATIONS
    ]

    production_total_ns = sum(
        sample["production_ns"]
        for row in rows
        for sample in row["paired_samples"]
    )

    independent_total_ns = sum(
        sample["independent_ns"]
        for row in rows
        for sample in row["paired_samples"]
    )

    production_total = production_total_ns / 1_000_000_000.0
    independent_total = independent_total_ns / 1_000_000_000.0

    return {
        "schema_version": 1,
        "benchmark_id": VALIDATOR.EXPECTED_BENCHMARK_ID,
        "project": "QFLPN P2",
        "timestamp_utc": "2026-10-20T12:00:00+00:00",
        "qubits": 4,
        "hilbert_dimension": 16,
        "basis_order": "big-endian",
        "activation_vector": [0.85, 0.9, 0.45, 0.7],
        "operator_order": "U = C3X @ U_rot",
        "warmups": 5,
        "repetitions": 30,
        "timer": "time.perf_counter_ns",
        "numerical_tolerance": 1e-12,

        "total_runtime_seconds": 10.0,
        "runtime_measurement_scope": (
            VALIDATOR.EXPECTED_RUNTIME_SCOPE
        ),

        "production_total_execution_seconds": production_total,
        "independent_total_execution_seconds": independent_total,
        "combined_timed_execution_seconds": (
            production_total + independent_total
        ),
        "initial_evidence_generation_seconds": 0.1,

        "environment": {
            "python_version": "3.11.17",
            "numpy_version": "2.2.6",
            "pennylane_version": "0.41.1",
            "scipy_version": "1.15.3",
        },

        "independent_reference": {
            "method": "Independent NumPy reference.",
            "used_for_timed_operation_checks": True,
            "paired_measurement": True,
            "execution_order": (
                "Alternating production-first and independent-first."
            ),
        },

        "pennylane_numpy_maximum_difference": 0.0,

        "literature_benchmarks": [
            {
                "id": "TEST-SOURCE",
                "title": "Test literature benchmark",
                "venue": "Test venue",
                "year": 2025,
                "url": "https://example.org/test",
                "scope": "Test-only scope.",
                "p2_comparability": "Not a directly comparable record.",
            }
        ],

        "world_record_policy": (
            "Only directly comparable and independently verified "
            "measurements may be called records."
        ),

        "operations": rows,
        "all_checks_pass": True,
        "status": "PASS",
    }


def make_markdown(report: dict) -> str:
    lines = [
        "# QFLPN P2 — Benchmark Results",
        "",
        f"- Generated (UTC): `{report['timestamp_utc']}`",
        f"- Status: **{report['status']}**",
        f"- Qubits: `{report['qubits']}`",
        f"- Hilbert dimension: `{report['hilbert_dimension']}`",
        f"- Basis order: `{report['basis_order']}`",
        f"- Operator order: `{report['operator_order']}`",
        f"- Warmups per operation: `{report['warmups']}`",
        f"- Measured repetitions: `{report['repetitions']}`",
        f"- Timer: `{report['timer']}`",
        f"- Numerical tolerance: `{report['numerical_tolerance']:.3e}`",
        (
            "- Total benchmark runtime: "
            f"**{report['total_runtime_seconds']:.6f} seconds**"
        ),
        (
            "- Total production execution time: "
            f"**{report['production_total_execution_seconds']:.9f} seconds**"
        ),
        (
            "- Total independent execution time: "
            f"**{report['independent_total_execution_seconds']:.9f} seconds**"
        ),
        (
            "- Total timed execution time (both implementations): "
            f"**{report['combined_timed_execution_seconds']:.9f} seconds**"
        ),
        (
            "- Initial evidence-generation time: "
            f"**{report['initial_evidence_generation_seconds']:.6f} seconds**"
        ),
        (
            f"- Runtime measurement scope: "
            f"{report['runtime_measurement_scope']}"
        ),
        "",
        "## Numerical parity",
        "",
        "PennyLane / independent NumPy state difference: `0.000000e+00`",
        "",
        "## Paired operation measurements",
        "",
        (
            "| Operation | Production median (ns) | Independent median (ns) "
            "| Production reduction (%) | Paired median difference (ns) "
            "| Production wins (%) | World record |"
        ),
        "|---|---:|---:|---:|---:|---:|---|",
    ]

    for row in report["operations"]:
        paired = row["paired_comparison"]

        lines.append(
            f"| {row['operation']}"
            f" | {row['production']['median_ns']:.2f}"
            f" | {row['independent']['median_ns']:.2f}"
            f" | {paired['production_reduction_percent_vs_independent']:.3f}"
            f" | {paired['median_difference_independent_minus_production_ns']:.2f}"
            f" | {paired['production_win_rate_percent']:.2f}"
            f" | {row['world_record']['display']} |"
        )

    lines.extend([
        "",
        "## Full timing statistics",
        "",
        (
            "| Operation | Implementation | Min (ns) | Median (ns) "
            "| Mean (ns) | Max (ns) | Std. dev. (ns) | Samples |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ])

    for row in report["operations"]:
        for implementation in ("production", "independent"):
            stats = row[implementation]

            lines.append(
                f"| {row['operation']}"
                f" | {implementation}"
                f" | {stats['minimum_ns']}"
                f" | {stats['median_ns']:.2f}"
                f" | {stats['mean_ns']:.2f}"
                f" | {stats['maximum_ns']}"
                f" | {stats['standard_deviation_ns']:.2f}"
                f" | {stats['samples']} |"
            )

    lines.extend([
        "",
        "## Paired comparison interpretation",
        "",
        "Positive median difference means the independent implementation took longer.",
        "Production win rate is the fraction of paired samples where production was faster.",
        "Ties are reported separately and are not counted as production wins.",
        "The median ratio is independent median divided by production median.",
        "Production reduction is measured relative to the independent median.",
        "",
        "## World-record and literature comparison",
        "",
        "No universal world-record registry exists for the exact P2 workload.",
        "",
        "| Literature source | Published scope | P2 status |",
        "|---|---|---|",
        "| [TEST-SOURCE](https://example.org/test) | Test-only scope. | Not a directly comparable record. |",
        "",
        "## Methodology",
        "",
        "Paired production and independent measurements.",
        "",
        "## Interpretation and limitations",
        "",
        "Canonical four-qubit workload only.",
        "",
        "## Generated evidence",
        "",
        "- `benchmark_report.json`",
        "- `benchmark_results.csv`",
        "- `environment.txt`",
        "",
        f"**Overall numerical status: {report['status']}**",
        "",
    ])

    return "\n".join(lines)


def make_environment() -> str:
    return "\n".join([
        "P2 BENCHMARK ENVIRONMENT",
        "captured_at_utc: 2026-10-20T12:00:00+00:00",
        "python_version: 3.11.17",
        "numpy_version: 2.2.6",
        "pennylane_version: 0.41.1",
        "scipy_version: 1.15.3",
        "operating_system: Linux",
        "machine: x86_64",
        "cpu_model: Test CPU",
        "logical_cpu_count: 4",
        "benchmark_timer: time.perf_counter_ns",
        "qubit_count: 4",
        "hilbert_dimension: 16",
        "canonical_memberships: [0.85, 0.9, 0.45, 0.7]",
        "",
    ])


def write_evidence(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    report = make_report()

    (directory / "benchmark_report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    with (directory / "benchmark_results.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=CSV_FIELDS,
        )
        writer.writeheader()

        for row in report["operations"]:
            writer.writerow({
                field: row[field]
                for field in CSV_FIELDS
            })

    (directory / "BENCHMARK_RESULTS.md").write_text(
        make_markdown(report),
        encoding="utf-8",
    )

    (directory / "environment.txt").write_text(
        make_environment(),
        encoding="utf-8",
    )

    return report


def test_paired_report_is_accepted():
    assert VALIDATOR.validate_report(make_report()) == []


def test_validator_rejects_old_benchmark_identifier():
    report = make_report()
    report["benchmark_id"] = "P2-CANONICAL-4Q-NUMERICAL-OPERATIONS"

    assert any(
        "identifier" in error.lower()
        for error in VALIDATOR.validate_report(report)
    )


def test_validator_rejects_missing_independent_statistics():
    report = make_report()
    del report["operations"][0]["independent"]

    errors = VALIDATOR.validate_report(report)

    assert any(
        "independent" in error.lower()
        for error in errors
    )


def test_validator_rejects_missing_paired_samples():
    report = make_report()
    del report["operations"][0]["paired_samples"]

    errors = VALIDATOR.validate_report(report)

    assert any(
        "paired_samples" in error
        for error in errors
    )


def test_validator_rejects_non_alternating_order():
    report = make_report()
    report["operations"][0]["paired_samples"][1][
        "first_execution"
    ] = "production"

    errors = VALIDATOR.validate_report(report)

    assert any(
        "did not alternate" in error
        for error in errors
    )


def test_validator_rejects_incorrect_paired_difference():
    report = make_report()
    report["operations"][0]["paired_samples"][0][
        "difference_independent_minus_production_ns"
    ] = 999

    errors = VALIDATOR.validate_report(report)

    assert any(
        "paired difference is inconsistent" in error
        for error in errors
    )


def test_validator_rejects_wrong_production_total():
    report = make_report()
    report["production_total_execution_seconds"] += 1.0

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Production total execution time" in error
        for error in errors
    )


def test_validator_rejects_wrong_independent_total():
    report = make_report()
    report["independent_total_execution_seconds"] += 1.0

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Independent total execution time" in error
        for error in errors
    )


def test_validator_rejects_wrong_combined_total():
    report = make_report()
    report["combined_timed_execution_seconds"] += 1.0

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Combined timed execution total" in error
        for error in errors
    )


def test_validator_rejects_fabricated_world_record():
    report = make_report()
    record = report["operations"][0]["world_record"]
    record["status"] = "VERIFIED_COMPARABLE_RECORD"
    record["verified_value_ns"] = 1

    errors = VALIDATOR.validate_report(report)

    assert any(
        "verified record requires structured source" in error.lower()
        for error in errors
    )


def test_validator_rejects_missing_world_record():
    report = make_report()
    report["operations"][0]["world_record"] = None

    errors = VALIDATOR.validate_report(report)

    assert any(
        "world-record metadata is missing" in error
        for error in errors
    )


def test_csv_accepts_production_statistics(tmp_path: Path):
    report = make_report()
    directory = tmp_path
    write_evidence(directory)

    assert VALIDATOR.validate_csv(
        directory / "benchmark_results.csv",
        report,
    ) == []


def test_csv_rejects_mismatch_with_json(tmp_path: Path):
    report = make_report()
    write_evidence(tmp_path)

    path = tmp_path / "benchmark_results.csv"

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as stream:
        rows = list(csv.DictReader(stream))

    rows[0]["median_ns"] = "999999"

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    errors = VALIDATOR.validate_csv(path, report)

    assert any(
        "CSV/JSON production median_ns mismatch" in error
        for error in errors
    )


def test_markdown_accepts_all_timing_tables(tmp_path: Path):
    report = make_report()
    path = tmp_path / "BENCHMARK_RESULTS.md"

    path.write_text(
        make_markdown(report),
        encoding="utf-8",
    )

    assert VALIDATOR.validate_markdown(path, report) == []


def test_markdown_rejects_missing_full_timing_row(tmp_path: Path):
    report = make_report()
    content = make_markdown(report)

    content = content.replace(
        "| rotation_operator | independent |",
        "| rotation_operator | missing |",
    )

    path = tmp_path / "BENCHMARK_RESULTS.md"
    path.write_text(content, encoding="utf-8")

    errors = VALIDATOR.validate_markdown(path, report)

    assert any(
        "full timing row is missing" in error
        for error in errors
    )


def test_complete_paired_evidence_is_accepted(tmp_path: Path):
    write_evidence(tmp_path)

    assert VALIDATOR.validate_results(
        make_test_contract(tmp_path)
    ) == []


def test_complete_evidence_rejects_missing_markdown(tmp_path: Path):
    write_evidence(tmp_path)
    (tmp_path / "BENCHMARK_RESULTS.md").unlink()

    errors = VALIDATOR.validate_results(
        make_test_contract(tmp_path)
    )

    assert any(
        "Markdown report does not exist" in error
        for error in errors
    )


def test_complete_evidence_rejects_missing_environment(tmp_path: Path):
    write_evidence(tmp_path)
    (tmp_path / "environment.txt").unlink()

    errors = VALIDATOR.validate_results(
        make_test_contract(tmp_path)
    )

    assert any(
        "environment file does not exist" in error
        for error in errors
    )


def test_complete_evidence_rejects_old_json_schema(tmp_path: Path):
    write_evidence(tmp_path)

    path = tmp_path / "benchmark_report.json"
    report = json.loads(path.read_text(encoding="utf-8"))

    report["benchmark_id"] = (
        "P2-CANONICAL-4Q-NUMERICAL-OPERATIONS"
    )

    path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    errors = VALIDATOR.validate_results(
        make_test_contract(tmp_path)
    )

    assert any(
        "identifier" in error.lower()
        for error in errors
    )


def test_validator_rejects_non_object_report():
    for invalid in (None, [], "invalid", 1):
        assert VALIDATOR.validate_report(invalid)


def test_validator_rejects_missing_operation():
    report = make_report()
    report["operations"].pop()

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Missing benchmark operations" in error
        for error in errors
    )


def test_validator_rejects_duplicate_operation():
    report = make_report()
    report["operations"].append(
        dict(report["operations"][0])
    )

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Duplicate benchmark operation" in error
        for error in errors
    )


def test_validator_rejects_failed_operation():
    report = make_report()
    report["operations"][0]["passed"] = False

    errors = VALIDATOR.validate_report(report)

    assert any(
        "numerical validation failed" in error
        for error in errors
    )


def test_validator_rejects_invalid_total_runtime():
    report = make_report()
    report["total_runtime_seconds"] = float("nan")

    errors = VALIDATOR.validate_report(report)

    assert any(
        "total_runtime_seconds" in error
        for error in errors
    )


def test_validator_rejects_runtime_below_measured_work():
    report = make_report()
    report["total_runtime_seconds"] = 0.000001

    errors = VALIDATOR.validate_report(report)

    assert any(
        "below combined timed execution" in error
        for error in errors
    )


def test_validator_rejects_missing_paired_metadata():
    report = make_report()
    report["independent_reference"]["paired_measurement"] = False

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Paired measurement metadata is missing" in error
        for error in errors
    )


def test_environment_requires_cpu_model(tmp_path: Path):
    path = tmp_path / "environment.txt"
    content = make_environment().replace("cpu_model:", "cpu_name:")
    path.write_text(content, encoding="utf-8")

    errors = VALIDATOR.validate_environment(path)

    assert any(
        "cpu_model" in error
        for error in errors
    )


def test_complete_evidence_accepts_custom_artifact_names(tmp_path: Path):
    default_names = {
        "json": "benchmark_report.json",
        "csv": "benchmark_results.csv",
        "markdown": "BENCHMARK_RESULTS.md",
        "environment": "environment.txt",
    }
    custom_names = {
        "json": "custom_report.json",
        "csv": "custom_results.csv",
        "markdown": "custom_results.md",
        "environment": "custom_environment.txt",
    }

    write_evidence(tmp_path)
    contract = make_test_contract(tmp_path, custom_names)

    for artifact_type, default_name in default_names.items():
        source = tmp_path / default_name
        destination = contract.artifact_paths[artifact_type]
        source.replace(destination)

    markdown = contract.markdown_path.read_text(encoding="utf-8")
    for artifact_type, default_name in default_names.items():
        markdown = markdown.replace(
            default_name,
            custom_names[artifact_type],
        )
    contract.markdown_path.write_text(markdown, encoding="utf-8")

    assert VALIDATOR.validate_results(contract) == []


def test_cli_rejects_results_directory_that_differs_from_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    contract = make_test_contract(tmp_path)
    wrong_results = tmp_path / "wrong-results"

    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_benchmark.py",
            "--config",
            str(contract.config_path),
            "--results",
            str(wrong_results),
            "--keep-cache",
        ],
    )

    exit_code = VALIDATOR.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "--results directory does not match" in captured.out
    assert "VERDICT: BENCHMARK_REJECTED" in captured.out
