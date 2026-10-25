from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from P3.results import generate_benchmark_summary as generator


RUN_ID = "p3-12345-1"


def csv_row() -> dict[str, str]:
    return {
        "timestamp": "2026-10-25T12:00:00+00:00",
        "run_id": RUN_ID,
        "benchmark_id": "QFLPN-100",
        "dimension": "100",
        "non_zero_count": "200",
        "warmup_iterations": "2",
        "measured_iterations": "5",
        "sequential_mean_ms": "10.0",
        "sequential_median_ms": "9.8",
        "sequential_stddev_ms": "0.5",
        "parallel_mean_ms": "5.0",
        "parallel_median_ms": "4.9",
        "parallel_stddev_ms": "0.3",
        "speedup": "2.0",
        "sequential_throughput_states_per_s": "10000.0",
        "parallel_throughput_states_per_s": "20000.0",
        "sequential_expected_error": "0.0",
        "parallel_expected_error": "0.0",
        "max_absolute_error": "0.0",
    }


def report_document(**overrides) -> dict:
    latest = {
        "row": 1,
        "run_id": RUN_ID,
        "dimension": 100,
        "nnz": 200,
        "speedup": 2.0,
        "sequential_mean_ms": 10.0,
        "parallel_mean_ms": 5.0,
        "max_error": 0.0,
    }
    latest.update(overrides)

    return {
        "schema": "qflpn-benchmark-v2",
        "validation": "PASS",
        "records": 1,
        "all_records_valid": True,
        "latest_record": latest,
    }


def write_evidence(
    tmp_path: Path,
    *,
    rows: list[dict[str, str]] | None = None,
    report: dict | None = None,
) -> tuple[Path, Path]:
    csv_path = tmp_path / "benchmark.csv"
    report_path = tmp_path / "validation.json"

    records = rows if rows is not None else [csv_row()]
    fields = list(csv_row())

    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    report_path.write_text(
        json.dumps(
            report if report is not None else report_document(),
            indent=2,
        ),
        encoding="utf-8",
    )

    return csv_path, report_path


def test_summary_accepts_matching_csv_and_json(tmp_path: Path) -> None:
    csv_path, report_path = write_evidence(tmp_path)

    summary = generator.build_summary(
        csv_path,
        report_path,
        expected_run_id=RUN_ID,
    )

    assert f"`{RUN_ID}`" in summary
    assert "Validation: **PASS**" in summary
    assert "2.000000×" in summary
    assert "10000.000" in summary
    assert "20000.000" in summary


def test_summary_rejects_csv_run_id_mismatch(tmp_path: Path) -> None:
    row = csv_row()
    row["run_id"] = "p3-other-run"

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


def test_summary_rejects_json_run_id_mismatch(tmp_path: Path) -> None:
    csv_path, report_path = write_evidence(
        tmp_path,
        report=report_document(run_id="p3-other-run"),
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
        ("dimension", 101),
        ("nnz", 201),
        ("speedup", 3.0),
        ("sequential_mean_ms", 11.0),
        ("parallel_mean_ms", 6.0),
        ("max_error", 1e-5),
    ],
)
def test_summary_rejects_csv_json_metric_mismatch(
    tmp_path: Path,
    field: str,
    value,
) -> None:
    csv_path, report_path = write_evidence(
        tmp_path,
        report=report_document(**{field: value}),
    )

    with pytest.raises(generator.SummaryError):
        generator.build_summary(
            csv_path,
            report_path,
            expected_run_id=RUN_ID,
        )


def test_summary_rejects_duplicate_csv_run_id(tmp_path: Path) -> None:
    row = csv_row()
    csv_path, report_path = write_evidence(
        tmp_path,
        rows=[row, dict(row)],
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


def test_summary_rejects_failed_validation_json(tmp_path: Path) -> None:
    report = report_document()
    report["validation"] = "FAIL"

    csv_path, report_path = write_evidence(
        tmp_path,
        report=report,
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


def test_summary_rejects_nonfinite_csv_metric(tmp_path: Path) -> None:
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


def test_summary_rejects_symlinked_csv(tmp_path: Path) -> None:
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
