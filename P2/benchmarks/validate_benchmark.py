"""Fail-closed validation of the five agreed P2 benchmark files."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent

JSON_FILENAME = "benchmark_report.json"
CSV_FILENAME = "benchmark_results.csv"
MARKDOWN_FILENAME = "BENCHMARK_RESULTS.md"
ENVIRONMENT_FILENAME = "environment.txt"

EXPECTED_OPERATIONS = {
    "rotation_operator",
    "c3x_operator",
    "transition_operator",
    "state_evolution",
    "density_matrix",
    "reduced_density_q4",
    "reduced_density_q123",
    "pennylane_execution",
}

CSV_FIELDS = [
    "operation",
    "warmups",
    "repetitions",
    "minimum_ns",
    "median_ns",
    "mean_ns",
    "maximum_ns",
    "standard_deviation_ns",
    "numerical_error",
    "numerical_tolerance",
    "passed",
]

NUMERIC_FIELDS = (
    "minimum_ns",
    "median_ns",
    "mean_ns",
    "maximum_ns",
    "standard_deviation_ns",
    "numerical_error",
    "numerical_tolerance",
)


def finite_number(value) -> bool:
    """Return true only for finite, non-Boolean numeric values."""

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_report(report: object) -> list[str]:
    """Validate the semantic content of the benchmark JSON."""

    errors: list[str] = []

    if not isinstance(report, dict):
        return [
            "Benchmark report root must be a JSON object."
        ]

    if report.get("schema_version") != 1:
        errors.append(
            "Unsupported benchmark report schema."
        )

    if report.get("benchmark_id") != (
        "P2-CANONICAL-4Q-NUMERICAL-OPERATIONS"
    ):
        errors.append(
            "Unexpected benchmark identifier."
        )

    if report.get("project") != "QFLPN P2":
        errors.append(
            "Unexpected benchmark project."
        )

    if report.get("qubits") != 4:
        errors.append(
            "Benchmark must use four qubits."
        )

    if report.get("hilbert_dimension") != 16:
        errors.append(
            "Benchmark dimension must be 16."
        )

    if report.get("basis_order") != "big-endian":
        errors.append(
            "Benchmark basis order is invalid."
        )

    if report.get("operator_order") != "U = C3X @ U_rot":
        errors.append(
            "Benchmark operator order is invalid."
        )

    activations = report.get("activation_vector")

    if activations != [0.85, 0.9, 0.45, 0.7]:
        errors.append(
            "Benchmark activation vector is not canonical."
        )

    if report.get("timer") != "time.perf_counter_ns":
        errors.append(
            "Benchmark timer is invalid."
        )

    warmups = report.get("warmups")
    repetitions = report.get("repetitions")

    if type(warmups) is not int or warmups < 5:
        errors.append(
            "Benchmark requires at least five warmups."
        )

    if type(repetitions) is not int or repetitions < 30:
        errors.append(
            "Benchmark requires at least 30 repetitions."
        )

    tolerance = report.get("numerical_tolerance")

    if not finite_number(tolerance) or tolerance <= 0:
        errors.append(
            "Benchmark numerical tolerance is invalid."
        )

    parity_error = report.get(
        "pennylane_numpy_maximum_difference"
    )

    if (
        not finite_number(parity_error)
        or not finite_number(tolerance)
        or parity_error > tolerance
    ):
        errors.append(
            "PennyLane/NumPy parity check failed."
        )

    reference = report.get("independent_reference")

    if not isinstance(reference, dict):
        errors.append(
            "Independent reference metadata is missing."
        )
    elif reference.get("used_for_timed_operation_checks") is not True:
        errors.append(
            "Independent references were not used for operation checks."
        )

    rows = report.get("operations")

    if not isinstance(rows, list):
        errors.append(
            "Benchmark operations must be a list."
        )
        rows = []

    observed: set[str] = set()

    for index, row in enumerate(rows):
        prefix = f"operations[{index}]"

        if not isinstance(row, dict):
            errors.append(
                f"{prefix} must be an object."
            )
            continue

        name = row.get("operation")

        if not isinstance(name, str):
            errors.append(
                f"{prefix}.operation must be a string."
            )
            continue

        if name in observed:
            errors.append(
                f"Duplicate benchmark operation: {name}"
            )

        observed.add(name)

        if row.get("passed") is not True:
            errors.append(
                f"{name}: numerical validation did not pass."
            )

        if (
            type(warmups) is int
            and row.get("warmups") != warmups
        ):
            errors.append(
                f"{name}: warmup count mismatch."
            )

        if (
            type(repetitions) is int
            and row.get("repetitions") != repetitions
        ):
            errors.append(
                f"{name}: repetition count mismatch."
            )

        for field in NUMERIC_FIELDS:
            if not finite_number(row.get(field)):
                errors.append(
                    f"{name}: invalid numeric field {field}."
                )

        if all(
            finite_number(row.get(field))
            for field in NUMERIC_FIELDS
        ):
            if row["minimum_ns"] <= 0:
                errors.append(
                    f"{name}: minimum time must be positive."
                )

            if row["maximum_ns"] < row["minimum_ns"]:
                errors.append(
                    f"{name}: maximum is below minimum."
                )

            if not (
                row["minimum_ns"]
                <= row["median_ns"]
                <= row["maximum_ns"]
            ):
                errors.append(
                    f"{name}: median is outside the measured range."
                )

            if not (
                row["minimum_ns"]
                <= row["mean_ns"]
                <= row["maximum_ns"]
            ):
                errors.append(
                    f"{name}: mean is outside the measured range."
                )

            if row["standard_deviation_ns"] < 0:
                errors.append(
                    f"{name}: negative standard deviation."
                )

            if row["numerical_error"] < 0:
                errors.append(
                    f"{name}: negative numerical error."
                )

            if row["numerical_tolerance"] <= 0:
                errors.append(
                    f"{name}: invalid numerical tolerance."
                )

            if (
                row["numerical_error"]
                > row["numerical_tolerance"]
            ):
                errors.append(
                    f"{name}: numerical error exceeds tolerance."
                )

    missing = EXPECTED_OPERATIONS - observed
    extra = observed - EXPECTED_OPERATIONS

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

    if report.get("all_checks_pass") is not True:
        errors.append(
            "all_checks_pass must be true."
        )

    if report.get("status") != "PASS":
        errors.append(
            "Benchmark status must be PASS."
        )

    return errors


def validate_csv(
    path: Path,
    report: dict | None = None,
) -> list[str]:
    """Validate CSV schema, values and consistency with JSON."""

    errors: list[str] = []

    if not path.is_file():
        return [
            f"Benchmark CSV does not exist: {path}"
        ]

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
        return [
            f"Cannot read benchmark CSV: {exc}"
        ]

    names = [
        row.get("operation")
        for row in rows
    ]

    if len(names) != len(set(names)):
        errors.append(
            "Benchmark CSV contains duplicate operations."
        )

    if set(names) != EXPECTED_OPERATIONS:
        errors.append(
            "Benchmark CSV operation set is incomplete or invalid."
        )

    csv_by_name = {
        row.get("operation"): row
        for row in rows
    }

    for row in rows:
        name = row.get("operation", "<unknown>")

        if row.get("passed", "").lower() != "true":
            errors.append(
                f"{name}: CSV numerical status is not PASS."
            )

        parsed: dict[str, float] = {}

        for field in NUMERIC_FIELDS:
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

        if len(parsed) == len(NUMERIC_FIELDS):
            if parsed["minimum_ns"] <= 0:
                errors.append(
                    f"{name}: CSV minimum time must be positive."
                )

            if parsed["maximum_ns"] < parsed["minimum_ns"]:
                errors.append(
                    f"{name}: CSV maximum is below minimum."
                )

            if not (
                parsed["minimum_ns"]
                <= parsed["median_ns"]
                <= parsed["maximum_ns"]
            ):
                errors.append(
                    f"{name}: CSV median is outside the measured range."
                )

            if parsed["standard_deviation_ns"] < 0:
                errors.append(
                    f"{name}: CSV standard deviation is negative."
                )

            if (
                parsed["numerical_error"]
                > parsed["numerical_tolerance"]
            ):
                errors.append(
                    f"{name}: CSV numerical error exceeds tolerance."
                )

    if report is not None:
        report_rows = {
            row["operation"]: row
            for row in report.get("operations", [])
            if isinstance(row, dict)
            and isinstance(row.get("operation"), str)
        }

        if set(report_rows) != set(csv_by_name):
            errors.append(
                "CSV and JSON operation sets differ."
            )
        else:
            for name in sorted(EXPECTED_OPERATIONS):
                json_row = report_rows[name]
                csv_row = csv_by_name[name]

                for field in (
                    "warmups",
                    "repetitions",
                ):
                    try:
                        csv_value = int(csv_row[field])
                    except (KeyError, TypeError, ValueError):
                        continue

                    if csv_value != json_row.get(field):
                        errors.append(
                            f"{name}: CSV/JSON {field} mismatch."
                        )

                for field in NUMERIC_FIELDS:
                    try:
                        csv_value = float(csv_row[field])
                    except (KeyError, TypeError, ValueError):
                        continue

                    json_value = json_row.get(field)

                    if (
                        finite_number(json_value)
                        and not math.isclose(
                            csv_value,
                            float(json_value),
                            rel_tol=1e-12,
                            abs_tol=1e-12,
                        )
                    ):
                        errors.append(
                            f"{name}: CSV/JSON {field} mismatch."
                        )

                if (
                    csv_row.get("passed", "").lower() == "true"
                ) != (json_row.get("passed") is True):
                    errors.append(
                        f"{name}: CSV/JSON passed status mismatch."
                    )

    return errors


def validate_markdown(path: Path) -> list[str]:
    """Check that the human-readable report exists and is substantive."""

    if not path.is_file():
        return [
            f"Benchmark Markdown report does not exist: {path}"
        ]

    try:
        content = path.read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeError) as exc:
        return [
            f"Cannot read benchmark Markdown report: {exc}"
        ]

    required_sections = (
        "# QFLPN P2 — Benchmark Results",
        "## Numerical parity",
        "## Operation measurements",
        "## Methodology",
        "## Interpretation and limitations",
        "benchmark_report.json",
        "benchmark_results.csv",
        "environment.txt",
    )

    errors = [
        f"Benchmark Markdown is missing required content: {section}"
        for section in required_sections
        if section not in content
    ]

    if len(content.strip()) < 300:
        errors.append(
            "Benchmark Markdown report is unexpectedly short."
        )

    return errors


def validate_environment(path: Path) -> list[str]:
    """Check the presence of essential environment evidence."""

    if not path.is_file():
        return [
            f"Benchmark environment file does not exist: {path}"
        ]

    try:
        content = path.read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeError) as exc:
        return [
            f"Cannot read benchmark environment file: {exc}"
        ]

    required_fields = (
        "P2 BENCHMARK ENVIRONMENT",
        "captured_at_utc:",
        "python_version:",
        "numpy_version:",
        "pennylane_version:",
        "operating_system:",
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
        errors.append(
            "Environment file is unexpectedly short."
        )

    return errors


def validate_results(results_dir: Path) -> list[str]:
    """Validate all four generated benchmark evidence files."""

    json_path = results_dir / JSON_FILENAME
    csv_path = results_dir / CSV_FILENAME
    markdown_path = results_dir / MARKDOWN_FILENAME
    environment_path = results_dir / ENVIRONMENT_FILENAME

    try:
        report = json.loads(
            json_path.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [
            f"Cannot read benchmark JSON: {exc}"
        ]

    errors = validate_report(report)

    if isinstance(report, dict):
        errors.extend(
            validate_csv(
                csv_path,
                report,
            )
        )
    else:
        errors.extend(
            validate_csv(csv_path)
        )

    errors.extend(
        validate_markdown(markdown_path)
    )

    errors.extend(
        validate_environment(environment_path)
    )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate all P2 benchmark evidence files."
    )

    parser.add_argument(
        "--results",
        type=Path,
        default=BENCHMARK_DIR,
        help="Directory containing the four generated evidence files.",
    )

    args = parser.parse_args()

    errors = validate_results(
        args.results.resolve()
    )

    for error in errors:
        print("FAIL:", error)

    if errors:
        print("VERDICT: BENCHMARK_REJECTED")
        return 1

    print("Benchmark JSON: PASS")
    print("Benchmark CSV: PASS")
    print("Benchmark Markdown: PASS")
    print("Benchmark environment: PASS")
    print("Required operations:", len(EXPECTED_OPERATIONS))
    print("VERDICT: BENCHMARK_ACCEPTED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
