"""Tests for the QFLPN P3 HPC inventory collector.

Run from the repository root:
    python -m pytest -q P3/tests/test_hpc_inventory.py

The tests use only Python's standard library plus pytest.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
COLLECTOR_PATH = (
    REPOSITORY_ROOT
    / "P3"
    / "hpc"
    / "tools"
    / "collect_hpc_inventory.py"
)

SPEC = importlib.util.spec_from_file_location(
    "p3_collect_hpc_inventory",
    COLLECTOR_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None

inventory_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory_module)


def make_config() -> dict[str, Any]:
    """Return the smallest valid reference configuration."""
    return {
        "schema": "qflpn-p3-hpc-configuration",
        "configuration_id": "P3-HPC-664-REFERENCE",
        "configuration_status": "PROPOSED_NOT_HARDWARE_VERIFIED",
        "hardware_reference": {
            "compute_nodes": 16,
            "physical_cores_total": 664,
            "memory_per_node_gib": 256,
        },
    }


def make_inventory(
    *,
    operating_system: str = "Linux",
    affinity_count: int | None = 42,
    memory_total_bytes: int | None = 256 * 1024**3,
    slurm_active: bool = True,
) -> dict[str, Any]:
    """Return a synthetic inventory for isolated validator tests."""
    return {
        "host": {
            "operating_system": operating_system,
        },
        "hardware": {
            "cpu": {
                "logical_processors": 84,
                "physical_core_count": 42,
            },
            "cpu_affinity": {
                "available": affinity_count is not None,
                "cpu_ids": list(range(affinity_count or 0)),
                "cpu_count": affinity_count,
            },
            "memory": {
                "total_bytes": memory_total_bytes,
                "total_gib": (
                    round(memory_total_bytes / (1024**3), 3)
                    if memory_total_bytes is not None
                    else None
                ),
            },
        },
        "scheduler": {
            "slurm": {
                "active": slurm_active,
                "environment": {
                    "SLURM_JOB_ID": "12345" if slurm_active else None,
                    "SLURM_NNODES": "16" if slurm_active else None,
                },
            },
        },
    }


def test_parse_cpu_list_accepts_ranges_and_individual_cpus() -> None:
    assert inventory_module.parse_cpu_list("0-3,8,10-11") == [
        0, 1, 2, 3, 8, 10, 11
    ]


def test_parse_cpu_list_removes_duplicates_and_sorts() -> None:
    assert inventory_module.parse_cpu_list("3,1-2,2,0") == [
        0, 1, 2, 3
    ]


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        " ",
        "0-",
        "-3",
        "4-2",
        "0,a,2",
        "0,,2",
    ],
)
def test_parse_cpu_list_rejects_invalid_input(value: str | None) -> None:
    assert inventory_module.parse_cpu_list(value) is None


def test_validate_reference_accepts_valid_local_slurm_inventory() -> None:
    config = make_config()
    inventory = make_inventory()

    errors = inventory_module.validate_reference(config, inventory)

    assert errors == []
    comparison = inventory["reference_comparison"]
    assert comparison["expected_cluster_nodes"] == 16
    assert comparison["expected_cluster_physical_cores"] == 664
    assert (
        comparison["cluster_wide_verification"]
        == "NOT_POSSIBLE_FROM_SINGLE_NODE_INVENTORY"
    )


def test_validate_reference_rejects_wrong_configuration_schema() -> None:
    config = make_config()
    config["schema"] = "wrong-schema"

    errors = inventory_module.validate_reference(
        config,
        make_inventory(),
    )

    assert [error["code"] for error in errors] == [
        "CONFIG_SCHEMA_INVALID"
    ]


def test_validate_reference_rejects_non_linux_host() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(operating_system="Windows"),
    )

    assert "UNSUPPORTED_OPERATING_SYSTEM" in {
        error["code"] for error in errors
    }


def test_validate_reference_rejects_unknown_cpu_affinity() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(affinity_count=None),
    )

    assert "CPU_AFFINITY_UNKNOWN" in {
        error["code"] for error in errors
    }


def test_validate_reference_rejects_unknown_memory_capacity() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(memory_total_bytes=None),
    )

    assert "MEMORY_TOTAL_UNKNOWN" in {
        error["code"] for error in errors
    }


def test_validate_reference_rejects_missing_slurm_allocation() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(slurm_active=False),
    )

    assert "SLURM_ALLOCATION_ABSENT" in {
        error["code"] for error in errors
    }


def test_validate_reference_rejects_invalid_reference_values() -> None:
    config = make_config()
    config["hardware_reference"]["compute_nodes"] = 0
    config["hardware_reference"]["physical_cores_total"] = "664"
    config["hardware_reference"]["memory_per_node_gib"] = -1

    errors = inventory_module.validate_reference(
        config,
        make_inventory(),
    )

    codes = {error["code"] for error in errors}
    assert "CONFIG_NODE_COUNT_INVALID" in codes
    assert "CONFIG_CORE_COUNT_INVALID" in codes
    assert "CONFIG_MEMORY_INVALID" in codes


def test_collect_marks_cluster_acceptance_not_evaluated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "hpc-664.json"
    config_path.write_text(
        json.dumps(make_config()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        inventory_module,
        "parse_cpuinfo",
        lambda: {
            "model_names": ["Synthetic test CPU"],
            "logical_processors": 84,
            "physical_core_ids": [
                f"0:{core}" for core in range(42)
            ],
            "socket_ids": ["0"],
        },
    )
    monkeypatch.setattr(
        inventory_module,
        "discover_frequency",
        lambda: {
            "available": True,
            "scaling_governor": "performance",
            "scaling_min_khz": 1000000,
            "scaling_max_khz": 3000000,
            "cpuinfo_max_khz": 3000000,
        },
    )
    monkeypatch.setattr(
        inventory_module,
        "discover_cache",
        lambda: [],
    )
    monkeypatch.setattr(
        inventory_module,
        "discover_affinity",
        lambda: {
            "available": True,
            "cpu_ids": list(range(42)),
            "cpu_count": 42,
        },
    )
    monkeypatch.setattr(
        inventory_module,
        "discover_cgroup",
        lambda: {
            "version": "V2",
            "cpu_quota_cores": None,
            "cpu_period_us": None,
            "cpu_max": "max 100000",
            "cpuset_cpus": "0-41",
            "memory_limit_bytes": None,
            "memory_current_bytes": None,
        },
    )
    monkeypatch.setattr(
        inventory_module,
        "discover_memory",
        lambda: {
            "total_bytes": 256 * 1024**3,
            "available_bytes": 200 * 1024**3,
            "free_bytes": 100 * 1024**3,
            "total_gib": 256.0,
            "available_gib": 200.0,
        },
    )
    monkeypatch.setattr(
        inventory_module,
        "discover_numa",
        lambda: {
            "available": True,
            "node_count": 2,
            "nodes": [],
        },
    )
    monkeypatch.setattr(
        inventory_module,
        "discover_slurm",
        lambda: {
            "active": True,
            "environment": {
                "SLURM_JOB_ID": "12345",
                "SLURM_NNODES": "16",
            },
            "scontrol_job_query": {
                "available": True,
                "return_code": 0,
                "stdout": "JobId=12345",
                "stderr": "",
            },
        },
    )
    monkeypatch.setattr(
        inventory_module,
        "discover_software",
        lambda: {
            "platform": "Linux-test",
            "system": "Linux",
            "release": "test-kernel",
            "machine": "x86_64",
            "python_version": "3.x",
            "java": {"available": True, "return_code": 0},
            "maven": {"available": True, "return_code": 0},
            "mpi_and_scheduler_commands": {},
        },
    )
    monkeypatch.setattr(
        inventory_module.platform,
        "system",
        lambda: "Linux",
    )

    result = inventory_module.collect(
        config_path,
        require_slurm=True,
    )

    assert result["schema"] == "qflpn-p3-hpc-inventory"
    assert result["validation"]["status"] == "PASS_LOCAL_PREFLIGHT"
    assert result["validation"]["errors"] == []
    assert result["validation"]["cluster_acceptance"] == "NOT_EVALUATED"
    assert result["reference_comparison"]["expected_cluster_nodes"] == 16


def test_collect_rejects_invalid_json_configuration(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "invalid.json"
    config_path.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(ValueError, match="Nu se poate citi configurația JSON"):
        inventory_module.collect(config_path, require_slurm=False)


def test_collect_rejects_non_object_json_configuration(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "array.json"
    config_path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Rădăcina configurației trebuie să fie un obiect JSON",
    ):
        inventory_module.collect(config_path, require_slurm=False)


def test_inventory_schema_constants_are_stable() -> None:
    assert inventory_module.SCHEMA == "qflpn-p3-hpc-inventory"
    assert inventory_module.SCHEMA_VERSION == "1.0.0"
