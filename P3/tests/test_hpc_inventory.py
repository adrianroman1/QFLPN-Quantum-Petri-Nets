#!/usr/bin/env python3
"""Tests for the QFLPN P3 HPC inventory collector.

These tests cover:
- CPU, RAM, cgroup and motherboard collection helpers;
- explicit UNAVAILABLE motherboard values;
- the nested hpc-target.json configuration;
- node inventory schema compatibility;
- cluster aggregation and validator interoperability;
- duplicate nodes and incorrect physical-core topology;
- the separation between proposed targets and execution evidence.

No SpMV benchmark is executed by this test module.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]

COLLECTOR_PATH = (
    ROOT / "P3" / "hpc" / "tools" / "collect_hpc_inventory.py"
)
VALIDATOR_PATH = (
    ROOT / "P3" / "hpc" / "tools" / "validate_hpc_results.py"
)
TARGET_PATH = (
    ROOT / "P3" / "hpc" / "config" / "hpc-target.json"
)


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COLLECTOR = load_module(
    "qflpn_hpc_inventory_collector_tests",
    COLLECTOR_PATH,
)

VALIDATOR = load_module(
    "qflpn_hpc_results_validator_tests",
    VALIDATOR_PATH,
)


def load_target() -> dict[str, Any]:
    return json.loads(TARGET_PATH.read_text(encoding="utf-8"))


def motherboard(
    manufacturer: str = "Example Manufacturer",
    model: str = "Example HPC Board",
    version: str = "1.0",
) -> dict[str, str]:
    return {
        "manufacturer": manufacturer,
        "model": model,
        "version": version,
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
        "schema": COLLECTOR.NODE_SCHEMA,
        "collected_utc": "2026-11-01T00:00:00Z",
        "hostname": hostname,
        "os": "Linux test",
        "kernel": "6.0-test",
        "python": "3.12.0",
        "cpu_model": "Example CPU",
        "sockets": 2,
        "physical_cores": physical_cores,
        "logical_processors": physical_cores,
        "cpu_affinity_count": (
            physical_cores if affinity is None else affinity
        ),
        "cpu_affinity_ids": [],
        "cgroup_cpu_quota_cores": quota,
        "memory_gib": memory_gib,
        "numa_nodes": ["node0", "node1"],
        "motherboard": motherboard() if board is None else board,
        "slurm": {
            "SLURM_JOB_ID": "12345",
            "SLURM_NNODES": "16",
        },
        "java": "openjdk 21",
        "maven": "Apache Maven 3.9",
        "mpi": "mpirun 4",
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


def checks_by_id(
    checks: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    return {
        item["id"]: item
        for item in checks
    }


def write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Target configuration and schema
# ---------------------------------------------------------------------------

def test_repository_target_file_exists() -> None:
    assert TARGET_PATH.is_file()


def test_repository_target_uses_canonical_schema_and_status() -> None:
    target = load_target()

    assert target["schema"] == "qflpn-p3-hpc-target-v2"
    assert target["status"] == (
        "PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE"
    )


def test_repository_target_uses_nested_hardware_target() -> None:
    target = load_target()
    hardware = target["hardware_target"]

    assert hardware["compute_nodes"] == 16
    assert hardware["physical_cores_total"] == 664
    assert hardware["ram_gib_total"] == 4096
    assert hardware["ram_gib_per_node"] == 256


def test_repository_target_declares_exact_node_core_distribution() -> None:
    hardware = load_target()["hardware_target"]

    assert hardware["node_groups"] == [
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

    assert 8 * 42 + 8 * 41 == 664


def test_repository_target_declares_motherboard_collection_contract() -> None:
    board = load_target()["hardware_target"]["motherboard"]

    assert board["collection_required"] is True
    assert board["fields"] == [
        "manufacturer",
        "model",
        "version",
    ]
    assert board["source"] == "/sys/class/dmi/id/"
    assert board["missing_value"] == "UNAVAILABLE"


def test_repository_target_declares_spmv_proposal_without_claiming_execution() -> None:
    benchmark = load_target()["benchmark"]

    assert benchmark["workload"] == "SpMV"
    assert benchmark["parallelism_target"] == 664
    assert 664 in benchmark["worker_counts"]
    assert benchmark["maximum_target_dimension"] == 10_000_000
    assert 10_000_000 in benchmark["thresholds"]
    assert benchmark["minimum_warmup"] == 5
    assert benchmark["minimum_valid_measurements"] == 30
    assert benchmark["execution_status"] == "NOT_EXECUTED"


def test_collector_validates_actual_nested_target_configuration() -> None:
    result = COLLECTOR.validate_configuration(load_target())
    by_id = checks_by_id(result["checks"])

    assert result["overall"] == "PASS"
    assert len(result["expected_cores_by_node"]) == 16
    assert result["expected_nodes"] == 16
    assert result["expected_physical_cores"] == 664

    assert by_id["CONFIG_STATUS"]["status"] == "PASS"
    assert by_id["HARDWARE_TARGET_INTERNAL_CONSISTENCY"]["status"] == "PASS"
    assert by_id["MOTHERBOARD_COLLECTION_CONTRACT"]["status"] == "PASS"
    assert by_id["SPMV_BENCHMARK_PROPOSAL"]["status"] == "PASS"


def test_collector_rejects_wrong_target_schema() -> None:
    target = load_target()
    target["schema"] = "qflpn-p3-hpc-target-v1"

    result = COLLECTOR.validate_configuration(target)
    by_id = checks_by_id(result["checks"])

    assert result["overall"] == "FAIL"
    assert by_id["CONFIG_SCHEMA"]["status"] == "FAIL"


def test_collector_rejects_wrong_physical_core_total() -> None:
    target = load_target()
    target["hardware_target"]["physical_cores_total"] = 672

    result = COLLECTOR.validate_configuration(target)
    by_id = checks_by_id(result["checks"])

    assert result["overall"] == "FAIL"
    assert by_id["HARDWARE_TARGET_INTERNAL_CONSISTENCY"]["status"] == "FAIL"


def test_collector_rejects_wrong_node_core_distribution() -> None:
    target = load_target()
    target["hardware_target"]["node_groups"][0][
        "physical_cores_per_node"
    ] = 43

    result = COLLECTOR.validate_configuration(target)
    by_id = checks_by_id(result["checks"])

    assert result["overall"] == "FAIL"
    assert by_id["HARDWARE_TARGET_INTERNAL_CONSISTENCY"]["status"] == "FAIL"


def test_collector_rejects_missing_motherboard_contract() -> None:
    target = load_target()
    del target["hardware_target"]["motherboard"]["fields"]

    result = COLLECTOR.validate_configuration(target)
    by_id = checks_by_id(result["checks"])

    assert result["overall"] == "FAIL"
    assert by_id["MOTHERBOARD_COLLECTION_CONTRACT"]["status"] == "FAIL"


# ---------------------------------------------------------------------------
# CPU, RAM and cgroup parsing
# ---------------------------------------------------------------------------

CPUINFO = """processor : 0
model name : Example CPU
physical id : 0
core id : 0

processor : 1
model name : Example CPU
physical id : 0
core id : 0

processor : 2
model name : Example CPU
physical id : 0
core id : 1

processor : 3
model name : Example CPU
physical id : 1
core id : 0

processor : 4
model name : Example CPU
physical id : 1
core id : 0
"""


def test_cpuinfo_parser_counts_physical_cores_sockets_and_logical_processors() -> None:
    result = COLLECTOR.parse_cpuinfo(CPUINFO)

    assert result["logical_processors"] == 5
    assert result["physical_cores"] == 3
    assert result["sockets"] == 2
    assert result["cpu_model"] == "Example CPU"


def test_cpuinfo_without_physical_topology_keeps_core_count_unknown() -> None:
    result = COLLECTOR.parse_cpuinfo(
        "processor : 0\nprocessor : 1\n"
    )

    assert result["logical_processors"] == 2
    assert result["physical_cores"] is None
    assert result["sockets"] is None


def test_meminfo_parser_converts_kib_to_gib() -> None:
    assert (
        COLLECTOR.parse_meminfo_gib(
            "MemTotal:  268435456 kB\n"
        )
        == 256.0
    )
    assert COLLECTOR.parse_meminfo_gib("not available") is None


def test_cgroup_v2_cpu_quota_parser() -> None:
    assert COLLECTOR.parse_cgroup_cpu_max("200000 100000") == 2.0
    assert COLLECTOR.parse_cgroup_cpu_max("max 100000") is None
    assert COLLECTOR.parse_cgroup_cpu_max("invalid") is None


def test_cgroup_v1_cpu_quota_parser() -> None:
    assert COLLECTOR.parse_cgroup_v1_cpu_quota(
        "200000",
        "100000",
    ) == 2.0

    assert COLLECTOR.parse_cgroup_v1_cpu_quota(
        "-1",
        "100000",
    ) is None

    assert COLLECTOR.parse_cgroup_v1_cpu_quota(
        "invalid",
        "100000",
    ) is None


def test_usable_cores_uses_the_minimum_known_cpu_limit() -> None:
    item = {
        "physical_cores": 42,
        "cpu_affinity_count": 8,
        "cgroup_cpu_quota_cores": 4.0,
    }

    assert COLLECTOR.usable_cores(item) == 4.0
    assert COLLECTOR.usable_cores({}) is None


# ---------------------------------------------------------------------------
# Motherboard collection
# ---------------------------------------------------------------------------

def test_motherboard_collection_reads_all_three_dmi_fields(
    tmp_path: Path,
) -> None:
    (tmp_path / "board_vendor").write_text(
        "Example Manufacturer\n",
        encoding="utf-8",
    )
    (tmp_path / "board_name").write_text(
        "Example HPC Board\n",
        encoding="utf-8",
    )
    (tmp_path / "board_version").write_text(
        "2.1\n",
        encoding="utf-8",
    )

    result = COLLECTOR.collect_motherboard(tmp_path)

    assert result == {
        "manufacturer": "Example Manufacturer",
        "model": "Example HPC Board",
        "version": "2.1",
    }


def test_missing_motherboard_fields_are_unavailable(
    tmp_path: Path,
) -> None:
    result = COLLECTOR.collect_motherboard(tmp_path)

    assert result == {
        "manufacturer": "UNAVAILABLE",
        "model": "UNAVAILABLE",
        "version": "UNAVAILABLE",
    }


def test_empty_motherboard_field_is_unavailable(
    tmp_path: Path,
) -> None:
    (tmp_path / "board_vendor").write_text(
        "\n",
        encoding="utf-8",
    )
    (tmp_path / "board_name").write_text(
        "Example HPC Board\n",
        encoding="utf-8",
    )
    (tmp_path / "board_version").write_text(
        "1.0\n",
        encoding="utf-8",
    )

    result = COLLECTOR.collect_motherboard(tmp_path)

    assert result["manufacturer"] == "UNAVAILABLE"
    assert result["model"] == "Example HPC Board"
    assert result["version"] == "1.0"


def test_placeholder_motherboard_values_are_unavailable(
    tmp_path: Path,
) -> None:
    (tmp_path / "board_vendor").write_text(
        "To be filled by O.E.M.\n",
        encoding="utf-8",
    )
    (tmp_path / "board_name").write_text(
        "Default string\n",
        encoding="utf-8",
    )
    (tmp_path / "board_version").write_text(
        "None\n",
        encoding="utf-8",
    )

    result = COLLECTOR.collect_motherboard(tmp_path)

    assert result == {
        "manufacturer": "UNAVAILABLE",
        "model": "UNAVAILABLE",
        "version": "UNAVAILABLE",
    }


# ---------------------------------------------------------------------------
# Node inventory and aggregation
# ---------------------------------------------------------------------------

def test_collector_returns_canonical_node_schema() -> None:
    result = COLLECTOR.collect()

    assert result["schema"] == "qflpn-p3-hpc-node-inventory-v1"
    assert isinstance(result["hostname"], str)
    assert result["hostname"]
    assert "physical_cores" in result
    assert "logical_processors" in result
    assert "cpu_affinity_count" in result
    assert "cgroup_cpu_quota_cores" in result
    assert "memory_gib" in result

    assert result["motherboard"] == {
        "manufacturer": result["motherboard"]["manufacturer"],
        "model": result["motherboard"]["model"],
        "version": result["motherboard"]["version"],
    }

    assert all(
        isinstance(result["motherboard"][field], str)
        and result["motherboard"][field]
        for field in ("manufacturer", "model", "version")
    )


def test_aggregate_uses_canonical_cluster_schema() -> None:
    result = COLLECTOR.aggregate(
        full_cluster(),
        collected_utc="2026-11-01T00:00:00Z",
    )

    assert result["schema"] == (
        "qflpn-p3-hpc-cluster-inventory-v1"
    )
    assert result["node_count"] == 16
    assert result["distinct_hostname_count"] == 16
    assert len(result["nodes"]) == 16
    assert result["collected_utc"] == "2026-11-01T00:00:00Z"


def test_aggregate_preserves_node_motherboard_fields() -> None:
    nodes = full_cluster()
    result = COLLECTOR.aggregate(nodes)

    assert result["nodes"][0]["motherboard"] == motherboard()
    assert all(
        "motherboard" in item
        for item in result["nodes"]
    )


def test_aggregate_does_not_silently_drop_duplicate_hostnames() -> None:
    nodes = full_cluster()
    nodes[1]["hostname"] = nodes[0]["hostname"]

    result = COLLECTOR.aggregate(nodes)

    assert result["node_count"] == 16
    assert result["distinct_hostname_count"] == 15

    validation = COLLECTOR.validate_target(load_target(), result["nodes"])
    by_id = checks_by_id(validation["inventory_validation"]["checks"])

    assert validation["overall"] == "FAIL"
    assert by_id["DISTINCT_COMPUTE_NODES"]["status"] == "FAIL"


def test_aggregate_rejects_wrong_node_schema() -> None:
    nodes = full_cluster()
    nodes[0]["schema"] = "wrong-schema"

    with pytest.raises(ValueError):
        COLLECTOR.aggregate(nodes)


def test_aggregate_rejects_non_object_node() -> None:
    with pytest.raises(ValueError):
        COLLECTOR.aggregate([{"schema": COLLECTOR.NODE_SCHEMA}, "invalid"])


def test_aggregate_file_is_readable_by_the_real_validator(
    tmp_path: Path,
) -> None:
    aggregate_value = COLLECTOR.aggregate(full_cluster())
    aggregate_path = write_json(
        tmp_path / "cluster-inventory.json",
        aggregate_value,
    )

    loaded_nodes = VALIDATOR.load_inventory_files([aggregate_path])

    assert len(loaded_nodes) == 16
    assert all(
        item["schema"] == VALIDATOR.NODE_SCHEMA
        for item in loaded_nodes
    )

    _, parsed_target = VALIDATOR.validate_configuration(load_target())

    status, checks, summary = VALIDATOR.validate_inventory(
        loaded_nodes,
        parsed_target,
    )

    by_id = checks_by_id(checks)

    assert status == "PASS"
    assert by_id["COMPUTE_NODE_SET"]["status"] == "PASS"
    assert by_id["PHYSICAL_CORE_TOPOLOGY"]["status"] == "PASS"
    assert by_id["MOTHERBOARD_INVENTORY"]["status"] == "PASS"
    assert summary["node_count_observed"] == 16
    assert summary["physical_cores_observed"] == 664


def test_validator_accepts_individual_node_inventory_files(
    tmp_path: Path,
) -> None:
    paths = [
        write_json(
            tmp_path / f"node-{index:02d}.json",
            item,
        )
        for index, item in enumerate(full_cluster(), start=1)
    ]

    loaded_nodes = VALIDATOR.load_inventory_files(paths)

    assert len(loaded_nodes) == 16
    assert {
        item["hostname"]
        for item in loaded_nodes
    } == {
        f"HPC-{index:02d}"
        for index in range(1, 17)
    }


# ---------------------------------------------------------------------------
# Inventory validation and failure cases
# ---------------------------------------------------------------------------

def test_full_reference_cluster_satisfies_hardware_inventory_checks() -> None:
    result = COLLECTOR.validate_target(
        load_target(),
        full_cluster(),
    )

    assert result["overall"] == "PASS"

    by_id = checks_by_id(
        result["inventory_validation"]["checks"]
    )

    assert by_id["DISTINCT_COMPUTE_NODES"]["status"] == "PASS"
    assert by_id["COMPUTE_NODE_SET"]["status"] == "PASS"
    assert by_id["PHYSICAL_CORE_TOPOLOGY"]["status"] == "PASS"
    assert by_id["TOTAL_RAM"]["status"] == "PASS"
    assert by_id["RAM_PER_NODE"]["status"] == "PASS"
    assert by_id["MOTHERBOARD_INVENTORY"]["status"] == "PASS"
    assert by_id["EFFECTIVE_CPU_CAPACITY"]["status"] == "PASS"


def test_no_inventory_is_deferred_not_pass() -> None:
    result = COLLECTOR.validate_target(load_target(), [])

    assert result["overall"] == "DEFERRED"

    by_id = checks_by_id(
        result["inventory_validation"]["checks"]
    )

    assert by_id["INVENTORY_PRESENT"]["status"] == "DEFERRED"
    assert by_id["MOTHERBOARD_INVENTORY"]["status"] == "DEFERRED"


def test_fifteen_nodes_are_deferred() -> None:
    result = COLLECTOR.validate_target(
        load_target(),
        full_cluster()[:15],
    )

    assert result["overall"] == "DEFERRED"

    by_id = checks_by_id(
        result["inventory_validation"]["checks"]
    )

    assert by_id["COMPUTE_NODE_SET"]["status"] == "DEFERRED"
    assert by_id["PHYSICAL_CORE_TOPOLOGY"]["status"] == "DEFERRED"


def test_duplicate_hostnames_fail() -> None:
    nodes = full_cluster()
    nodes[1]["hostname"] = nodes[0]["hostname"]

    result = COLLECTOR.validate_target(load_target(), nodes)

    assert result["overall"] == "FAIL"

    by_id = checks_by_id(
        result["inventory_validation"]["checks"]
    )

    assert by_id["DISTINCT_COMPUTE_NODES"]["status"] == "FAIL"


def test_wrong_physical_core_count_fails() -> None:
    nodes = full_cluster()
    nodes[0]["physical_cores"] = 40

    result = COLLECTOR.validate_target(load_target(), nodes)

    assert result["overall"] == "FAIL"

    by_id = checks_by_id(
        result["inventory_validation"]["checks"]
    )

    assert by_id["PHYSICAL_CORE_TOPOLOGY"]["status"] == "FAIL"


def test_unavailable_motherboard_defers_motherboard_check() -> None:
    nodes = full_cluster()
    nodes[0]["motherboard"] = {
        "manufacturer": "UNAVAILABLE",
        "model": "Example HPC Board",
        "version": "1.0",
    }

    result = COLLECTOR.validate_target(load_target(), nodes)

    assert result["overall"] == "DEFERRED"

    by_id = checks_by_id(
        result["inventory_validation"]["checks"]
    )

    assert by_id["MOTHERBOARD_INVENTORY"]["status"] == "DEFERRED"


def test_missing_motherboard_object_defers_motherboard_check() -> None:
    nodes = full_cluster()
    del nodes[0]["motherboard"]

    result = COLLECTOR.validate_target(load_target(), nodes)

    assert result["overall"] == "DEFERRED"

    by_id = checks_by_id(
        result["inventory_validation"]["checks"]
    )

    assert by_id["MOTHERBOARD_INVENTORY"]["status"] == "DEFERRED"


def test_low_cpu_affinity_defers_effective_capacity() -> None:
    nodes = full_cluster()
    nodes[0]["cpu_affinity_count"] = 8

    result = COLLECTOR.validate_target(load_target(), nodes)

    assert result["overall"] == "DEFERRED"

    by_id = checks_by_id(
        result["inventory_validation"]["checks"]
    )

    assert by_id["EFFECTIVE_CPU_CAPACITY"]["status"] == "DEFERRED"


def test_low_cgroup_quota_defers_effective_capacity() -> None:
    nodes = full_cluster()
    nodes[0]["cgroup_cpu_quota_cores"] = 4.0

    result = COLLECTOR.validate_target(load_target(), nodes)

    assert result["overall"] == "DEFERRED"

    by_id = checks_by_id(
        result["inventory_validation"]["checks"]
    )

    assert by_id["EFFECTIVE_CPU_CAPACITY"]["status"] == "DEFERRED"


def test_insufficient_ram_fails_per_node_check() -> None:
    nodes = full_cluster()
    nodes[0]["memory_gib"] = 128.0

    result = COLLECTOR.validate_target(load_target(), nodes)

    assert result["overall"] == "FAIL"

    by_id = checks_by_id(
        result["inventory_validation"]["checks"]
    )

    assert by_id["RAM_PER_NODE"]["status"] == "FAIL"


def test_unknown_inventory_schema_is_rejected_by_validator(
    tmp_path: Path,
) -> None:
    path = write_json(
        tmp_path / "invalid-inventory.json",
        {
            "schema": "unknown-schema",
            "hostname": "HPC-01",
        },
    )

    with pytest.raises(VALIDATOR.InputError):
        VALIDATOR.load_inventory_files([path])


def test_aggregate_without_nodes_array_is_rejected_by_validator(
    tmp_path: Path,
) -> None:
    path = write_json(
        tmp_path / "invalid-aggregate.json",
        {
            "schema": COLLECTOR.AGGREGATE_SCHEMA,
        },
    )

    with pytest.raises(VALIDATOR.InputError):
        VALIDATOR.load_inventory_files([path])


def test_execution_evidence_remains_not_executed() -> None:
    result = COLLECTOR.validate_target(
        load_target(),
        full_cluster(),
    )

    evidence = result["execution_evidence"]

    assert evidence["benchmark_execution_status"] == "NOT_EXECUTED"
    assert evidence["664_worker_execution_demonstrated"] is False
    assert evidence["dimension_10000000_execution_demonstrated"] is False
    assert evidence["this_report_is_not_performance_evidence"] is True


# ---------------------------------------------------------------------------
# Command-line integration
# ---------------------------------------------------------------------------

def test_aggregate_cli_writes_validator_compatible_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_paths = [
        write_json(
            tmp_path / f"node-{index:02d}.json",
            item,
        )
        for index, item in enumerate(full_cluster(), start=1)
    ]

    output_path = tmp_path / "reports" / "cluster-inventory.json"

    arguments = [
        "aggregate",
        str(output_path),
        *[str(path) for path in input_paths],
    ]

    assert COLLECTOR.main(arguments) == 0
    assert output_path.is_file()

    aggregate_value = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert aggregate_value["schema"] == COLLECTOR.AGGREGATE_SCHEMA
    assert aggregate_value["node_count"] == 16

    loaded_nodes = VALIDATOR.load_inventory_files([output_path])
    assert len(loaded_nodes) == 16


def test_validate_cli_accepts_nested_target_and_aggregate_inventory(
    tmp_path: Path,
) -> None:
    target_path = write_json(
        tmp_path / "hpc-target.json",
        load_target(),
    )

    aggregate_path = write_json(
        tmp_path / "cluster-inventory.json",
        COLLECTOR.aggregate(full_cluster()),
    )

    from contextlib import redirect_stdout
    from io import StringIO

    output = StringIO()

    with redirect_stdout(output):
        exit_code = COLLECTOR.main([
            "validate",
            str(target_path),
            str(aggregate_path),
        ])

    assert exit_code == 0

    report = json.loads(output.getvalue())

    assert report["overall"] == "PASS"
    assert report["configuration_validation"]["overall"] == "PASS"
    assert report["inventory_validation"]["overall"] == "PASS"
    assert report["execution_evidence"]["benchmark_execution_status"] == (
        "NOT_EXECUTED"
    )


def test_validate_cli_returns_nonzero_for_deferred_inventory(
    tmp_path: Path,
) -> None:
    target_path = write_json(
        tmp_path / "hpc-target.json",
        load_target(),
    )

    from contextlib import redirect_stdout
    from io import StringIO

    output = StringIO()

    with redirect_stdout(output):
        exit_code = COLLECTOR.main([
            "validate",
            str(target_path),
        ])

    report = json.loads(output.getvalue())

    assert exit_code == 1
    assert report["overall"] == "DEFERRED"
    assert report["inventory_validation"]["overall"] == "DEFERRED"
