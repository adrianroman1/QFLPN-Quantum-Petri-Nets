#!/usr/bin/env python3
"""Tests for P3/hpc/tools/validate_hpc_results.py.

These tests validate the target configuration and inventory contract.
They do not execute SpMV and do not claim measured HPC performance.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "P3" / "hpc" / "tools" / "validate_hpc_results.py"
CONFIG = ROOT / "P3" / "hpc" / "config" / "hpc-target.json"

EXPECTED_THRESHOLDS = [
    256,
    512,
    1024,
    2048,
    4096,
    8192,
    16384,
    32768,
    65536,
    131072,
    262144,
    524288,
    1048576,
    2097152,
    4194304,
    8388608,
    10000000,
]

SPEC = importlib.util.spec_from_file_location(
    "qflpn_validate_hpc_results",
    TOOL,
)
assert SPEC is not None and SPEC.loader is not None

MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_target() -> dict[str, Any]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def motherboard() -> dict[str, str]:
    return {
        "manufacturer": "Example Manufacturer",
        "model": "Example HPC Board",
        "version": "1.0",
    }


def node(
    hostname: str,
    physical_cores: int,
    *,
    memory_gib: float = 256.0,
    affinity: int | None = None,
    quota: float | None = None,
    board: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": MODULE.NODE_SCHEMA,
        "hostname": hostname,
        "physical_cores": physical_cores,
        "logical_processors": physical_cores,
        "cpu_affinity_count": (
            physical_cores if affinity is None else affinity
        ),
        "cgroup_cpu_quota_cores": quota,
        "memory_gib": memory_gib,
        "motherboard": motherboard() if board is None else board,
    }


def full_cluster() -> list[dict[str, Any]]:
    return (
        [
            node(f"HPC-{number:02d}", 42)
            for number in range(1, 9)
        ]
        + [
            node(f"HPC-{number:02d}", 41)
            for number in range(9, 17)
        ]
    )


def checks_by_id(checks: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {item["id"]: item for item in checks}


def write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def test_repository_target_uses_expected_schema_and_filename() -> None:
    target = load_target()

    assert target["schema"] == "qflpn-p3-hpc-target-v2"
    assert target["status"] == (
        "PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE"
    )
    assert CONFIG.name == "hpc-target.json"


def test_repository_target_declares_exact_664_core_topology() -> None:
    target = load_target()
    hardware = target["hardware_target"]

    assert hardware["compute_nodes"] == 16
    assert hardware["physical_cores_total"] == 664
    assert hardware["ram_gib_total"] == 4096
    assert hardware["ram_gib_per_node"] == 256

    groups = hardware["node_groups"]

    assert groups == [
        {
            "names": "HPC-01..HPC-08",
            "nodes": 8,
            "physical_cores_per_node": 42,
        },
        {
            "names": "HPC-09..HPC-16",
            "nodes": 8,
            "physical_cores_per_node": 41,
        },
    ]

    assert sum(
        group["nodes"] * group["physical_cores_per_node"]
        for group in groups
    ) == 664


def test_repository_target_declares_motherboard_collection_contract() -> None:
    target = load_target()
    board = target["hardware_target"]["motherboard"]

    assert board["collection_required"] is True
    assert board["fields"] == [
        "manufacturer",
        "model",
        "version",
    ]
    assert board["source"] == "/sys/class/dmi/id/"
    assert board["missing_value"] == "UNAVAILABLE"


def test_repository_target_declares_exact_17_spmv_thresholds() -> None:
    benchmark = load_target()["benchmark"]

    assert benchmark["thresholds"] == EXPECTED_THRESHOLDS
    assert len(benchmark["thresholds"]) == 17
    assert benchmark["maximum_target_dimension"] == 10_000_000


def test_repository_target_declares_spmv_664_and_10m_proposal() -> None:
    benchmark = load_target()["benchmark"]

    assert benchmark["workload"] == "SpMV"
    assert benchmark["parallelism_target"] == 664
    assert 664 in benchmark["worker_counts"]
    assert benchmark["maximum_target_dimension"] == 10_000_000
    assert benchmark["minimum_warmup"] == 5
    assert benchmark["minimum_valid_measurements"] == 30
    assert benchmark["execution_status"] == "NOT_EXECUTED"


def test_configuration_validation_passes_for_repository_target() -> None:
    checks, target = MODULE.validate_configuration(load_target())
    by_id = checks_by_id(checks)

    assert target["expected_nodes"] == 16
    assert target["expected_physical_cores"] == 664
    assert len(target["expected_cores_by_node"]) == 16

    assert by_id["CONFIG_SCHEMA"]["status"] == "PASS"
    assert by_id["CONFIG_STATUS"]["status"] == "PASS"
    assert by_id["HARDWARE_TARGET_INTERNAL_CONSISTENCY"]["status"] == "PASS"
    assert by_id["MOTHERBOARD_COLLECTION_CONTRACT"]["status"] == "PASS"
    assert by_id["SPMV_BENCHMARK_PROPOSAL"]["status"] == "PASS"


def test_configuration_validation_rejects_wrong_schema() -> None:
    target = load_target()
    target["schema"] = "qflpn-p3-hpc-configuration"

    checks, parsed = MODULE.validate_configuration(target)
    by_id = checks_by_id(checks)

    assert parsed == {}
    assert by_id["CONFIG_SCHEMA"]["status"] == "FAIL"


def test_configuration_validation_rejects_wrong_core_total() -> None:
    target = load_target()
    target["hardware_target"]["physical_cores_total"] = 672

    checks, _ = MODULE.validate_configuration(target)
    by_id = checks_by_id(checks)

    assert by_id["HARDWARE_TARGET_INTERNAL_CONSISTENCY"]["status"] == "FAIL"


def test_configuration_validation_rejects_wrong_node_distribution() -> None:
    target = load_target()
    target["hardware_target"]["node_groups"][0][
        "physical_cores_per_node"
    ] = 43

    checks, _ = MODULE.validate_configuration(target)
    by_id = checks_by_id(checks)

    assert by_id["HARDWARE_TARGET_INTERNAL_CONSISTENCY"]["status"] == "FAIL"


def test_configuration_validation_rejects_missing_motherboard_contract() -> None:
    target = load_target()
    del target["hardware_target"]["motherboard"]["fields"]

    checks, _ = MODULE.validate_configuration(target)
    by_id = checks_by_id(checks)

    assert by_id["MOTHERBOARD_COLLECTION_CONTRACT"]["status"] == "FAIL"


def test_configuration_validation_rejects_missing_664_worker_target() -> None:
    target = load_target()
    target["benchmark"]["worker_counts"].remove(664)

    checks, _ = MODULE.validate_configuration(target)
    by_id = checks_by_id(checks)

    assert by_id["SPMV_BENCHMARK_PROPOSAL"]["status"] == "FAIL"


def test_configuration_validation_rejects_missing_10m_threshold() -> None:
    target = load_target()
    target["benchmark"]["thresholds"].remove(10_000_000)

    checks, _ = MODULE.validate_configuration(target)
    by_id = checks_by_id(checks)

    assert by_id["SPMV_BENCHMARK_PROPOSAL"]["status"] == "FAIL"


def test_configuration_validation_rejects_missing_intermediate_threshold() -> None:
    target = load_target()
    target["benchmark"]["thresholds"].remove(4096)

    checks, _ = MODULE.validate_configuration(target)
    by_id = checks_by_id(checks)

    assert by_id["SPMV_BENCHMARK_PROPOSAL"]["status"] == "FAIL"


def test_configuration_validation_rejects_unapproved_extra_threshold() -> None:
    target = load_target()
    target["benchmark"]["thresholds"].append(16_777_216)
    target["benchmark"]["thresholds"].sort()

    checks, _ = MODULE.validate_configuration(target)
    by_id = checks_by_id(checks)

    assert by_id["SPMV_BENCHMARK_PROPOSAL"]["status"] == "FAIL"


def test_configuration_validation_rejects_reordered_thresholds() -> None:
    target = load_target()
    target["benchmark"]["thresholds"].reverse()

    checks, _ = MODULE.validate_configuration(target)
    by_id = checks_by_id(checks)

    assert by_id["SPMV_BENCHMARK_PROPOSAL"]["status"] == "FAIL"


def test_configuration_validation_rejects_executed_status_in_proposal() -> None:
    target = load_target()
    target["benchmark"]["execution_status"] = "EXECUTED"

    checks, _ = MODULE.validate_configuration(target)
    by_id = checks_by_id(checks)

    assert by_id["SPMV_BENCHMARK_PROPOSAL"]["status"] == "FAIL"


def test_no_inventory_is_deferred_not_pass() -> None:
    checks, target = MODULE.validate_configuration(load_target())

    assert not any(item["status"] == "FAIL" for item in checks)

    status, inventory_checks, summary = MODULE.validate_inventory([], target)
    by_id = checks_by_id(inventory_checks)

    assert status == "DEFERRED"
    assert by_id["INVENTORY_PRESENT"]["status"] == "DEFERRED"
    assert by_id["MOTHERBOARD_INVENTORY"]["status"] == "DEFERRED"
    assert summary["node_count_observed"] == 0


def test_complete_16_node_inventory_passes_all_hardware_checks() -> None:
    config_checks, target = MODULE.validate_configuration(load_target())

    assert not any(item["status"] == "FAIL" for item in config_checks)

    status, checks, summary = MODULE.validate_inventory(
        full_cluster(),
        target,
    )
    by_id = checks_by_id(checks)

    assert status == "PASS"
    assert by_id["COMPUTE_NODE_SET"]["status"] == "PASS"
    assert by_id["PHYSICAL_CORE_TOPOLOGY"]["status"] == "PASS"
    assert by_id["TOTAL_RAM"]["status"] == "PASS"
    assert by_id["RAM_PER_NODE"]["status"] == "PASS"
    assert by_id["MOTHERBOARD_INVENTORY"]["status"] == "PASS"
    assert by_id["EFFECTIVE_CPU_CAPACITY"]["status"] == "PASS"

    assert summary["node_count_observed"] == 16
    assert summary["physical_cores_observed"] == 664
    assert summary["motherboard_nodes_missing"] == []


def test_inventory_without_motherboard_is_deferred() -> None:
    config_checks, target = MODULE.validate_configuration(load_target())
    assert not any(item["status"] == "FAIL" for item in config_checks)

    nodes = full_cluster()
    nodes[0].pop("motherboard")

    status, checks, _ = MODULE.validate_inventory(nodes, target)
    by_id = checks_by_id(checks)

    assert status == "DEFERRED"
    assert by_id["MOTHERBOARD_INVENTORY"]["status"] == "DEFERRED"


def test_inventory_with_unavailable_motherboard_is_deferred() -> None:
    config_checks, target = MODULE.validate_configuration(load_target())
    assert not any(item["status"] == "FAIL" for item in config_checks)

    nodes = full_cluster()
    nodes[0]["motherboard"] = {
        "manufacturer": "UNAVAILABLE",
        "model": "Example HPC Board",
        "version": "1.0",
    }

    status, checks, _ = MODULE.validate_inventory(nodes, target)
    by_id = checks_by_id(checks)

    assert status == "DEFERRED"
    assert by_id["MOTHERBOARD_INVENTORY"]["status"] == "DEFERRED"


def test_fifteen_nodes_are_deferred() -> None:
    _, target = MODULE.validate_configuration(load_target())

    status, checks, summary = MODULE.validate_inventory(
        full_cluster()[:15],
        target,
    )
    by_id = checks_by_id(checks)

    assert status == "DEFERRED"
    assert by_id["COMPUTE_NODE_SET"]["status"] == "DEFERRED"
    assert by_id["PHYSICAL_CORE_TOPOLOGY"]["status"] == "DEFERRED"
    assert summary["node_count_observed"] == 15


def test_wrong_physical_core_count_fails_closed() -> None:
    _, target = MODULE.validate_configuration(load_target())

    nodes = full_cluster()
    nodes[0]["physical_cores"] = 40

    status, checks, _ = MODULE.validate_inventory(nodes, target)
    by_id = checks_by_id(checks)

    assert status == "FAIL"
    assert by_id["PHYSICAL_CORE_TOPOLOGY"]["status"] == "FAIL"


def test_duplicate_hostnames_fail() -> None:
    _, target = MODULE.validate_configuration(load_target())

    nodes = full_cluster()
    nodes[1]["hostname"] = nodes[0]["hostname"]

    status, checks, _ = MODULE.validate_inventory(nodes, target)
    by_id = checks_by_id(checks)

    assert status == "FAIL"
    assert by_id["DISTINCT_COMPUTE_NODES"]["status"] == "FAIL"


def test_low_cpu_affinity_defers_effective_capacity() -> None:
    _, target = MODULE.validate_configuration(load_target())

    nodes = full_cluster()
    nodes[0]["cpu_affinity_count"] = 8

    status, checks, _ = MODULE.validate_inventory(nodes, target)
    by_id = checks_by_id(checks)

    assert status == "DEFERRED"
    assert by_id["EFFECTIVE_CPU_CAPACITY"]["status"] == "DEFERRED"


def test_low_cgroup_quota_defers_effective_capacity() -> None:
    _, target = MODULE.validate_configuration(load_target())

    nodes = full_cluster()
    nodes[0]["cgroup_cpu_quota_cores"] = 4.0

    status, checks, _ = MODULE.validate_inventory(nodes, target)
    by_id = checks_by_id(checks)

    assert status == "DEFERRED"
    assert by_id["EFFECTIVE_CPU_CAPACITY"]["status"] == "DEFERRED"


def test_missing_physical_core_value_is_deferred() -> None:
    _, target = MODULE.validate_configuration(load_target())

    nodes = full_cluster()
    nodes[0]["physical_cores"] = None

    status, checks, _ = MODULE.validate_inventory(nodes, target)
    by_id = checks_by_id(checks)

    assert status == "DEFERRED"
    assert by_id["PHYSICAL_CORE_TOPOLOGY"]["status"] == "DEFERRED"


def test_insufficient_memory_fails() -> None:
    _, target = MODULE.validate_configuration(load_target())

    nodes = full_cluster()
    nodes[0]["memory_gib"] = 128.0

    status, checks, _ = MODULE.validate_inventory(nodes, target)
    by_id = checks_by_id(checks)

    assert status == "FAIL"
    assert by_id["RAM_PER_NODE"]["status"] == "FAIL"


def test_aggregate_inventory_is_loaded_and_validated(tmp_path: Path) -> None:
    aggregate_path = write_json(
        tmp_path / "cluster-inventory.json",
        {
            "schema": MODULE.AGGREGATE_SCHEMA,
            "nodes": full_cluster(),
        },
    )

    nodes = MODULE.load_inventory_files([aggregate_path])

    assert len(nodes) == 16
    assert all(item["schema"] == MODULE.NODE_SCHEMA for item in nodes)

    _, target = MODULE.validate_configuration(load_target())
    status, checks, _ = MODULE.validate_inventory(nodes, target)

    assert status == "PASS"
    assert checks_by_id(checks)["MOTHERBOARD_INVENTORY"]["status"] == "PASS"


def test_individual_node_inventory_files_are_loaded(tmp_path: Path) -> None:
    paths = [
        write_json(tmp_path / f"node-{index:02d}.json", item)
        for index, item in enumerate(full_cluster(), start=1)
    ]

    nodes = MODULE.load_inventory_files(paths)

    assert len(nodes) == 16
    assert {item["hostname"] for item in nodes} == {
        f"HPC-{index:02d}" for index in range(1, 17)
    }


def test_unknown_inventory_schema_is_rejected(tmp_path: Path) -> None:
    path = write_json(
        tmp_path / "invalid.json",
        {
            "schema": "unknown-inventory-schema",
            "hostname": "HPC-01",
        },
    )

    with pytest.raises(MODULE.InputError):
        MODULE.load_inventory_files([path])


def test_aggregate_without_nodes_array_is_rejected(tmp_path: Path) -> None:
    path = write_json(
        tmp_path / "invalid-aggregate.json",
        {
            "schema": MODULE.AGGREGATE_SCHEMA,
        },
    )

    with pytest.raises(MODULE.InputError):
        MODULE.load_inventory_files([path])


def test_validate_report_keeps_proposal_separate_from_execution_evidence(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "validation.json"

    report = MODULE.validate(CONFIG, [])

    assert report["schema"] == MODULE.REPORT_SCHEMA
    assert report["configuration_validation"]["status"] == "PASS"
    assert report["inventory_validation"]["status"] == "DEFERRED"
    assert report["overall_status"] == "DEFERRED"

    evidence = report["execution_evidence"]
    assert evidence["benchmark_execution_status"] == "NOT_EXECUTED"
    assert evidence["664_worker_execution_demonstrated"] is False
    assert evidence["dimension_10000000_execution_demonstrated"] is False
    assert evidence["this_report_is_not_performance_evidence"] is True

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    persisted = json.loads(report_path.read_text(encoding="utf-8"))

    assert persisted["overall_status"] == "DEFERRED"


def test_validate_cli_writes_report_and_returns_zero_for_deferred(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "reports" / "validation.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_hpc_results.py",
            "--config",
            str(CONFIG),
            "--output",
            str(output),
        ],
    )

    result = MODULE.main()

    assert result == 0
    assert output.is_file()

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["overall_status"] == "DEFERRED"
    assert report["execution_evidence"]["benchmark_execution_status"] == (
        "NOT_EXECUTED"
    )


def test_validate_cli_rejects_missing_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "validation.json"
    missing_config = tmp_path / "missing-target.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_hpc_results.py",
            "--config",
            str(missing_config),
            "--output",
            str(output),
        ],
    )

    assert MODULE.main() == 2
    assert not output.exists()
