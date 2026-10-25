from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from P3.tools import record_environment as environment


def valid_environment() -> dict:
    return {
        "schema": "qflpn-p3-environment-v1",
        "captured_at_utc": "2026-10-25T12:00:00+00:00",
        "run_id": "p3-12345-1",
        "repository": {
            "root": "/workspace/repository",
            "remote_origin": "https://github.com/example/repository.git",
            "branch": "main",
            "commit": "a" * 40,
            "commit_dirty": False,
        },
        "runner": {
            "os": "Linux",
            "os_release": "6.8.0",
            "os_version": "runner",
            "machine": "x86_64",
            "processor": "CPU",
            "logical_cpu_count": 2,
            "load_average_1_5_15": [0.1, 0.2, 0.3],
            "memory": {
                "total_bytes": 8_000_000_000,
                "available_bytes": 4_000_000_000,
            },
            "github_runner_os": "Linux",
            "github_runner_arch": "X64",
            "github_workflow": "P3 Validation",
            "github_run_id": "12345",
            "github_run_attempt": "1",
        },
        "runtime": {
            "python": "3.12.0",
            "java": 'openjdk version "21"',
            "maven": "Apache Maven 3.9",
            "git": "git version 2.43",
        },
        "benchmark": {
            "dimension": 1_000_000,
            "warmup_iterations": 5,
            "measured_iterations": 10,
            "threshold": 4096,
            "parallelism": 2,
        },
    }


def test_validate_accepts_complete_environment() -> None:
    environment.validate_environment(valid_environment())


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("repository", "commit"),
        ("repository", "remote_origin"),
        ("runner", "os"),
        ("runner", "machine"),
        ("runtime", "java"),
        ("runtime", "maven"),
        ("runtime", "python"),
        ("runtime", "git"),
    ],
)
def test_validate_rejects_missing_required_fields(
    section: str,
    field: str,
) -> None:
    data = valid_environment()
    data[section][field] = ""

    with pytest.raises(ValueError):
        environment.validate_environment(data)


@pytest.mark.parametrize(
    "value",
    [0, -1, True, 1.5, None, "100"],
)
def test_validate_rejects_invalid_benchmark_integer(value) -> None:
    data = valid_environment()
    data["benchmark"]["dimension"] = value

    with pytest.raises(ValueError):
        environment.validate_environment(data)


def test_validate_rejects_wrong_schema() -> None:
    data = valid_environment()
    data["schema"] = "unknown-schema"

    with pytest.raises(ValueError, match="Unsupported environment schema"):
        environment.validate_environment(data)


def test_validate_rejects_unavailable_runtime() -> None:
    data = valid_environment()
    data["runtime"]["java"] = "UNAVAILABLE"

    with pytest.raises(ValueError, match="Runtime command unavailable"):
        environment.validate_environment(data)


def test_render_text_contains_run_and_configuration() -> None:
    rendered = environment.render_text(valid_environment())

    assert "p3-12345-1" in rendered
    assert "dimension: 1000000" in rendered
    assert "measured_iterations: 10" in rendered
    assert "parallelism: 2" in rendered
    assert "openjdk version" in rendered


def test_capture_environment_records_actual_metadata(
    tmp_path: Path,
) -> None:
    with (
        patch.object(
            environment,
            "git_value",
            side_effect=[
                "https://github.com/example/repository.git",
                "a" * 40,
                "",
            ],
        ),
        patch.object(
            environment,
            "run_command",
            side_effect=[
                'openjdk version "21"',
                "Apache Maven 3.9",
                "git version 2.43",
            ],
        ),
        patch.object(environment.os, "cpu_count", return_value=2),
        patch.object(environment.os, "getloadavg", return_value=(0.1, 0.2, 0.3)),
    ):
        data = environment.capture_environment(
            tmp_path,
            run_id="p3-12345-1",
            dimension=1_000_000,
            warmup_iterations=5,
            measured_iterations=10,
            threshold=4096,
            parallelism=2,
        )

    assert data["run_id"] == "p3-12345-1"
    assert data["repository"]["commit"] == "a" * 40
    assert data["runner"]["logical_cpu_count"] == 2
    assert data["benchmark"]["dimension"] == 1_000_000
    assert data["runtime"]["java"].startswith("openjdk")


def test_capture_environment_rejects_missing_repository(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="Repository root does not exist"):
        environment.capture_environment(
            tmp_path / "missing",
            run_id="p3-12345-1",
            dimension=100,
            warmup_iterations=1,
            measured_iterations=1,
            threshold=10,
            parallelism=1,
        )


def test_atomic_write_creates_parent_and_exact_content(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "reports" / "environment.txt"

    environment.atomic_write(destination, "actual environment\n")

    assert destination.read_text(encoding="utf-8") == "actual environment\n"


def test_atomic_write_refuses_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("keep", encoding="utf-8")

    link = tmp_path / "environment.txt"
    link.symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        environment.atomic_write(link, "replace")

    assert target.read_text(encoding="utf-8") == "keep"


def test_json_output_is_valid_and_round_trips(tmp_path: Path) -> None:
    data = valid_environment()
    destination = tmp_path / "environment.json"

    environment.atomic_write(
        destination,
        json.dumps(data, indent=2, allow_nan=False) + "\n",
    )

    loaded = json.loads(destination.read_text(encoding="utf-8"))
    assert loaded == data
