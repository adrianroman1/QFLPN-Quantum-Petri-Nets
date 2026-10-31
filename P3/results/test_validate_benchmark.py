from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("validate_benchmark.py")

SPEC = importlib.util.spec_from_file_location(
    "qflpn_validate_benchmark",
    MODULE_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


# Canonical catalog required by P3.
CANONICAL_TIMED_BENCHMARKS = (
    (1_000_000, "QFLPN-1M"),
    (10_000_000, "QFLPN-10M"),
    (70_000_000, "QFLPN-70M"),
    (100_000_000, "QFLPN-100M"),
)

CORRECTNESS_FIXTURE = (12, "QFLPN-12")


def valid_row(
    dimension: int = 1_000_000,
    benchmark_id: str | None = None,
    run_id: str = "ci-123",
) -> dict[str, str]:
    """Build a valid V2 record for a canonical timed dimension."""

    if benchmark_id is None:
        benchmark_id = VALIDATOR.expected_benchmark_id(dimension)

    sequential_mean_ms = 20.0
    parallel_mean_ms = 10.0

    return {
        "timestamp": "2026-10-22T10:00:00Z",
        "run_id": run_id,
        "benchmark_id": benchmark_id,
        "dimension": str(dimension),
        "non_zero_count": str(2 * dimension),
        "parallelism": "2",
        "threshold": "4096",
        "warmup_iterations": "5",
        "measured_iterations": "10",
        "sequential_mean_ms": str(sequential_mean_ms),
        "sequential_median_ms": "19",
        "sequential_stddev_ms": "2",
        "parallel_mean_ms": str(parallel_mean_ms),
        "parallel_median_ms": "9",
        "parallel_stddev_ms": "1",
        "speedup": str(sequential_mean_ms / parallel_mean_ms),
        "sequential_throughput_states_per_s": str(
            dimension / (sequential_mean_ms / 1000.0)
        ),
        "parallel_throughput_states_per_s": str(
            dimension / (parallel_mean_ms / 1000.0)
        ),
        "sequential_expected_error": "0",
        "parallel_expected_error": "0",
        "max_absolute_error": "0",
        "setup_time_ms": "1",
        "cpu": "test-cpu",
        "max_jvm_memory_bytes": "4000000000",
        "free_jvm_heap_bytes": "500000000",
        "java_version": "21",
        "operating_system": "Linux",
        "notes": "canonical catalog test",
    }


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    """Write a V2 CSV fixture using the validator's exact header."""

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=VALIDATOR.HEADER,
            extrasaction="raise",
        )

        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Canonical catalog tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("dimension", "benchmark_id"),
    CANONICAL_TIMED_BENCHMARKS,
)
def test_canonical_timed_dimension_resolves_exact_id(
    dimension: int,
    benchmark_id: str,
) -> None:
    """Every timed dimension must resolve to its exact canonical ID."""

    assert (
        VALIDATOR.expected_benchmark_id(dimension)
        == benchmark_id
    )


@pytest.mark.parametrize(
    ("dimension", "benchmark_id"),
    CANONICAL_TIMED_BENCHMARKS,
)
def test_accepts_each_canonical_timed_benchmark(
    tmp_path: Path,
    dimension: int,
    benchmark_id: str,
) -> None:
    """Each of the four canonical timed dimensions must validate."""

    path = tmp_path / f"benchmark-{dimension}.csv"

    write_csv(
        path,
        [
            valid_row(
                dimension=dimension,
                benchmark_id=benchmark_id,
            )
        ],
    )

    result = VALIDATOR.validate(path)

    assert result["validation"] == "PASS"
    assert result["records"] == 1
    assert result["all_records_valid"] is True

    latest = result["latest_record"]

    assert latest["dimension"] == dimension
    assert latest["benchmark_id"] == benchmark_id


def test_canonical_catalog_contains_exactly_five_entries() -> None:
    """The catalog must contain the fixture and four timed dimensions."""

    assert VALIDATOR.CANONICAL_BENCHMARKS == {
        12: "QFLPN-12",
        1_000_000: "QFLPN-1M",
        10_000_000: "QFLPN-10M",
        70_000_000: "QFLPN-70M",
        100_000_000: "QFLPN-100M",
    }

    assert len(VALIDATOR.CANONICAL_BENCHMARKS) == 5


def test_timed_catalog_contains_exactly_four_dimensions() -> None:
    assert VALIDATOR.TIMED_BENCHMARK_DIMENSIONS == {
        1_000_000,
        10_000_000,
        70_000_000,
        100_000_000,
    }


def test_correctness_fixture_is_not_a_timed_benchmark() -> None:
    """QFLPN-12 is recognized but must not be accepted as timed evidence."""

    dimension, benchmark_id = CORRECTNESS_FIXTURE

    assert (
        VALIDATOR.expected_benchmark_id(dimension)
        == benchmark_id
    )

    assert (
        dimension
        in VALIDATOR.CORRECTNESS_FIXTURE_DIMENSIONS
    )

    assert (
        dimension
        not in VALIDATOR.TIMED_BENCHMARK_DIMENSIONS
    )


def test_rejects_qflpn_12_as_timed_csv_record(
    tmp_path: Path,
) -> None:
    """A correctness fixture must not enter the timed benchmark CSV."""

    path = tmp_path / "fixture-12.csv"

    write_csv(
        path,
        [
            valid_row(
                dimension=12,
                benchmark_id="QFLPN-12",
            )
        ],
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="correctness fixture",
    ):
        VALIDATOR.validate(path)


def test_rejects_30m_dimension() -> None:
    """30M is not part of the canonical catalog."""

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="unsupported benchmark dimension",
    ):
        VALIDATOR.expected_benchmark_id(30_000_000)


def test_rejects_30m_csv_record(
    tmp_path: Path,
) -> None:
    path = tmp_path / "30m.csv"

    row = valid_row(
        dimension=1_000_000,
        benchmark_id="QFLPN-1M",
    )

    row["dimension"] = "30000000"
    row["non_zero_count"] = "60000000"
    row["benchmark_id"] = "QFLPN-30M"

    write_csv(path, [row])

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="unsupported benchmark dimension",
    ):
        VALIDATOR.validate(path)


@pytest.mark.parametrize(
    "dimension",
    [
        0,
        1,
        100,
        4096,
        30_000_000,
        50_000_000,
        200_000_000,
        999_999,
        1_000_001,
    ],
)
def test_rejects_unknown_dimensions(
    dimension: int,
) -> None:
    with pytest.raises(
        VALIDATOR.ValidationError,
        match="unsupported benchmark dimension",
    ):
        VALIDATOR.expected_benchmark_id(dimension)


@pytest.mark.parametrize(
    "dimension",
    [
        1.5,
        "1000000",
        None,
        True,
    ],
)
def test_rejects_non_integer_dimension_types(
    dimension: object,
) -> None:
    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.expected_benchmark_id(dimension)


@pytest.mark.parametrize(
    ("dimension", "wrong_id"),
    [
        (1_000_000, "QFLPN-1000000"),
        (1_000_000, "QFLPN-30M"),
        (10_000_000, "QFLPN-10"),
        (70_000_000, "QFLPN-70"),
        (100_000_000, "QFLPN-100"),
        (100_000_000, "QFLPN-100M-EXTRA"),
        (12, "QFLPN-12M"),
    ],
)
def test_rejects_wrong_ids_for_canonical_dimensions(
    tmp_path: Path,
    dimension: int,
    wrong_id: str,
) -> None:
    """A canonical dimension cannot be paired with a different ID."""

    path = tmp_path / "wrong-id.csv"

    write_csv(
        path,
        [
            valid_row(
                dimension=dimension,
                benchmark_id=wrong_id,
            )
        ],
    )

    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path)


def test_validator_has_no_generic_identifier_fallback() -> None:
    """
    Unknown dimensions must fail instead of becoming QFLPN-{dimension}.
    """

    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.expected_benchmark_id(123_456_789)

    source = MODULE_PATH.read_text(encoding="utf-8")

    assert 'return f"QFLPN-{dimension}"' not in source
    assert 'return "QFLPN-" + str(dimension)' not in source


# ---------------------------------------------------------------------------
# CSV V2 structural and numerical validation tests
# ---------------------------------------------------------------------------


def test_accepts_valid_v2_record(
    tmp_path: Path,
) -> None:
    path = tmp_path / "valid.csv"

    write_csv(
        path,
        [valid_row()],
    )

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
        ("dimension", "1000000.0"),
        ("dimension", "-1000000"),
        ("non_zero_count", "1999999"),
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
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    row = valid_row()
    row[field] = value

    path = tmp_path / "invalid.csv"

    write_csv(path, [row])

    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path)


def test_rejects_legacy_header(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy.csv"

    path.write_text(
        "timestamp,dimension\nnow,1\n",
        encoding="utf-8",
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="header mismatch",
    ):
        VALIDATOR.validate(path)


def test_rejects_header_only_csv(
    tmp_path: Path,
) -> None:
    path = tmp_path / "header-only.csv"

    path.write_text(
        ",".join(VALIDATOR.HEADER) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="no benchmark data",
    ):
        VALIDATOR.validate(path)


def test_rejects_empty_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "empty.csv"

    path.write_text(
        "",
        encoding="utf-8",
    )

    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path)


def test_rejects_missing_column_value(
    tmp_path: Path,
) -> None:
    row = valid_row()
    del row["cpu"]

    path = tmp_path / "missing.csv"

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=VALIDATOR.HEADER,
        )

        writer.writeheader()
        writer.writerow(row)

    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path)


def test_rejects_extra_csv_field(
    tmp_path: Path,
) -> None:
    path = tmp_path / "extra.csv"

    path.write_text(
        ",".join(VALIDATOR.HEADER)
        + "\n"
        + ",".join(
            valid_row()[key]
            for key in VALIDATOR.HEADER
        )
        + ",unexpected\n",
        encoding="utf-8",
    )

    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path)


def test_rejects_duplicate_run_id(
    tmp_path: Path,
) -> None:
    path = tmp_path / "duplicates.csv"

    write_csv(
        path,
        [
            valid_row(run_id="ci-duplicate"),
            valid_row(run_id="ci-duplicate"),
        ],
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="duplicate run_id",
    ):
        VALIDATOR.validate(path)


def test_accepts_multiple_canonical_dimensions_in_one_csv(
    tmp_path: Path,
) -> None:
    """A cumulative CSV may contain multiple canonical timed scales."""

    path = tmp_path / "multiple-scales.csv"

    rows = [
        valid_row(
            dimension=dimension,
            benchmark_id=benchmark_id,
            run_id=f"ci-{dimension}",
        )
        for dimension, benchmark_id in CANONICAL_TIMED_BENCHMARKS
    ]

    write_csv(path, rows)

    result = VALIDATOR.validate(path)

    assert result["validation"] == "PASS"
    assert result["records"] == 4
    assert result["latest_record"]["dimension"] == 100_000_000
    assert (
        result["latest_record"]["benchmark_id"]
        == "QFLPN-100M"
    )


def test_checks_expected_configuration(
    tmp_path: Path,
) -> None:
    path = tmp_path / "expected.csv"

    write_csv(
        path,
        [valid_row()],
    )

    result = VALIDATOR.validate(
        path,
        {
            "dimension": 1_000_000,
            "warmup_iterations": 5,
            "measured_iterations": 10,
            "threshold": 4096,
            "parallelism": 2,
        },
    )

    assert result["validation"] == "PASS"


def test_rejects_configuration_mismatch(
    tmp_path: Path,
) -> None:
    path = tmp_path / "mismatch.csv"

    write_csv(
        path,
        [valid_row()],
    )

    with pytest.raises(
        VALIDATOR.ValidationError,
        match="expected",
    ):
        VALIDATOR.validate(
            path,
            {"dimension": 12},
        )


def test_rejects_invalid_utf8(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad-encoding.csv"

    path.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(path)
