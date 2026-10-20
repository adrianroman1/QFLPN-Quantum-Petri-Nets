"""Regression and adversarial tests for the P2 benchmark evidence."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest

P2_ROOT = Path(__file__).resolve().parents[1]

VALIDATOR_PATH = (
    P2_ROOT
    / "benchmarks"
    / "validate_benchmark.py"
)

SPEC = importlib.util.spec_from_file_location(
    "p2_benchmark_validator",
    VALIDATOR_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "Cannot load P2 benchmark validator."
    )

VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

EXPECTED_OPERATIONS = sorted(
    VALIDATOR.EXPECTED_OPERATIONS
)

CSV_FIELDS = VALIDATOR.CSV_FIELDS


def valid_report() -> dict:
    """Return a semantically valid report fixture."""

    rows = []

    for name in EXPECTED_OPERATIONS:
        rows.append(
            {
                "operation": name,
                "warmups": 5,
                "repetitions": 30,
                "minimum_ns": 100,
                "median_ns": 150.0,
                "mean_ns": 160.0,
                "maximum_ns": 250,
                "standard_deviation_ns": 20.0,
                "numerical_error": 1e-14,
                "numerical_tolerance": 1e-12,
                "passed": True,
            }
        )

    return {
        "schema_version": 1,
        "benchmark_id": (
            "P2-CANONICAL-4Q-NUMERICAL-OPERATIONS"
        ),
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
        "environment": {
            "python_version": "3.11.0",
            "numpy_version": "2.0.0",
            "pennylane_version": "0.40.0",
        },
        "independent_reference": {
            "method": "Independent test reference.",
            "used_for_timed_operation_checks": True,
        },
        "pennylane_numpy_maximum_difference": 1e-14,
        "operations": rows,
        "all_checks_pass": True,
        "status": "PASS",
    }


def valid_markdown() -> str:
    return "\n".join(
        [
            "# QFLPN P2 — Benchmark Results",
            "",
            "- Status: PASS",
            "",
            "## Numerical parity",
            "",
            "PennyLane / independent NumPy state difference.",
            "",
            "## Operation measurements",
            "",
            "| Operation | Median |",
            "|---|---:|",
            "| rotation_operator | 150 |",
            "",
            "## Methodology",
            "",
            "Independent references and measured repetitions.",
            "",
            "## Interpretation and limitations",
            "",
            "Canonical four-qubit workload only.",
            "",
            "benchmark_report.json",
            "benchmark_results.csv",
            "environment.txt",
            "",
        ]
    )


def valid_environment() -> str:
    return "\n".join(
        [
            "P2 BENCHMARK ENVIRONMENT",
            "captured_at_utc: 2026-10-20T12:00:00+00:00",
            "python_version: 3.11.0",
            "numpy_version: 2.0.0",
            "pennylane_version: 0.40.0",
            "operating_system: Linux",
            "logical_cpu_count: 4",
            "benchmark_timer: time.perf_counter_ns",
            "qubit_count: 4",
            "hilbert_dimension: 16",
            "canonical_memberships: [0.85, 0.9, 0.45, 0.7]",
            "",
        ]
    )


def write_valid_csv(
    path: Path,
    report: dict,
) -> None:
    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=CSV_FIELDS,
        )
        writer.writeheader()
        writer.writerows(
            report["operations"]
        )


def write_valid_evidence(
    directory: Path,
) -> dict:
    """Create a complete, mutually consistent evidence fixture."""

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = valid_report()

    (directory / "benchmark_report.json").write_text(
        json.dumps(
            report,
            indent=2,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    write_valid_csv(
        directory / "benchmark_results.csv",
        report,
    )

    (
        directory / "BENCHMARK_RESULTS.md"
    ).write_text(
        valid_markdown(),
        encoding="utf-8",
    )

    (
        directory / "environment.txt"
    ).write_text(
        valid_environment(),
        encoding="utf-8",
    )

    return report


def test_valid_benchmark_report_is_accepted():
    assert VALIDATOR.validate_report(
        valid_report()
    ) == []


def test_report_rejects_non_object_root():
    for invalid in (
        None,
        [],
        "invalid",
        1,
    ):
        assert VALIDATOR.validate_report(invalid)


def test_report_rejects_wrong_qubit_count():
    report = valid_report()
    report["qubits"] = 5

    errors = VALIDATOR.validate_report(report)

    assert any(
        "four qubits" in error
        for error in errors
    )


def test_report_rejects_wrong_hilbert_dimension():
    report = valid_report()
    report["hilbert_dimension"] = 32

    errors = VALIDATOR.validate_report(report)

    assert any(
        "dimension must be 16" in error
        for error in errors
    )


def test_report_rejects_noncanonical_activations():
    report = valid_report()
    report["activation_vector"] = [
        0.85,
        0.90,
        0.45,
        0.71,
    ]

    errors = VALIDATOR.validate_report(report)

    assert any(
        "activation vector is not canonical" in error
        for error in errors
    )


def test_report_rejects_wrong_operator_order():
    report = valid_report()
    report["operator_order"] = "U = U_rot @ C3X"

    errors = VALIDATOR.validate_report(report)

    assert any(
        "operator order is invalid" in error
        for error in errors
    )


def test_report_rejects_insufficient_warmups():
    report = valid_report()
    report["warmups"] = 1

    errors = VALIDATOR.validate_report(report)

    assert any(
        "five warmups" in error
        for error in errors
    )


def test_report_rejects_insufficient_repetitions():
    report = valid_report()
    report["repetitions"] = 2

    errors = VALIDATOR.validate_report(report)

    assert any(
        "30 repetitions" in error
        for error in errors
    )


def test_report_rejects_failed_operation():
    report = valid_report()
    report["operations"][0]["passed"] = False

    errors = VALIDATOR.validate_report(report)

    assert any(
        "numerical validation did not pass" in error
        for error in errors
    )


def test_report_rejects_missing_operation():
    report = valid_report()
    report["operations"].pop()

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Missing benchmark operations" in error
        for error in errors
    )


def test_report_rejects_duplicate_operation():
    report = valid_report()
    report["operations"].append(
        dict(report["operations"][0])
    )

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Duplicate benchmark operation" in error
        for error in errors
    )


def test_report_rejects_non_finite_timing():
    report = valid_report()
    report["operations"][0]["median_ns"] = float("nan")

    errors = VALIDATOR.validate_report(report)

    assert any(
        "invalid numeric field median_ns" in error
        for error in errors
    )


def test_report_rejects_negative_standard_deviation():
    report = valid_report()
    report["operations"][0][
        "standard_deviation_ns"
    ] = -1.0

    errors = VALIDATOR.validate_report(report)

    assert any(
        "negative standard deviation" in error
        for error in errors
    )


def test_report_rejects_excessive_numerical_error():
    report = valid_report()
    report["operations"][0]["numerical_error"] = 1e-5

    errors = VALIDATOR.validate_report(report)

    assert any(
        "numerical error exceeds tolerance" in error
        for error in errors
    )


def test_report_rejects_failed_pennylane_parity():
    report = valid_report()
    report[
        "pennylane_numpy_maximum_difference"
    ] = 1e-3

    errors = VALIDATOR.validate_report(report)

    assert any(
        "PennyLane/NumPy parity check failed" in error
        for error in errors
    )


def test_report_rejects_missing_independent_reference():
    report = valid_report()
    report["independent_reference"] = None

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Independent reference metadata is missing" in error
        for error in errors
    )


def test_report_rejects_non_independent_validation():
    report = valid_report()
    report["independent_reference"][
        "used_for_timed_operation_checks"
    ] = False

    errors = VALIDATOR.validate_report(report)

    assert any(
        "Independent references were not used" in error
        for error in errors
    )


def test_report_rejects_non_pass_status():
    report = valid_report()
    report["status"] = "WARNING"

    errors = VALIDATOR.validate_report(report)

    assert any(
        "status must be PASS" in error
        for error in errors
    )


def test_csv_accepts_consistent_rows(tmp_path: Path):
    report = valid_report()
    csv_path = tmp_path / "benchmark_results.csv"

    write_valid_csv(
        csv_path,
        report,
    )

    assert VALIDATOR.validate_csv(
        csv_path,
        report,
    ) == []


def test_csv_rejects_missing_file(tmp_path: Path):
    errors = VALIDATOR.validate_csv(
        tmp_path / "missing.csv"
    )

    assert any(
        "does not exist" in error
        for error in errors
    )


def test_csv_rejects_duplicate_operation(tmp_path: Path):
    report = valid_report()
    csv_path = tmp_path / "benchmark_results.csv"

    rows = list(report["operations"])
    rows.append(dict(rows[0]))

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=CSV_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)

    errors = VALIDATOR.validate_csv(
        csv_path,
        report,
    )

    assert any(
        "duplicate operations" in error
        for error in errors
    )


def test_csv_rejects_nonfinite_value(tmp_path: Path):
    report = valid_report()
    csv_path = tmp_path / "benchmark_results.csv"

    rows = [
        dict(row)
        for row in report["operations"]
    ]
    rows[0]["median_ns"] = "nan"

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=CSV_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)

    errors = VALIDATOR.validate_csv(
        csv_path,
        report,
    )

    assert any(
        "non-finite CSV field median_ns" in error
        for error in errors
    )


def test_csv_rejects_json_mismatch(tmp_path: Path):
    report = valid_report()
    csv_path = tmp_path / "benchmark_results.csv"

    write_valid_csv(
        csv_path,
        report,
    )

    rows = list(report["operations"])
    rows[0]["median_ns"] = 999.0

    report["operations"] = rows

    errors = VALIDATOR.validate_csv(
        csv_path,
        report,
    )

    assert any(
        "CSV/JSON median_ns mismatch" in error
        for error in errors
    )


def test_markdown_accepts_required_sections(tmp_path: Path):
    path = tmp_path / "BENCHMARK_RESULTS.md"

    path.write_text(
        valid_markdown(),
        encoding="utf-8",
    )

    assert VALIDATOR.validate_markdown(path) == []


def test_markdown_rejects_missing_section(tmp_path: Path):
    path = tmp_path / "BENCHMARK_RESULTS.md"

    path.write_text(
        "# Incomplete report\n",
        encoding="utf-8",
    )

    errors = VALIDATOR.validate_markdown(path)

    assert errors


def test_environment_accepts_required_fields(tmp_path: Path):
    path = tmp_path / "environment.txt"

    path.write_text(
        valid_environment(),
        encoding="utf-8",
    )

    assert VALIDATOR.validate_environment(path) == []


def test_environment_rejects_missing_fields(tmp_path: Path):
    path = tmp_path / "environment.txt"

    path.write_text(
        "P2 BENCHMARK ENVIRONMENT\n",
        encoding="utf-8",
    )

    errors = VALIDATOR.validate_environment(path)

    assert errors


def test_complete_evidence_set_is_accepted(tmp_path: Path):
    write_valid_evidence(tmp_path)

    assert VALIDATOR.validate_results(tmp_path) == []


def test_complete_evidence_rejects_missing_markdown(
    tmp_path: Path,
):
    write_valid_evidence(tmp_path)

    (tmp_path / "BENCHMARK_RESULTS.md").unlink()

    errors = VALIDATOR.validate_results(tmp_path)

    assert any(
        "Markdown report does not exist" in error
        for error in errors
    )


def test_complete_evidence_rejects_missing_environment(
    tmp_path: Path,
):
    write_valid_evidence(tmp_path)

    (tmp_path / "environment.txt").unlink()

    errors = VALIDATOR.validate_results(tmp_path)

    assert any(
        "environment file does not exist" in error
        for error in errors
    )


def test_complete_evidence_rejects_json_csv_disagreement(
    tmp_path: Path,
):
    report = write_valid_evidence(tmp_path)

    rows = list(report["operations"])
    rows[0]["median_ns"] = 999.0

    with (
        tmp_path / "benchmark_results.csv"
    ).open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=CSV_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)

    errors = VALIDATOR.validate_results(tmp_path)

    assert any(
        "CSV/JSON median_ns mismatch" in error
        for error in errors
    )
