"""Fail-closed validation of P2 benchmark JSON and CSV evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = P2_ROOT / "benchmarks" / "results"

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
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_report(report: object) -> list[str]:
    errors: list[str] = []

    if not isinstance(report, dict):
        return ["Benchmark report root must be a JSON object."]

    if report.get("schema_version") != 1:
        errors.append("Unsupported benchmark report schema.")

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

    warmups = report.get("warmups")
    repetitions = report.get("repetitions")

    if type(warmups) is not int or warmups < 5:
        errors.append("Benchmark requires at least five warmups.")

    if type(repetitions) is not int or repetitions < 30:
        errors.append("Benchmark requires at least 30 repetitions.")

    tolerance = report.get("numerical_tolerance")

    if not finite_number(tolerance) or tolerance <= 0:
        errors.append("Benchmark numerical tolerance is invalid.")

    parity_error = report.get(
        "pennylane_numpy_maximum_difference"
    )

    if (
        not finite_number(parity_error)
        or not finite_number(tolerance)
        or parity_error > tolerance
    ):
        errors.append("PennyLane/NumPy parity check failed.")

    rows = report.get("operations")

    if not isinstance(rows, list):
        errors.append("Benchmark operations must be a list.")
        rows = []

    observed: set[str] = set()

    for index, row in enumerate(rows):
        prefix = f"operations[{index}]"

        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object.")
            continue

        name = row.get("operation")

        if not isinstance(name, str):
            errors.append(f"{prefix}.operation must be a string.")
            continue

        if name in observed:
            errors.append(f"Duplicate benchmark operation: {name}")

        observed.add(name)

        if row.get("passed") is not True:
            errors.append(f"{name}: numerical validation did not pass.")

        if row.get("warmups") != warmups:
            errors.append(f"{name}: warmup count mismatch.")

        if row.get("repetitions") != repetitions:
            errors.append(f"{name}: repetition count mismatch.")

        for field in NUMERIC_FIELDS:
            value = row.get(field)

            if not finite_number(value):
                errors.append(f"{name}: invalid numeric field {field}.")

        if all(finite_number(row.get(field)) for field in NUMERIC_FIELDS):
            if row["minimum_ns"] <= 0:
                errors.append(f"{name}: minimum time must be positive.")

            if row["maximum_ns"] < row["minimum_ns"]:
                errors.append(f"{name}: maximum is below minimum.")

            if row["median_ns"] < row["minimum_ns"]:
                errors.append(f"{name}: median is below minimum.")

            if row["median_ns"] > row["maximum_ns"]:
                errors.append(f"{name}: median is above maximum.")

            if row["standard_deviation_ns"] < 0:
                errors.append(f"{name}: negative standard deviation.")

            if row["numerical_error"] > row["numerical_tolerance"]:
                errors.append(f"{name}: numerical error exceeds tolerance.")

    missing = EXPECTED_OPERATIONS - observed
    extra = observed - EXPECTED_OPERATIONS

    if missing:
        errors.append(
            "Missing benchmark operations: " + ", ".join(sorted(missing))
        )

    if extra:
        errors.append(
            "Unexpected benchmark operations: " + ", ".join(sorted(extra))
        )

    if report.get("all_checks_pass") is not True:
        errors.append("all_checks_pass must be true.")

    if report.get("status") != "PASS":
        errors.append("Benchmark status must be PASS.")

    return errors


def validate_csv(path: Path) -> list[str]:
    errors: list[str] = []

    if not path.is_file():
        return [f"Benchmark CSV does not exist: {path}"]

    try:
        with path.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error) as exc:
        return [f"Cannot read benchmark CSV: {exc}"]

    names = [
        row.get("operation")
        for row in rows
    ]

    if len(names) != len(set(names)):
        errors.append("Benchmark CSV contains duplicate operations.")

    if set(names) != EXPECTED_OPERATIONS:
        errors.append("Benchmark CSV operation set is incomplete or invalid.")

    for row in rows:
        name = row.get("operation", "<unknown>")

        for field in NUMERIC_FIELDS:
            try:
                value = float(row[field])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{name}: invalid CSV field {field}.")
                continue

            if not math.isfinite(value):
                errors.append(f"{name}: non-finite CSV field {field}.")

        if row.get("passed", "").lower() != "true":
            errors.append(f"{name}: CSV numerical status is not PASS.")

    return errors


def validate_results(results_dir: Path) -> list[str]:
    json_path = results_dir / "benchmark_report.json"
    csv_path = results_dir / "benchmark_results.csv"

    errors: list[str] = []

    try:
        report = json.loads(
            json_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"Cannot read benchmark JSON: {exc}"]

    errors.extend(validate_report(report))
    errors.extend(validate_csv(csv_path))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate P2 benchmark evidence."
    )

    parser.add_argument(
        "--results",
        type=Path,
        default=DEFAULT_RESULTS,
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
    print("Required operations:", len(EXPECTED_OPERATIONS))
    print("VERDICT: BENCHMARK_ACCEPTED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
