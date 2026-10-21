"""Fail-closed validator for the paired QFLPN P2 benchmark evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import statistics
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent

JSON_FILENAME = "benchmark_report.json"
CSV_FILENAME = "benchmark_results.csv"
MARKDOWN_FILENAME = "BENCHMARK_RESULTS.md"
ENVIRONMENT_FILENAME = "environment.txt"

EXPECTED_BENCHMARK_ID = "P2-CANONICAL-4Q-PAIRED-OPERATIONS"
EXPECTED_SCHEMA_VERSION = 1

EXPECTED_OPERATIONS = (
    "rotation_operator",
    "c3x_operator",
    "transition_operator",
    "state_evolution",
    "density_matrix",
    "reduced_density_q4",
    "reduced_density_q123",
    "pennylane_execution",
)

EXPECTED_RUNTIME_SCOPE = (
    "Elapsed wall-clock time from benchmark CLI start, before configuration "
    "loading, through the first complete generation of the four evidence "
    "files. Final JSON and Markdown persistence of the measured duration "
    "is excluded to avoid a self-referential timing measurement."
)

EXPECTED_WORLD_RECORD_STATUS = "NO_DIRECTLY_COMPARABLE_RECORD"
EXPECTED_WORLD_RECORD_DISPLAY = (
    "N/A — no verified directly comparable record"
)

CSV_FIELDS = [
    "operation",
    "warmups",
    "repetitions",
    "minimum_ns",
    "median_ns",
    "mean_ns",
    "maximum_ns",
    "standard_deviation_ns",
    "operations_per_second",
    "numerical_error",
    "numerical_tolerance",
    "passed",
]

STAT_FIELDS = (
    "minimum_ns",
    "median_ns",
    "mean_ns",
    "maximum_ns",
    "standard_deviation_ns",
    "samples",
    "operations_per_second",
)

LEGACY_PRODUCTION_FIELDS = (
    "minimum_ns",
    "median_ns",
    "mean_ns",
    "maximum_ns",
    "standard_deviation_ns",
    "operations_per_second",
    "numerical_error",
    "numerical_tolerance",
)


def finite_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def close(
    actual: float,
    expected: float,
    *,
    rel_tol: float = 1e-9,
    abs_tol: float = 1e-9,
) -> bool:
    if not finite_number(actual) or not finite_number(expected):
        return False

    return math.isclose(
        float(actual),
        float(expected),
        rel_tol=rel_tol,
        abs_tol=abs_tol,
    )


def require_number(
    value,
    label: str,
    errors: list[str],
    *,
    minimum: float | None = None,
) -> bool:
    if not finite_number(value):
        errors.append(f"{label}: value must be a finite number.")
        return False

    if minimum is not None and value < minimum:
        errors.append(
            f"{label}: value must be greater than or equal to {minimum}."
        )
        return False

    return True


def validate_statistics(
    stats: object,
    label: str,
    repetitions: int,
    errors: list[str],
) -> list[int] | None:
    if not isinstance(stats, dict):
        errors.append(f"{label}: statistics object is missing.")
        return None

    for field in STAT_FIELDS:
        if field not in stats:
            errors.append(f"{label}: missing statistics field {field}.")

    numeric_fields = (
        "minimum_ns",
        "median_ns",
        "mean_ns",
        "maximum_ns",
        "standard_deviation_ns",
        "operations_per_second",
    )

    valid = True

    for field in numeric_fields:
        if not require_number(
            stats.get(field),
            f"{label}.{field}",
            errors,
            minimum=0,
        ):
            valid = False

    samples = stats.get("samples")

    if type(samples) is not int or samples != repetitions:
        errors.append(
            f"{label}: samples must equal configured repetitions "
            f"({repetitions})."
        )
        valid = False

    if not valid:
        return None

    minimum = stats["minimum_ns"]
    median = stats["median_ns"]
    mean = stats["mean_ns"]
    maximum = stats["maximum_ns"]
    stddev = stats["standard_deviation_ns"]
    throughput = stats["operations_per_second"]

    if minimum <= 0:
        errors.append(f"{label}: minimum timing must be positive.")

    if maximum < minimum:
        errors.append(f"{label}: maximum is below minimum.")

    if not minimum <= median <= maximum:
        errors.append(f"{label}: median is outside the timing range.")

    if not minimum <= mean <= maximum:
        errors.append(f"{label}: mean is outside the timing range.")

    if stddev < 0:
        errors.append(f"{label}: standard deviation cannot be negative.")

    if throughput <= 0:
        errors.append(f"{label}: throughput must be positive.")
    elif not close(
        throughput,
        1_000_000_000.0 / median,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        errors.append(
            f"{label}: throughput does not match median timing."
        )

    return []


def validate_world_record(
    record: object,
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(record, dict):
        errors.append(f"{label}: world-record metadata is missing.")
        return

    display = record.get("display")
    status = record.get("status")
    value = record.get("verified_value_ns")
    source = record.get("source")

    if not isinstance(display, str) or not display.strip():
        errors.append(f"{label}: world-record display is invalid.")

    if status == EXPECTED_WORLD_RECORD_STATUS:
        if display != EXPECTED_WORLD_RECORD_DISPLAY:
            errors.append(
                f"{label}: unverified record must use the explicit N/A label."
            )

        if value is not None:
            errors.append(
                f"{label}: unverified record cannot contain a timing value."
            )

        if source is not None:
            errors.append(
                f"{label}: unverified record cannot claim a source."
            )

        if (
            not isinstance(record.get("reason"), str)
            or not record["reason"].strip()
        ):
            errors.append(
                f"{label}: reason for missing comparable record is required."
            )

        return

    if status == "VERIFIED_COMPARABLE_RECORD":
        if not require_number(
            value,
            f"{label}.verified_value_ns",
            errors,
            minimum=1,
        ):
            return

        if not isinstance(source, dict):
            errors.append(
                f"{label}: verified record requires structured source metadata."
            )
            return

        required_source_fields = (
            "title",
            "authors",
            "year",
            "url",
            "hardware",
            "software",
            "operation",
            "comparability_basis",
        )

        for field in required_source_fields:
            if field not in source or source[field] in (None, "", []):
                errors.append(
                    f"{label}: verified source is missing {field}."
                )

        if (
            not isinstance(source.get("url"), str)
            or not source.get("url", "").startswith("https://")
        ):
            errors.append(
                f"{label}: verified record source URL must use HTTPS."
            )

        if (
            not isinstance(source.get("authors"), list)
            or not source.get("authors")
        ):
            errors.append(
                f"{label}: verified record must identify its authors."
            )

        if type(source.get("year")) is not int:
            errors.append(
                f"{label}: verified record year must be an integer."
            )

        return

    errors.append(f"{label}: unsupported world-record status.")


def validate_paired_samples(
    row: dict,
    label: str,
    repetitions: int,
    expected: object,
    tolerance: float,
    errors: list[str],
) -> tuple[list[int] | None, list[int] | None]:
    samples = row.get("paired_samples")

    if not isinstance(samples, list):
        errors.append(f"{label}: paired_samples must be a list.")
        return None, None

    if len(samples) != repetitions:
        errors.append(
            f"{label}: paired sample count does not equal repetitions."
        )
        return None, None

    production_times: list[int] = []
    independent_times: list[int] = []

    for index, sample in enumerate(samples):
        prefix = f"{label}.paired_samples[{index}]"

        if not isinstance(sample, dict):
            errors.append(f"{prefix}: sample must be an object.")
            continue

        if sample.get("sample_index") != index + 1:
            errors.append(f"{prefix}: sample index is not sequential.")

        expected_first = (
            "production" if index % 2 == 0 else "independent"
        )

        if sample.get("first_execution") != expected_first:
            errors.append(
                f"{prefix}: execution order did not alternate."
            )

        production_ns = sample.get("production_ns")
        independent_ns = sample.get("independent_ns")
        difference = sample.get(
            "difference_independent_minus_production_ns"
        )

        if type(production_ns) is not int or production_ns <= 0:
            errors.append(
                f"{prefix}: production duration must be a positive integer."
            )
            continue

        if type(independent_ns) is not int or independent_ns <= 0:
            errors.append(
                f"{prefix}: independent duration must be a positive integer."
            )
            continue

        if type(difference) is not int:
            errors.append(
                f"{prefix}: paired difference must be an integer."
            )
        elif difference != independent_ns - production_ns:
            errors.append(
                f"{prefix}: paired difference is inconsistent."
            )

        production_times.append(production_ns)
        independent_times.append(independent_ns)

    if (
        len(production_times) != repetitions
        or len(independent_times) != repetitions
    ):
        return None, None

    return production_times, independent_times


def validate_operation(
    row: object,
    index: int,
    warmups: int,
    repetitions: int,
    tolerance: float,
    errors: list[str],
) -> tuple[str | None, int, int]:
    prefix = f"operations[{index}]"

    if not isinstance(row, dict):
        errors.append(f"{prefix}: operation record must be an object.")
        return None, 0, 0

    name = row.get("operation")

    if not isinstance(name, str) or not name:
        errors.append(f"{prefix}: operation name is invalid.")
        return None, 0, 0

    if row.get("passed") is not True:
        errors.append(f"{name}: operation numerical validation failed.")

    if row.get("warmups") != warmups:
        errors.append(f"{name}: warmup count mismatch.")

    if row.get("repetitions") != repetitions:
        errors.append(f"{name}: repetition count mismatch.")

    production = row.get("production")
    independent = row.get("independent")
    paired = row.get("paired_comparison")

    validate_statistics(
        production,
        f"{name}.production",
        repetitions,
        errors,
    )

    validate_statistics(
        independent,
        f"{name}.independent",
        repetitions,
        errors,
    )

    production_error = row.get("numerical_error")
    independent_error = row.get("independent_numerical_error")

    if require_number(
        production_error,
        f"{name}.numerical_error",
        errors,
        minimum=0,
    ):
        if production_error > tolerance:
            errors.append(
                f"{name}: production numerical error exceeds tolerance."
            )

    if require_number(
        independent_error,
        f"{name}.independent_numerical_error",
        errors,
        minimum=0,
    ):
        if independent_error > tolerance:
            errors.append(
                f"{name}: independent numerical error exceeds tolerance."
            )

    if row.get("independent_passed") is not True:
        errors.append(
            f"{name}: independent numerical validation did not pass."
        )

    if not isinstance(paired, dict):
        errors.append(f"{name}: paired comparison object is missing.")
        paired = {}

    paired_fields = (
        "median_difference_independent_minus_production_ns",
        "production_win_count",
        "tie_count",
        "production_win_rate_percent",
        "independent_over_production_median_ratio",
        "production_reduction_percent_vs_independent",
    )

    for field in paired_fields:
        if field not in paired:
            errors.append(
                f"{name}: paired comparison is missing {field}."
            )

    samples_production, samples_independent = validate_paired_samples(
        row,
        name,
        repetitions,
        None,
        tolerance,
        errors,
    )

    production_total = 0
    independent_total = 0

    if samples_production is not None:
        production_total = sum(samples_production)
        independent_total = sum(samples_independent)

        if isinstance(production, dict):
            checks = {
                "minimum_ns": min(samples_production),
                "median_ns": statistics.median(samples_production),
                "mean_ns": statistics.mean(samples_production),
                "maximum_ns": max(samples_production),
                "standard_deviation_ns": statistics.pstdev(
                    samples_production
                ),
            }

            for field, expected_value in checks.items():
                actual = production.get(field)

                if not finite_number(actual) or not close(
                    actual,
                    expected_value,
                    rel_tol=1e-9,
                    abs_tol=1e-6,
                ):
                    errors.append(
                        f"{name}: production {field} does not match raw samples."
                    )

        if isinstance(independent, dict):
            checks = {
                "minimum_ns": min(samples_independent),
                "median_ns": statistics.median(samples_independent),
                "mean_ns": statistics.mean(samples_independent),
                "maximum_ns": max(samples_independent),
                "standard_deviation_ns": statistics.pstdev(
                    samples_independent
                ),
            }

            for field, expected_value in checks.items():
                actual = independent.get(field)

                if not finite_number(actual) or not close(
                    actual,
                    expected_value,
                    rel_tol=1e-9,
                    abs_tol=1e-6,
                ):
                    errors.append(
                        f"{name}: independent {field} does not match raw samples."
                    )

        if isinstance(paired, dict):
            differences = [
                independent_ns - production_ns
                for production_ns, independent_ns in zip(
                    samples_production,
                    samples_independent,
                )
            ]

            wins = sum(
                production_ns < independent_ns
                for production_ns, independent_ns in zip(
                    samples_production,
                    samples_independent,
                )
            )

            ties = sum(
                production_ns == independent_ns
                for production_ns, independent_ns in zip(
                    samples_production,
                    samples_independent,
                )
            )

            expected_paired = {
                "median_difference_independent_minus_production_ns": (
                    statistics.median(differences)
                ),
                "production_win_count": wins,
                "tie_count": ties,
                "production_win_rate_percent": (
                    wins / repetitions * 100.0
                ),
            }

            for field, expected_value in expected_paired.items():
                actual = paired.get(field)

                if not finite_number(actual) or not close(
                    actual,
                    expected_value,
                    rel_tol=1e-9,
                    abs_tol=1e-6,
                ):
                    errors.append(
                        f"{name}: paired {field} does not match raw samples."
                    )

            if isinstance(production, dict) and isinstance(
                independent, dict
            ):
                production_median = production.get("median_ns")
                independent_median = independent.get("median_ns")

                if (
                    finite_number(production_median)
                    and production_median > 0
                    and finite_number(independent_median)
                ):
                    ratio = independent_median / production_median

                    reduction = (
                        (independent_median - production_median)
                        / independent_median
                        * 100.0
                    )

                    if not close(
                        paired.get(
                            "independent_over_production_median_ratio"
                        ),
                        ratio,
                    ):
                        errors.append(
                            f"{name}: independent/production median ratio is inconsistent."
                        )

                    if not close(
                        paired.get(
                            "production_reduction_percent_vs_independent"
                        ),
                        reduction,
                    ):
                        errors.append(
                            f"{name}: production reduction is inconsistent."
                        )

    validate_world_record(
        row.get("world_record"),
        name,
        errors,
    )

    return name, production_total, independent_total


def validate_report(report: object) -> list[str]:
    errors: list[str] = []

    if not isinstance(report, dict):
        return ["Benchmark report root must be a JSON object."]

    if report.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        errors.append("Unsupported benchmark report schema.")

    if report.get("benchmark_id") != EXPECTED_BENCHMARK_ID:
        errors.append("Unexpected benchmark identifier.")

    if report.get("project") != "QFLPN P2":
        errors.append("Unexpected benchmark project.")

    if report.get("qubits") != 4:
        errors.append("Benchmark must use four qubits.")

    if report.get("hilbert_dimension") != 16:
        errors.append("Benchmark dimension must be 16.")

    if report.get("basis_order") != "big-endian":
        errors.append("Benchmark basis order is invalid.")

    if report.get("operator_order") != "U = C3X @ U_rot":
        errors.append("Benchmark operator order is invalid.")

    if report.get("activation_vector") != [0.85, 0.9, 0.45, 0.7]:
        errors.append("Benchmark activation vector is not canonical.")

    if report.get("timer") != "time.perf_counter_ns":
        errors.append("Benchmark timer is invalid.")

    if report.get("runtime_measurement_scope") != EXPECTED_RUNTIME_SCOPE:
        errors.append("Benchmark runtime measurement scope is invalid.")

    warmups = report.get("warmups")
    repetitions = report.get("repetitions")
    tolerance = report.get("numerical_tolerance")

    if type(warmups) is not int or warmups < 5:
        errors.append("Benchmark requires at least five warmups.")

    if type(repetitions) is not int or repetitions < 30:
        errors.append("Benchmark requires at least 30 repetitions.")

    if not finite_number(tolerance) or tolerance <= 0:
        errors.append("Benchmark numerical tolerance is invalid.")
        tolerance = 1e-12

    for field in (
        "total_runtime_seconds",
        "production_total_execution_seconds",
        "independent_total_execution_seconds",
        "combined_timed_execution_seconds",
        "initial_evidence_generation_seconds",
    ):
        require_number(
            report.get(field),
            f"report.{field}",
            errors,
            minimum=0,
        )

    runtime = report.get("total_runtime_seconds")
    production_total = report.get(
        "production_total_execution_seconds"
    )
    independent_total = report.get(
        "independent_total_execution_seconds"
    )
    combined_total = report.get(
        "combined_timed_execution_seconds"
    )
    evidence_time = report.get(
        "initial_evidence_generation_seconds"
    )

    if finite_number(runtime) and runtime <= 0:
        errors.append("Total benchmark runtime must be positive.")

    if finite_number(evidence_time) and finite_number(runtime):
        if evidence_time > runtime:
            errors.append(
                "Initial evidence-generation time exceeds total runtime."
            )

    if (
        finite_number(production_total)
        and finite_number(independent_total)
        and finite_number(combined_total)
        and not close(
            combined_total,
            production_total + independent_total,
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
    ):
        errors.append(
            "Combined timed execution total does not equal production "
            "plus independent totals."
        )

    parity_error = report.get(
        "pennylane_numpy_maximum_difference"
    )

    if (
        not finite_number(parity_error)
        or parity_error < 0
        or parity_error > tolerance
    ):
        errors.append("PennyLane/NumPy parity check failed.")

    reference = report.get("independent_reference")

    if not isinstance(reference, dict):
        errors.append("Independent reference metadata is missing.")
    else:
        if reference.get("used_for_timed_operation_checks") is not True:
            errors.append(
                "Independent references were not used for timed checks."
            )

        if reference.get("paired_measurement") is not True:
            errors.append(
                "Paired measurement metadata is missing."
            )

    rows = report.get("operations")

    if not isinstance(rows, list):
        errors.append("Benchmark operations must be a list.")
        rows = []

    observed: set[str] = set()
    summed_production_ns = 0
    summed_independent_ns = 0

    if (
        type(warmups) is int
        and type(repetitions) is int
        and finite_number(tolerance)
    ):
        for index, row in enumerate(rows):
            name, production_ns, independent_ns = validate_operation(
                row,
                index,
                warmups,
                repetitions,
                tolerance,
                errors,
            )

            if name is not None:
                if name in observed:
                    errors.append(
                        f"Duplicate benchmark operation: {name}"
                    )

                observed.add(name)

            summed_production_ns += production_ns
            summed_independent_ns += independent_ns

    missing = set(EXPECTED_OPERATIONS) - observed
    extra = observed - set(EXPECTED_OPERATIONS)

    if missing:
        errors.append(
            "Missing benchmark operations: "
            + ", ".join(sorted(missing))
        )

    if extra:
        errors.append(
            "Unexpected benchmark operations: "
            + ", ".join(sorted(extra))
        )

    if len(rows) != len(EXPECTED_OPERATIONS):
        errors.append(
            "Benchmark must contain exactly eight operation records."
        )

    if finite_number(production_total):
        expected_total = summed_production_ns / 1_000_000_000.0

        if not close(
            production_total,
            expected_total,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            errors.append(
                "Production total execution time does not equal "
                "the sum of raw production samples."
            )

    if finite_number(independent_total):
        expected_total = summed_independent_ns / 1_000_000_000.0

        if not close(
            independent_total,
            expected_total,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            errors.append(
                "Independent total execution time does not equal "
                "the sum of raw independent samples."
            )

    if finite_number(runtime) and finite_number(combined_total):
        if runtime + 1e-9 < combined_total:
            errors.append(
                "Total benchmark runtime is below combined timed execution."
            )

    literature = report.get("literature_benchmarks")

    if not isinstance(literature, list) or not literature:
        errors.append("Literature benchmark metadata is missing.")
    else:
        for index, source in enumerate(literature):
            label = f"literature_benchmarks[{index}]"

            if not isinstance(source, dict):
                errors.append(f"{label}: source must be an object.")
                continue

            for field in ("id", "title", "venue", "scope", "url"):
                if (
                    not isinstance(source.get(field), str)
                    or not source[field]
                ):
                    errors.append(
                        f"{label}: missing or invalid {field}."
                    )

            if not str(source.get("url", "")).startswith("https://"):
                errors.append(f"{label}: URL must use HTTPS.")

    if report.get("all_checks_pass") is not True:
        errors.append("all_checks_pass must be true.")

    if report.get("status") != "PASS":
        errors.append("Benchmark status must be PASS.")

    return errors


def validate_csv(path: Path, report: dict | None = None) -> list[str]:
    errors: list[str] = []

    if not path.is_file():
        return [f"Benchmark CSV does not exist: {path}"]

    try:
        with path.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as stream:
            reader = csv.DictReader(stream)

            if reader.fieldnames != CSV_FIELDS:
                return [
                    "Benchmark CSV header does not match the required schema."
                ]

            rows = list(reader)

    except (OSError, UnicodeError, csv.Error) as exc:
        return [f"Cannot read benchmark CSV: {exc}"]

    names = [row.get("operation") for row in rows]

    if len(names) != len(set(names)):
        errors.append("Benchmark CSV contains duplicate operations.")

    if set(names) != set(EXPECTED_OPERATIONS):
        errors.append("Benchmark CSV operation set is incomplete or invalid.")

    csv_by_name = {
        row.get("operation"): row
        for row in rows
    }

    for row in rows:
        name = row.get("operation") or "<unknown>"

        # Fail closed without calling .lower() on None or a non-string.
        passed_value = row.get("passed")

        if (
            not isinstance(passed_value, str)
            or passed_value.strip().lower() != "true"
        ):
            errors.append(f"{name}: CSV numerical status is not PASS.")

        parsed = {}

        for field in LEGACY_PRODUCTION_FIELDS:
            try:
                value = float(row[field])
            except (KeyError, TypeError, ValueError):
                errors.append(
                    f"{name}: invalid CSV field {field}."
                )
                continue

            if not math.isfinite(value):
                errors.append(
                    f"{name}: non-finite CSV field {field}."
                )
                continue

            parsed[field] = value

        if len(parsed) != len(LEGACY_PRODUCTION_FIELDS):
            continue

        if parsed["minimum_ns"] <= 0:
            errors.append(f"{name}: CSV minimum time must be positive.")

        if parsed["maximum_ns"] < parsed["minimum_ns"]:
            errors.append(f"{name}: CSV maximum is below minimum.")

        if not (
            parsed["minimum_ns"]
            <= parsed["median_ns"]
            <= parsed["maximum_ns"]
        ):
            errors.append(
                f"{name}: CSV median is outside the timing range."
            )

        if not (
            parsed["minimum_ns"]
            <= parsed["mean_ns"]
            <= parsed["maximum_ns"]
        ):
            errors.append(
                f"{name}: CSV mean is outside the timing range."
            )

        if parsed["standard_deviation_ns"] < 0:
            errors.append(
                f"{name}: CSV standard deviation is negative."
            )

        if parsed["numerical_error"] < 0:
            errors.append(f"{name}: CSV numerical error is negative.")

        if parsed["numerical_tolerance"] <= 0:
            errors.append(f"{name}: CSV tolerance must be positive.")

        if parsed["numerical_error"] > parsed["numerical_tolerance"]:
            errors.append(
                f"{name}: CSV numerical error exceeds tolerance."
            )

        if parsed["operations_per_second"] <= 0:
            errors.append(f"{name}: CSV throughput must be positive.")
        elif not close(
            parsed["operations_per_second"],
            1_000_000_000.0 / parsed["median_ns"],
        ):
            errors.append(
                f"{name}: CSV throughput does not match median."
            )

    if report is not None and isinstance(report, dict):
        raw_report_rows = report.get("operations", [])

        report_rows = {
            row["operation"]: row
            for row in raw_report_rows
            if isinstance(row, dict)
            and isinstance(row.get("operation"), str)
        } if isinstance(raw_report_rows, list) else {}

        if set(report_rows) != set(csv_by_name):
            errors.append("CSV and JSON operation sets differ.")
        else:
            for name in EXPECTED_OPERATIONS:
                json_row = report_rows[name]
                csv_row = csv_by_name[name]
                production = json_row.get("production")

                if not isinstance(production, dict):
                    errors.append(
                        f"{name}: JSON production statistics are missing."
                    )
                    continue

                for field in ("warmups", "repetitions"):
                    try:
                        csv_value = int(csv_row[field])
                    except (KeyError, TypeError, ValueError):
                        errors.append(
                            f"{name}: invalid CSV {field}."
                        )
                        continue

                    if csv_value != json_row.get(field):
                        errors.append(
                            f"{name}: CSV/JSON {field} mismatch."
                        )

                for field in (
                    "minimum_ns",
                    "median_ns",
                    "mean_ns",
                    "maximum_ns",
                    "standard_deviation_ns",
                    "operations_per_second",
                ):
                    try:
                        csv_value = float(csv_row[field])
                    except (KeyError, TypeError, ValueError):
                        errors.append(
                            f"{name}: invalid CSV field {field}."
                        )
                        continue

                    json_value = production.get(field)

                    if not finite_number(json_value) or not close(
                        csv_value,
                        json_value,
                        rel_tol=1e-12,
                        abs_tol=1e-9,
                    ):
                        errors.append(
                            f"{name}: CSV/JSON production {field} mismatch."
                        )

                for csv_field, json_field in (
                    ("numerical_error", "numerical_error"),
                    ("numerical_tolerance", "numerical_tolerance"),
                ):
                    try:
                        csv_value = float(csv_row[csv_field])
                    except (KeyError, TypeError, ValueError):
                        errors.append(
                            f"{name}: invalid CSV field {csv_field}."
                        )
                        continue

                    json_value = json_row.get(json_field)

                    if not finite_number(json_value) or not close(
                        csv_value,
                        json_value,
                    ):
                        errors.append(
                            f"{name}: CSV/JSON {csv_field} mismatch."
                        )

                csv_passed = csv_row.get("passed")
                csv_is_passed = (
                    isinstance(csv_passed, str)
                    and csv_passed.strip().lower() == "true"
                )

                if csv_is_passed != (json_row.get("passed") is True):
                    errors.append(
                        f"{name}: CSV/JSON passed status mismatch."
                    )

    return errors


def markdown_number_matches(
    content: str,
    label: str,
    value: float,
    errors: list[str],
    digits: int,
) -> None:
    expected = f"**{value:.{digits}f} seconds**"

    matches = [
        line for line in content.splitlines()
        if line.startswith(label)
    ]

    if len(matches) != 1:
        errors.append(
            f"Markdown must contain exactly one {label.strip()} value."
        )
        return

    if expected not in matches[0]:
        errors.append(
            f"Markdown {label.strip()} does not match JSON."
        )


def validate_markdown(
    path: Path,
    report: dict | None = None,
) -> list[str]:
    if not path.is_file():
        return [f"Benchmark Markdown report does not exist: {path}"]

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"Cannot read benchmark Markdown report: {exc}"]

    errors: list[str] = []

    required_sections = (
        "# QFLPN P2 — Benchmark Results",
        "## Numerical parity",
        "## Paired operation measurements",
        "## Full timing statistics",
        "## Paired comparison interpretation",
        "## World-record and literature comparison",
        "## Methodology",
        "## Interpretation and limitations",
        "## Generated evidence",
        "- Total benchmark runtime:",
        "- Total production execution time:",
        "- Total independent execution time:",
        "- Total timed execution time (both implementations):",
        "- Initial evidence-generation time:",
        "- Runtime measurement scope:",
        "World record",
        "benchmark_report.json",
        "benchmark_results.csv",
        "environment.txt",
    )

    for section in required_sections:
        if section not in content:
            errors.append(
                f"Benchmark Markdown is missing required content: {section}"
            )

    if len(content.strip()) < 500:
        errors.append("Benchmark Markdown report is unexpectedly short.")

    if report is None or not isinstance(report, dict):
        return errors

    for label, field, digits in (
        ("- Total benchmark runtime:", "total_runtime_seconds", 6),
        (
            "- Total production execution time:",
            "production_total_execution_seconds",
            9,
        ),
        (
            "- Total independent execution time:",
            "independent_total_execution_seconds",
            9,
        ),
        (
            "- Total timed execution time (both implementations):",
            "combined_timed_execution_seconds",
            9,
        ),
        (
            "- Initial evidence-generation time:",
            "initial_evidence_generation_seconds",
            6,
        ),
    ):
        value = report.get(field)

        if finite_number(value):
            markdown_number_matches(
                content,
                label,
                value,
                errors,
                digits,
            )

    raw_operations = report.get("operations")

    if not isinstance(raw_operations, list):
        errors.append("Markdown validation cannot inspect malformed operations.")
        return errors

    operations = {
        row["operation"]: row
        for row in raw_operations
        if isinstance(row, dict)
        and isinstance(row.get("operation"), str)
    }

    # Every paired summary row must be present and agree with JSON.
    for name in EXPECTED_OPERATIONS:
        row = operations.get(name)

        if row is None:
            continue

        production = row.get("production")
        independent = row.get("independent")
        paired = row.get("paired_comparison")
        world_record = row.get("world_record")

        if not all(
            isinstance(value, dict)
            for value in (production, independent, paired, world_record)
        ):
            errors.append(
                f"Markdown source data is malformed for operation {name}."
            )
            continue

        numeric_fields = (
            production.get("median_ns"),
            independent.get("median_ns"),
            paired.get("production_reduction_percent_vs_independent"),
            paired.get(
                "median_difference_independent_minus_production_ns"
            ),
            paired.get("production_win_rate_percent"),
        )

        if not all(finite_number(value) for value in numeric_fields):
            errors.append(
                f"Markdown numeric source data is invalid for operation {name}."
            )
            continue

        display = world_record.get("display")

        if not isinstance(display, str):
            errors.append(
                f"Markdown world-record display is invalid for {name}."
            )
            continue

        summary_line = (
            f"| {name}"
            f" | {production['median_ns']:.2f}"
            f" | {independent['median_ns']:.2f}"
            f" | {paired['production_reduction_percent_vs_independent']:.3f}"
            f" | {paired['median_difference_independent_minus_production_ns']:.2f}"
            f" | {paired['production_win_rate_percent']:.2f}"
            f" | {display} |"
        )

        if summary_line not in content:
            errors.append(
                f"Markdown paired comparison row is missing or inconsistent: {name}."
            )

        for implementation, stats in (
            ("production", production),
            ("independent", independent),
        ):
            required_numeric = (
                "minimum_ns",
                "median_ns",
                "mean_ns",
                "maximum_ns",
                "standard_deviation_ns",
                "samples",
            )

            if not all(
                finite_number(stats.get(field))
                for field in required_numeric
            ):
                errors.append(
                    f"Markdown timing statistics are invalid: "
                    f"{name}/{implementation}."
                )
                continue

            full_line = (
                f"| {name}"
                f" | {implementation}"
                f" | {stats['minimum_ns']}"
                f" | {stats['median_ns']:.2f}"
                f" | {stats['mean_ns']:.2f}"
                f" | {stats['maximum_ns']}"
                f" | {stats['standard_deviation_ns']:.2f}"
                f" | {stats['samples']} |"
            )

            if full_line not in content:
                errors.append(
                    f"Markdown full timing row is missing or inconsistent: "
                    f"{name}/{implementation}."
                )

    if EXPECTED_WORLD_RECORD_DISPLAY not in content:
        errors.append(
            "Markdown does not explicitly distinguish unavailable world records."
        )

    return errors


def validate_environment(path: Path) -> list[str]:
    if not path.is_file():
        return [f"Benchmark environment file does not exist: {path}"]

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"Cannot read benchmark environment file: {exc}"]

    required_fields = (
        "P2 BENCHMARK ENVIRONMENT",
        "captured_at_utc:",
        "python_version:",
        "numpy_version:",
        "pennylane_version:",
        "scipy_version:",
        "operating_system:",
        "machine:",
        "cpu_model:",
        "logical_cpu_count:",
        "benchmark_timer:",
        "qubit_count:",
        "hilbert_dimension:",
        "canonical_memberships:",
    )

    errors = [
        f"Environment file is missing required field: {field}"
        for field in required_fields
        if field not in content
    ]

    if len(content.strip()) < 200:
        errors.append("Environment file is unexpectedly short.")

    return errors


def remove_benchmark_cache(
    cache_dir: Path | None = None,
) -> list[str]:
    """Remove only P2/benchmarks/__pycache__; fail closed on errors."""

    if cache_dir is None:
        cache_dir = BENCHMARK_DIR / "__pycache__"

    cache_dir = Path(cache_dir)

    if cache_dir.is_symlink():
        return [
            f"Refusing to remove benchmark cache symlink: {cache_dir}"
        ]

    if not cache_dir.exists():
        return []

    if not cache_dir.is_dir():
        return [
            f"Benchmark cache path is not a directory: {cache_dir}"
        ]

    try:
        shutil.rmtree(cache_dir)
    except OSError as exc:
        return [
            f"Cannot remove P2 benchmark cache {cache_dir}: {exc}"
        ]

    if cache_dir.exists() or cache_dir.is_symlink():
        return [
            f"P2 benchmark cache still exists: {cache_dir}"
        ]

    print("P2 benchmark cache: REMOVED")
    return []


def validate_results(results_dir: Path) -> list[str]:
    json_path = results_dir / JSON_FILENAME
    csv_path = results_dir / CSV_FILENAME
    markdown_path = results_dir / MARKDOWN_FILENAME
    environment_path = results_dir / ENVIRONMENT_FILENAME

    try:
        report = json.loads(
            json_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"Cannot read benchmark JSON: {exc}"]

    errors = validate_report(report)

    if isinstance(report, dict):
        errors.extend(validate_csv(csv_path, report))
        errors.extend(validate_markdown(markdown_path, report))
    else:
        errors.extend(validate_csv(csv_path))
        errors.extend(validate_markdown(markdown_path))

    errors.extend(validate_environment(environment_path))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate all paired P2 benchmark evidence files."
    )

    parser.add_argument(
        "--results",
        type=Path,
        default=BENCHMARK_DIR,
        help="Directory containing the four benchmark evidence files.",
    )

    parser.add_argument(
        "--keep-cache",
        action="store_true",
        help="Do not remove P2/benchmarks/__pycache__ before validation.",
    )

    args = parser.parse_args()

    if not args.keep_cache:
        errors = remove_benchmark_cache()

        if errors:
            for error in errors:
                print("FAIL:", error)

            print("VERDICT: BENCHMARK_REJECTED")
            return 1

    errors = validate_results(args.results.resolve())

    for error in errors:
        print("FAIL:", error)

    if errors:
        print("VERDICT: BENCHMARK_REJECTED")
        return 1

    print("Benchmark JSON paired schema: PASS")
    print("Benchmark raw paired samples: PASS")
    print("Benchmark total execution times: PASS")
    print("Benchmark CSV/JSON consistency: PASS")
    print("Benchmark Markdown/JSON consistency: PASS")
    print("Benchmark world-record metadata: PASS")
    print("Benchmark environment: PASS")
    print("Required operations:", len(EXPECTED_OPERATIONS))
    print("VERDICT: BENCHMARK_ACCEPTED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
