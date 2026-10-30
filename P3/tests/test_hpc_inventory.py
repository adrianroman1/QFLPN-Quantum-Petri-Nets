"""Tests for the QFLPN P3 HPC inventory collector.

Run from the repository root:
    python -m pytest -q P3/tests/test_hpc_inventory.py

The tests use only the Python standard library plus pytest.
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

CONFIG_PATH = (
    REPOSITORY_ROOT
    / "P3"
    / "hpc"
    / "config"
    / "hpc-664.json"
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
    """Return a minimal valid configuration using the current v1 schema."""
    return {
        "schema": "qflpn-p3-hpc-configuration-v1",
        "configuration_id": "P3-HPC-664-REFERENCE",
        "status": "PROPOSED_NOT_HARDWARE_VERIFIED",
        "cluster": {
            "node_count": 16,
            "physical_cores_target": 664,
            "memory_gib_total": 4096,
        },
        "node_allocation": {
            "groups": [
                {
                    "node_count": 8,
                    "physical_cores_per_node": 42,
                    "memory_gib_per_node": 256,
                },
                {
                    "node_count": 8,
                    "physical_cores_per_node": 41,
                    "memory_gib_per_node": 256,
                },
            ],
        },
    }


def make_inventory(
    *,
    operating_system: str = "Linux",
    physical_core_count: int | None = 42,
    affinity_count: int | None = 42,
    memory_total_bytes: int | None = 256 * 1024**3,
    memory_limit_bytes: int | None = None,
    slurm_active: bool = True,
    slurm_nodes: str | None = "16",
) -> dict[str, Any]:
    """Return a synthetic single-node inventory."""
    return {
        "host": {
            "operating_system": operating_system,
        },
        "hardware": {
            "cpu": {
                "logical_processors": 84,
                "physical_core_count": physical_core_count,
            },
            "cpu_affinity": {
                "available": affinity_count is not None,
                "cpu_ids": (
                    list(range(affinity_count))
                    if affinity_count is not None
                    else None
                ),
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
            "cgroup": {
                "version": "V2",
                "cpu_quota_cores": None,
                "cpu_period_us": None,
                "cpu_max": "max 100000",
                "cpuset_cpus": "0-41",
                "cpuset_cpu_ids": list(range(42)),
                "memory_limit_bytes": memory_limit_bytes,
                "memory_current_bytes": None,
                "cgroup_mount_detected": True,
            },
        },
        "scheduler": {
            "slurm": {
                "active": slurm_active,
                "environment": {
                    "SLURM_JOB_ID": (
                        "12345" if slurm_active else None
                    ),
                    "SLURM_NNODES": (
                        slurm_nodes if slurm_active else None
                    ),
                },
                "scontrol_job_query": {
                    "available": slurm_active,
                    "return_code": 0 if slurm_active else None,
                    "stdout": "JobId=12345" if slurm_active else "",
                    "stderr": "",
                },
            },
        },
    }


def error_codes(errors: list[dict[str, str]]) -> set[str]:
    return {error["code"] for error in errors}


def test_current_repository_configuration_exists() -> None:
    assert CONFIG_PATH.is_file()


def test_current_repository_configuration_has_valid_schema() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    assert config["schema"] == "qflpn-p3-hpc-configuration-v1"

    nodes, cores, memory_per_node = (
        inventory_module.read_reference_targets(config)
    )

    assert nodes == 16
    assert cores == 664
    assert memory_per_node == pytest.approx(256.0)


def test_reference_configuration_calculates_heterogeneous_core_total() -> None:
    config = make_config()

    nodes, cores, memory_per_node = (
        inventory_module.read_reference_targets(config)
    )

    assert nodes == 16
    assert cores == 664
    assert memory_per_node == pytest.approx(256.0)

    groups = config["node_allocation"]["groups"]

    calculated_nodes = sum(
        group["node_count"] for group in groups
    )
    calculated_cores = sum(
        group["node_count"] * group["physical_cores_per_node"]
        for group in groups
    )
    calculated_memory = sum(
        group["node_count"] * group["memory_gib_per_node"]
        for group in groups
    )

    assert calculated_nodes == 16
    assert calculated_cores == 664
    assert calculated_memory == pytest.approx(4096.0)


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
        ",0",
        "0,",
        "1-2-3",
        "-1",
    ],
)
def test_parse_cpu_list_rejects_invalid_input(
    value: str | None,
) -> None:
    assert inventory_module.parse_cpu_list(value) is None


def test_validate_reference_accepts_valid_heterogeneous_node() -> None:
    config = make_config()
    inventory = make_inventory(physical_core_count=42)

    errors = inventory_module.validate_reference(
        config,
        inventory,
        require_slurm=True,
    )

    assert errors == []

    comparison = inventory["reference_comparison"]

    assert comparison["expected_cluster_nodes"] == 16
    assert comparison["expected_cluster_physical_cores"] == 664
    assert comparison["expected_local_physical_cores_options"] == [
        41, 42
    ]
    assert comparison["expected_local_memory_gib"] == pytest.approx(256.0)
    assert (
        comparison["cluster_wide_verification"]
        == "NOT_POSSIBLE_FROM_SINGLE_NODE_INVENTORY"
    )


def test_validate_reference_accepts_41_core_node() -> None:
    config = make_config()
    inventory = make_inventory(physical_core_count=41)

    errors = inventory_module.validate_reference(
        config,
        inventory,
        require_slurm=True,
    )

    assert errors == []


def test_validate_reference_rejects_wrong_configuration_schema() -> None:
    config = make_config()
    config["schema"] = "wrong-schema"

    errors = inventory_module.validate_reference(
        config,
        make_inventory(),
        require_slurm=True,
    )

    assert error_codes(errors) == {"CONFIGURATION_INVALID"}


def test_validate_reference_rejects_inconsistent_node_count() -> None:
    config = make_config()
    config["node_allocation"]["groups"][0]["node_count"] = 7

    errors = inventory_module.validate_reference(
        config,
        make_inventory(),
        require_slurm=True,
    )

    assert "CONFIGURATION_INVALID" in error_codes(errors)
    assert "CONFIG_NODE_COUNT_INCONSISTENT" in str(errors)


def test_validate_reference_rejects_inconsistent_core_total() -> None:
    config = make_config()
    config["cluster"]["physical_cores_target"] = 665

    errors = inventory_module.validate_reference(
        config,
        make_inventory(),
        require_slurm=True,
    )

    assert "CONFIGURATION_INVALID" in error_codes(errors)
    assert "CONFIG_CORE_COUNT_INCONSISTENT" in str(errors)


def test_validate_reference_rejects_inconsistent_memory_total() -> None:
    config = make_config()
    config["cluster"]["memory_gib_total"] = 4000

    errors = inventory_module.validate_reference(
        config,
        make_inventory(),
        require_slurm=True,
    )

    assert "CONFIGURATION_INVALID" in error_codes(errors)
    assert "CONFIG_MEMORY_TOTAL_INCONSISTENT" in str(errors)


def test_validate_reference_rejects_non_linux_host() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(operating_system="Windows"),
        require_slurm=True,
    )

    assert "UNSUPPORTED_OPERATING_SYSTEM" in error_codes(errors)


def test_validate_reference_rejects_unknown_cpu_affinity() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(affinity_count=None),
        require_slurm=True,
    )

    assert "CPU_AFFINITY_UNKNOWN" in error_codes(errors)


def test_validate_reference_rejects_unknown_memory_capacity() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(memory_total_bytes=None),
        require_slurm=True,
    )

    assert "MEMORY_TOTAL_UNKNOWN" in error_codes(errors)


def test_validate_reference_rejects_memory_below_node_target() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(
            memory_total_bytes=200 * 1024**3,
        ),
        require_slurm=True,
    )

    assert "LOCAL_MEMORY_TARGET_MISMATCH" in error_codes(errors)


def test_validate_reference_rejects_missing_slurm_allocation() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(slurm_active=False),
        require_slurm=True,
    )

    assert "SLURM_ALLOCATION_ABSENT" in error_codes(errors)


def test_validate_reference_allows_missing_slurm_when_not_required() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(slurm_active=False),
        require_slurm=False,
    )

    assert "SLURM_ALLOCATION_ABSENT" not in error_codes(errors)


def test_validate_reference_rejects_slurm_node_count_above_reference() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(slurm_nodes="17"),
        require_slurm=True,
    )

    assert "SLURM_NODE_COUNT_EXCEEDS_REFERENCE" in error_codes(errors)


def test_validate_reference_rejects_non_numeric_slurm_node_count() -> None:
    errors = inventory_module.validate_reference(
        make_config(),
        make_inventory(slurm_nodes="sixteen"),
        require_slurm=True,
    )

    assert "SLURM_NODE_COUNT_INVALID" in error_codes(errors)


def test_validate_reference_warns_when_cgroup_memory_is_restricted() -> None:
    inventory = make_inventory(
        memory_total_bytes=256 * 1024**3,
        memory_limit_bytes=64 * 1024**3,
    )

    errors = inventory_module.validate_reference(
        make_config(),
        inventory,
        require_slurm=True,
    )

    assert errors == []
    assert "resource_warnings" in inventory
    assert inventory["resource_warnings"][0]["code"] == (
        "CGROUP_MEMORY_LIMIT_BELOW_HOST_RAM"
    )


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
            "physical_core_count": 42,
            "socket_ids": ["0"],
            "socket_count": 1,
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
            "source": "synthetic-test",
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
            "cpuset_cpu_ids": list(range(42)),
            "memory_limit_bytes": None,
            "memory_current_bytes": None,
            "cgroup_mount_detected": True,
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
                "SLURM_NODEID": "0",
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
    assert result["schema_version"] == inventory_module.SCHEMA_VERSION
    assert result["validation"]["status"] == "PASS_LOCAL_PREFLIGHT"
    assert result["validation"]["errors"] == []
    assert result["validation"]["cluster_acceptance"] == "NOT_EVALUATED"
    assert result["validation"]["acceptance_gate"] == "p3_validation"
    assert result["reference_comparison"]["expected_cluster_nodes"] == 16
    assert (
        result["reference_comparison"]["expected_cluster_physical_cores"]
        == 664
    )
    assert (
        result["reference_comparison"]["cluster_wide_verification"]
        == "NOT_POSSIBLE_FROM_SINGLE_NODE_INVENTORY"
    )


def test_collect_rejects_invalid_json_configuration(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "invalid.json"
    config_path.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Nu se poate citi configurația JSON",
    ):
        inventory_module.collect(
            config_path,
            require_slurm=False,
        )


def test_collect_rejects_non_object_json_configuration(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "array.json"
    config_path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Rădăcina configurației trebuie să fie un obiect JSON",
    ):
        inventory_module.collect(
            config_path,
            require_slurm=False,
        )


def test_read_reference_targets_rejects_unknown_schema() -> None:
    with pytest.raises(ValueError, match="CONFIG_SCHEMA_INVALID"):
        inventory_module.read_reference_targets({
            "schema": "unknown",
        })


def test_read_reference_targets_rejects_missing_node_groups() -> None:
    config = make_config()
    config["node_allocation"]["groups"] = []

    with pytest.raises(
        ValueError,
        match="CONFIG_NODE_ALLOCATION_GROUPS_INVALID",
    ):
        inventory_module.read_reference_targets(config)


def test_read_reference_targets_rejects_invalid_group_values() -> None:
    config = make_config()
    config["node_allocation"]["groups"][0][
        "physical_cores_per_node"
    ] = 0

    with pytest.raises(
        ValueError,
        match="CONFIG_NODE_ALLOCATION_VALUE_INVALID",
    ):
        inventory_module.read_reference_targets(config)


def test_inventory_schema_constants_are_stable() -> None:
    assert inventory_module.SCHEMA == "qflpn-p3-hpc-inventory"
    assert inventory_module.SCHEMA_VERSION == "1.1.0"


def test_inventory_never_claims_cluster_acceptance_from_one_node() -> None:
    config = make_config()
    inventory = make_inventory()

    inventory_module.validate_reference(
        config,
        inventory,
        require_slurm=True,
    )

    assert (
        inventory["reference_comparison"]["cluster_wide_verification"]
        == "NOT_POSSIBLE_FROM_SINGLE_NODE_INVENTORY"
    )
