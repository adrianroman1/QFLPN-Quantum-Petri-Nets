#!/usr/bin/env python3

"""Unit tests for validate_benchmark.py."""

import argparse
import csv
import importlib.util
import tempfile
import unittest

from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_benchmark.py")

SPEC = importlib.util.spec_from_file_location(
    "validate_benchmark",
    SCRIPT,
)

VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


HEADER = VALIDATOR.EXPECTED_HEADER


def valid_row():
    return {
        "timestamp": "2026-10-20T10:00:00+00:00",
        "benchmark_id": "QFLPN-100",
        "dimension": "100",
        "non_zero_count": "200",
        "parallelism": "2",
        "threshold": "4096",
        "warmup_iterations": "5",
        "measured_iterations": "10",
        "sequential_ms": "2.000000000000e+01",
        "parallel_ms": "1.000000000000e+01",
        "speedup": "2.000000000000e+00",
        "sequential_throughput_states_per_s": "5.000000000000e+03",
        "parallel_throughput_states_per_s": "1.000000000000e+04",
        "sequential_expected_error": "0.000000000000e+00",
        "parallel_expected_error": "0.000000000000e+00",
        "max_absolute_error": "0.000000000000e+00",
        "setup_time_ms": "1.000000000000e+00",
        "cpu": "test-cpu; processors=2",
        "available_memory_bytes": "1073741824",
        "java_version": "21",
        "operating_system": "Test OS",
        "notes": "synthetic unit-test row",
    }


class BenchmarkValidatorTest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "benchmark.csv"

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_csv(self, row):
        with self.csv_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=HEADER,
            )

            writer.writeheader()
            writer.writerow(row)

    def arguments(self):
        return argparse.Namespace(
            csv=self.csv_path,
            expected_n=100,
            parallelism=2,
            threshold=4096,
            warmup=5,
            iterations=10,
        )

    def test_valid_speedup_and_reduction(self):
        self.write_csv(valid_row())

        result = VALIDATOR.validate(self.arguments())

        self.assertEqual(result["validation"], "PASS")

        self.assertAlmostEqual(
            result["speedup_recomputed"],
            2.0,
        )

        self.assertAlmostEqual(
            result["time_reduction"],
            0.5,
        )

        self.assertAlmostEqual(
            result["time_reduction_percent"],
            50.0,
        )

    def test_rejects_incorrect_stored_speedup(self):
        row = valid_row()
        row["speedup"] = "1.900000000000e+00"

        self.write_csv(row)

        with self.assertRaises(VALIDATOR.ValidationError):
            VALIDATOR.validate(self.arguments())

    def test_rejects_incorrect_nnz(self):
        row = valid_row()
        row["non_zero_count"] = "199"

        self.write_csv(row)

        with self.assertRaises(VALIDATOR.ValidationError):
            VALIDATOR.validate(self.arguments())

    def test_rejects_nonpositive_sequential_time(self):
        row = valid_row()
        row["sequential_ms"] = "0"

        self.write_csv(row)

        with self.assertRaises(VALIDATOR.ValidationError):
            VALIDATOR.validate(self.arguments())

    def test_rejects_numerical_error_above_tolerance(self):
        row = valid_row()
        row["parallel_expected_error"] = "1.0e-6"

        self.write_csv(row)

        with self.assertRaises(VALIDATOR.ValidationError):
            VALIDATOR.validate(self.arguments())


if __name__ == "__main__":
    unittest.main(verbosity=2)
