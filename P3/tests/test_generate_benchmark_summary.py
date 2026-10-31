from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from P3.results import generate_benchmark_summary as generator
from P3.results import validate_benchmark as validator


RUN_ID = "p3-12345-1"

CANONICAL_TIMED_BENCHMARKS = (
    (1_000_000, "QFLPN-1M"),
    (10_000_000, "QFLPN-10M"),
    (70_000_000, "QFLPN-70M"),
    (100_000_000, "QFLPN-100M"),
)


def csv_row(
    dimension: int = 1_000_000,
    *,
    run_id: str = RUN_ID,
    benchmark_id: str | None = None,
) -> dict[str, str]:
    """Build one complete V2 CSV row accepted by the real validator."""

    if benchmark_id is None:
        benchmark_id = validator.expected_benchmark_id(dimension)

    sequential_mean = 10.0
    parallel_mean = 5.0

    return {
        "timestamp": "2026-10-25T12:00:00+00:00",
        "run_id": run_id,
        "benchmark_id": benchmark_id,
        "dimension": str(dimension),
        "non_zero_count": str(2 * dimension),
        "parallelism": "2",
        "threshold": "4096",
        "warmup_iterations": "5",
        "measured_iterations": "10",
        "sequential_mean_ms": str(sequential_mean),
        "sequential_median_ms": "9.8",
        "sequential_stddev_ms": "0.5",
        "parallel_mean_ms": str(parallel_mean),
        "parallel_median_ms": "4.9",
        "parallel_stddev_ms": "0.3",
        "speedup": str(sequential_mean / parallel_mean),
        "sequential_throughput_states_per_s": str(
            dimension / (sequential_mean / 1000.0)
        ),
        "parallel_throughput_states_per_s": str(
            dimension / (parallel_mean / 1000.0)
        ),
        "sequential_expected_error": "0.0",
        "parallel_expected_error": "0.0",
        "max_absolute_error": "0.0",
        "setup_time_ms": "1.0",
        "cpu": "test-cpu",
        "max_jvm_memory_bytes": str(4 * 1024**3),
        "free_jvm_heap_bytes": str(1024**3),
        "java_version": "21",
        "operating_system": "Linux",
        "notes": "automated test fixture",
    }


def write_csv(
    csv_path: Path,
    rows: list[dict[str, str]],
) -> None:
    """Write a CSV using the exact production V2 header."""

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=validator.HEADER,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_evidence(
    tmp_path: Path,
    *,
    rows: list[dict[str, str]] | None = None,
    report_override: dict | None = None,
) -> tuple[Path, Path]:
    """Create CSV evidence and JSON using the production validator."""

    csv_path = tmp_path / "benchmark_results_v2.csv"
    report_path = tmp_path / "validation-report.json"

    records = rows if rows is not None else [csv_row()]

    write_csv(
        csv_path,
        records,
    )

    # Generate the JSON with the actual V2 validator.
    report = validator.validate(csv_path)

    if report_override is not None:
        report = json.loads(json.dumps(report))
        report_override(report)

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    return csv_path, report_path


def test_summary_accepts_matching_csv_and_real_validator_json(
    tmp_path: Path,
) -> None:
    csv_path, report_path = write_evidence(tmp_path)

    summary = generator.build_summary(
        csv_path,
        report_path,
        expected_run_id=RUN_ID,
    )

    assert f"`{RUN_ID}`" in summary
    assert "Validation: **PASS**" in summary
    assert "QFLPN-1M" in summary
    assert "1,000,000" in summary or "1000000" in summary
    assert "2.000000×" in summary
    assert "100000000.000" in summary
    assert "200000000.000" in summary


@pytest.mark.parametrize(
    ("dimension", "benchmark_id"),
    CANONICAL_TIMED_BENCHMARKS,
)
def test_summary_accepts_every_canonical_timed_scale(
    tmp_path: Path,
    dimension: int,
    benchmark_id: str,
) -> None:
    row = csv_row(
        dimension,
        run_id=f"p3-{dimension}-1",
    )

    csv_path, report_path = write_evidence(
        tmp_path,
        rows=[row],
    )

    summary = generator.build_summary(
        csv_path,
        report_path,
        expected_run_id=row["run_id"],
    )

    assert benchmark_id in summary
    assert row["run_id"] in summary
    assert "Validation: **PASS**" in summary


def test_summary_rejects_csv_run_id_mismatch(
    tmp_path: Path,
) -> None:
    row = csv_row(
        run_id="p3-other-run",
    )

    csv_path, report_path = write_evidence(
        tmp_path,
        rows=[row],
    )

    with pytest.raises(generator.SummaryError):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_json_run_id_mismatch(
    tmp_path: Path,
) -> None:
    def alter(report: dict) -> None:
        report["latest_record"]["run_id"] = "p3-other-run"

    csv_path, report_path = write_evidence(
        tmp_path,
        report_override=alter,
    )

    with pytest.raises(
        generator.SummaryError,
        match="run_id",
    ):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dimension", 1_000_001),
        ("nnz", 2_000_001),
        ("speedup", 3.0),
        ("sequential_mean_ms", 11.0),
        ("parallel_mean_ms", 6.0),
        ("max_error", 1e-5),
    ],
)
def test_summary_rejects_csv_json_metric_mismatch(
    tmp_path: Path,
    field: str,
    value: int | float,
) -> None:
    def alter(report: dict) -> None:
        report["latest_record"][field] = value

    csv_path, report_path = write_evidence(
        tmp_path,
        report_override=alter,
    )

    with pytest.raises(generator.SummaryError):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_json_benchmark_id_mismatch(
    tmp_path: Path,
) -> None:
    def alter(report: dict) -> None:
        report["latest_record"]["benchmark_id"] = "QFLPN-10M"

    csv_path, report_path = write_evidence(
        tmp_path,
        report_override=alter,
    )

    with pytest.raises(
        generator.SummaryError,
        match="benchmark_id",
    ):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_duplicate_csv_run_id(
    tmp_path: Path,
) -> None:
    row = csv_row()

    csv_path, report_path = write_evidence(
        tmp_path,
        rows=[
            row,
            dict(row),
        ],
    )

    with pytest.raises(
        generator.SummaryError,
        match="exactly one CSV row",
    ):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_failed_validation_json(
    tmp_path: Path,
) -> None:
    def alter(report: dict) -> None:
        report["validation"] = "FAIL"

    csv_path, report_path = write_evidence(
        tmp_path,
        report_override=alter,
    )

    with pytest.raises(
        generator.SummaryError,
        match="not PASS",
    ):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_report_without_all_records_valid(
    tmp_path: Path,
) -> None:
    def alter(report: dict) -> None:
        report["all_records_valid"] = False

    csv_path, report_path = write_evidence(
        tmp_path,
        report_override=alter,
    )

    with pytest.raises(
        generator.SummaryError,
        match="all records valid",
    ):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_invalid_report_schema(
    tmp_path: Path,
) -> None:
    def alter(report: dict) -> None:
        report["schema"] = "qflpn-benchmark-v3"

    csv_path, report_path = write_evidence(
        tmp_path,
        report_override=alter,
    )

    with pytest.raises(
        generator.SummaryError,
        match="unsupported schema",
    ):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_nonfinite_csv_metric(
    tmp_path: Path,
) -> None:
    row = csv_row()
    row["speedup"] = "NaN"

    csv_path, report_path = write_evidence(
        tmp_path,
        rows=[row],
    )

    with pytest.raises(generator.SummaryError):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_nonfinite_json_metric(
    tmp_path: Path,
) -> None:
    def alter(report: dict) -> None:
        report["latest_record"]["speedup"] = float("inf")

    csv_path, report_path = write_evidence(
        tmp_path,
        report_override=alter,
    )

    # The report writer disallows NaN and infinity.
    # Use a standards-compliant JSON token to test the generator itself.
    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )
    report["latest_record"]["speedup"] = "Infinity"

    report_path.write_text(
        json.dumps(report),
        encoding="utf-8",
    )

    with pytest.raises(generator.SummaryError):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_correctness_fixture_dimension(
    tmp_path: Path,
) -> None:
    row = csv_row(
        12,
        run_id=RUN_ID,
    )

    csv_path = tmp_path / "benchmark.csv"
    report_path = tmp_path / "validation.json"

    # The production validator must reject dimension 12 as timed evidence.
    write_csv(
        csv_path,
        [row],
    )

    with pytest.raises(
        validator.ValidationError,
        match="correctness fixture",
    ):
        validator.validate(csv_path)


@pytest.mark.parametrize(
    "dimension",
    [
        30_000_000,
        50_000_000,
        100,
        4096,
        999_999,
        1_000_001,
    ],
)
def test_summary_rejects_noncanonical_dimensions(
    tmp_path: Path,
    dimension: int,
) -> None:
    row = csv_row(
        dimension,
        run_id=RUN_ID,
        benchmark_id=f"QFLPN-{dimension}",
    )

    csv_path = tmp_path / "benchmark.csv"
    report_path = tmp_path / "validation.json"

    write_csv(
        csv_path,
        [row],
    )

    report_path.write_text(
        json.dumps({
            "schema": "qflpn-benchmark-v2",
            "validation": "PASS",
            "records": 1,
            "all_records_valid": True,
            "latest_record": {
                "run_id": RUN_ID,
                "dimension": dimension,
                "nnz": 2 * dimension,
                "speedup": 2.0,
                "sequential_mean_ms": 10.0,
                "parallel_mean_ms": 5.0,
                "max_error": 0.0,
            },
        }),
        encoding="utf-8",
    )

    with pytest.raises(generator.SummaryError):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_wrong_canonical_identifier(
    tmp_path: Path,
) -> None:
    row = csv_row(
        1_000_000,
        benchmark_id="QFLPN-1000000",
    )

    csv_path = tmp_path / "benchmark.csv"
    report_path = tmp_path / "validation.json"

    write_csv(
        csv_path,
        [row],
    )

    report_path.write_text(
        json.dumps({
            "schema": "qflpn-benchmark-v2",
            "validation": "PASS",
            "records": 1,
            "all_records_valid": True,
            "latest_record": {
                "run_id": RUN_ID,
                "dimension": 1_000_000,
                "nnz": 2_000_000,
                "speedup": 2.0,
                "sequential_mean_ms": 10.0,
                "parallel_mean_ms": 5.0,
                "max_error": 0.0,
            },
        }),
        encoding="utf-8",
    )

    with pytest.raises(
        generator.SummaryError,
        match="canonical catalog",
    ):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_missing_csv_columns(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "benchmark.csv"
    report_path = tmp_path / "validation.json"

    row = csv_row()

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["run_id", "dimension"],
        )
        writer.writeheader()
        writer.writerow({
            "run_id": RUN_ID,
            "dimension": "1000000",
        })

    report_path.write_text(
        json.dumps({
            "schema": "qflpn-benchmark-v2",
            "validation": "PASS",
            "records": 1,
            "all_records_valid": True,
            "latest_record": {
                "run_id": RUN_ID,
                "dimension": 1_000_000,
                "nnz": 2_000_000,
                "speedup": 2.0,
                "sequential_mean_ms": 10.0,
                "parallel_mean_ms": 5.0,
                "max_error": 0.0,
            },
        }),
        encoding="utf-8",
    )

    with pytest.raises(
        generator.SummaryError,
        match="missing columns",
    ):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_symlinked_csv(
    tmp_path: Path,
) -> None:
    real_csv, report_path = write_evidence(tmp_path)

    linked_csv = tmp_path / "linked.csv"
    linked_csv.symlink_to(real_csv)

    with pytest.raises(
        generator.SummaryError,
        match="symlink",
    ):
        generator.build_summary(
            linked_csv,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_symlinked_json_report(
    tmp_path: Path,
) -> None:
    csv_path, real_report = write_evidence(tmp_path)

    linked_report = tmp_path / "linked-report.json"
    linked_report.symlink_to(real_report)

    with pytest.raises(
        generator.SummaryError,
        match="symlink",
    ):
        generator.build_summary(
            csv_path,
            linked_report,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_invalid_run_id(
    tmp_path: Path,
) -> None:
    csv_path, report_path = write_evidence(tmp_path)

    with pytest.raises(
        generator.SummaryError,
        match="unsupported characters",
    ):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id="../invalid-run",
        )


def test_summary_rejects_empty_csv(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "benchmark.csv"
    report_path = tmp_path / "validation.json"

    csv_path.write_text(
        "",
        encoding="utf-8",
    )

    report_path.write_text(
        json.dumps({
            "schema": "qflpn-benchmark-v2",
            "validation": "PASS",
            "records": 1,
            "all_records_valid": True,
            "latest_record": {
                "run_id": RUN_ID,
            },
        }),
        encoding="utf-8",
    )

    with pytest.raises(generator.SummaryError):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_missing_report(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "benchmark.csv"
    report_path = tmp_path / "missing.json"

    write_csv(
        csv_path,
        [csv_row()],
    )

    with pytest.raises(
        generator.SummaryError,
        match="missing",
    ):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_output_is_run_specific(
    tmp_path: Path,
) -> None:
    csv_path, report_path = write_evidence(tmp_path)

    summary = generator.build_summary(
        csv_path,
        report_path,
        expected_run_id=RUN_ID,
    )

    output_path = tmp_path / "benchmark-report.md"

    generator.write_output(
        output_path,
        summary,
        overwrite=True,
    )

    content = output_path.read_text(
        encoding="utf-8"
    )

    assert RUN_ID in content
    assert "QFLPN-1M" in content
    assert "Validation: **PASS**" in content
