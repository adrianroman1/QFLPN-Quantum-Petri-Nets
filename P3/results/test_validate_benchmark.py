from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).with_name("validate_benchmark.py")
SPEC = importlib.util.spec_from_file_location("qflpn_validate_benchmark", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def valid_row() -> dict[str, str]:
    return {
        "timestamp": "2026-10-22T10:00:00Z",
        "run_id": "ci-123",
        "benchmark_id": "QFLPN-100",
        "dimension": "100",
        "non_zero_count": "200",
        "parallelism": "2",
        "threshold": "4096",
        "warmup_iterations": "5",
        "measured_iterations": "10",
        "sequential_mean_ms": "20",
        "sequential_median_ms": "19",
        "sequential_stddev_ms": "2",
        "parallel_mean_ms": "10",
        "parallel_median_ms": "9",
        "parallel_stddev_ms": "1",
        "speedup": "2",
        "sequential_throughput_states_per_s": "5000",
        "parallel_throughput_states_per_s": "10000",
        "sequential_expected_error": "0",
        "parallel_expected_error": "0",
        "max_absolute_error": "0",
        "setup_time_ms": "1",
        "cpu": "test-cpu",
        "max_jvm_memory_bytes": "4000000000",
        "free_jvm_heap_bytes": "500000000",
        "java_version": "21",
        "operating_system": "Linux",
        "notes": "test",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=VALIDATOR.HEADER, extrasaction="raise"
        )
        writer.writeheader()
        writer.writerows(rows)


def test_accepts_valid_v2_record(tmp_path: Path) -> None:
    path = tmp_path / "valid.csv"
    write_csv(path, [valid_row()])
    result = VALIDATOR.validate(path)
    assert result["validation"] == "PASS"
    assert result["records"] == 1
    assert result["all_records_valid"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("speedup", "3"),
        ("sequential_expected_error", "1e-5"),
        ("parallel_stddev_ms", "nan"),
        ("run_id", ""),
        ("timestamp", "not-a-date"),
        ("timestamp", "2026-10-22T10:00:00"),
        ("dimension", "100.0"),
        ("dimension", "-100"),
        ("non_zero_count", "199"),
        ("benchmark_id", "WRONG"),
        ("parallelism", "0"),
        ("threshold", "0"),
        ("warmup_iterations", "-1"),
        ("measured_iterations", "0"),
        ("max_jvm_memory_bytes", "0"),
        ("free_jvm_heap_bytes", "5000000000"),
        ("cpu", ""),
        ("operating_system", ""),
    ],
)
def test_rejects_invalid_fields(
    tmp_path: Path, field: str, value: str
) -> None:
    row = valid_row()
    row[field] = value
    path = tmp_path / "invalid.csv"
    write_csv(path, [row])
    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path)


def test_rejects_legacy_header(tmp_path: Path) -> None:
    path = tmp_path / "legacy.csv"
    path.write_text("timestamp,dimension\nnow,1\n", encoding="utf-8")
    with pytest.raises(VALIDATOR.ValidationError, match="header mismatch"):
        VALIDATOR.validate(path)


def test_rejects_header_only_csv(tmp_path: Path) -> None:
    path = tmp_path / "header-only.csv"
    path.write_text(",".join(VALIDATOR.HEADER) + "\n", encoding="utf-8")
    with pytest.raises(VALIDATOR.ValidationError, match="no benchmark data"):
        VALIDATOR.validate(path)


def test_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path)


def test_rejects_missing_column_value(tmp_path: Path) -> None:
    row = valid_row()
    del row["cpu"]
    path = tmp_path / "missing.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=VALIDATOR.HEADER)
        writer.writeheader()
        writer.writerow(row)
    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path)


def test_rejects_extra_csv_field(tmp_path: Path) -> None:
    path = tmp_path / "extra.csv"
    path.write_text(
        ",".join(VALIDATOR.HEADER) + "\n"
        + ",".join(valid_row()[key] for key in VALIDATOR.HEADER)
        + ",unexpected\n",
        encoding="utf-8",
    )
    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path)


def test_rejects_duplicate_run_id(tmp_path: Path) -> None:
    path = tmp_path / "duplicates.csv"
    write_csv(path, [valid_row(), valid_row()])
    with pytest.raises(VALIDATOR.ValidationError, match="duplicate run_id"):
        VALIDATOR.validate(path)


def test_checks_expected_configuration(tmp_path: Path) -> None:
    path = tmp_path / "expected.csv"
    write_csv(path, [valid_row()])
    result = VALIDATOR.validate(
        path,
        {
            "dimension": 100,
            "warmup_iterations": 5,
            "measured_iterations": 10,
            "threshold": 4096,
            "parallelism": 2,
        },
    )
    assert result["validation"] == "PASS"


def test_rejects_configuration_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "mismatch.csv"
    write_csv(path, [valid_row()])
    with pytest.raises(VALIDATOR.ValidationError, match="expected"):
        VALIDATOR.validate(path, {"dimension": 12})


def test_rejects_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "bad-encoding.csv"
    path.write_bytes(b"\xff\xfe\xfa")
    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path)
