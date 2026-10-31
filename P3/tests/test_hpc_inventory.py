#!/usr/bin/env python3
"""Tests for P3/hpc/tools/collect_hpc_inventory.py and the 664-core target."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "P3" / "hpc" / "tools" / "collect_hpc_inventory.py"
TARGET = ROOT / "P3" / "hpc" / "config" / "hpc-664.json"

SPEC = importlib.util.spec_from_file_location("qflpn_hpc_inventory", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

CPUINFO = """processor\t: 0
model name\t: Example CPU
physical id\t: 0
core id\t: 0

processor\t: 1
model name\t: Example CPU
physical id\t: 0
core id\t: 0

processor\t: 2
model name\t: Example CPU
physical id\t: 0
core id\t: 1

processor\t: 3
model name\t: Example CPU
physical id\t: 1
core id\t: 0

processor\t: 4
model name\t: Example CPU
physical id\t: 1
core id\t: 0
"""


def target() -> dict:
    return json.loads(TARGET.read_text(encoding="utf-8"))


def node(host: str, cores: int, ram: float = 256.0, mpi: str = "mpirun 5") -> dict:
    return {"hostname": host, "physical_cores": cores,
            "cpu_affinity_count": cores, "cgroup_cpu_quota_cores": None,
            "memory_gib": ram, "mpi": mpi}


def full_cluster() -> list[dict]:
    return ([node(f"HPC-{i:02d}", 42) for i in range(1, 9)]
            + [node(f"HPC-{i:02d}", 41) for i in range(9, 17)])


def status(result: dict) -> dict[str, str]:
    return {c["id"]: c["status"] for c in result["checks"]}


def test_target_file_is_internally_consistent() -> None:
    t = target()
    assert t["physical_cores_total"] == 8 * 42 + 8 * 41 == 664
    assert t["compute_nodes"] * t["ram_gib_per_node"] == t["ram_gib_total"] == 4096
    assert 672 in t["oversubscribed_points"]
    assert 672 > t["physical_cores_total"]
    assert "NOT_EVIDENCE" in t["status"]


def test_cpuinfo_parsing_counts_distinct_physical_cores_and_sockets() -> None:
    info = MODULE.parse_cpuinfo(CPUINFO)
    assert info["logical_processors"] == 5
    assert info["physical_cores"] == 3           # (0,0) (0,1) (1,0)
    assert info["sockets"] == 2
    assert info["cpu_model"] == "Example CPU"


def test_cpuinfo_without_topology_keeps_physical_cores_unknown() -> None:
    info = MODULE.parse_cpuinfo("processor\t: 0\nprocessor\t: 1\n")
    assert info["logical_processors"] == 2
    assert info["physical_cores"] is None


def test_meminfo_and_cgroup_parsing() -> None:
    assert MODULE.parse_meminfo_gib("MemTotal:  268435456 kB\n") == 256.0
    assert MODULE.parse_meminfo_gib("nothing") is None
    assert MODULE.parse_cgroup_cpu_max("max 100000") is None
    assert MODULE.parse_cgroup_cpu_max("200000 100000") == 2.0
    assert MODULE.parse_cgroup_cpu_max("garbage") is None


def test_usable_cores_is_the_minimum_of_every_limit() -> None:
    n = {"physical_cores": 42, "cpu_affinity_count": 8,
         "cgroup_cpu_quota_cores": 4.0}
    assert MODULE.usable_cores(n) == 4
    assert MODULE.usable_cores({}) is None


def test_the_full_reference_cluster_passes() -> None:
    result = MODULE.validate_target(target(), full_cluster())
    assert result["overall"] == "PASS", result
    assert sum(MODULE.usable_cores(n) for n in full_cluster()) == 664


def test_no_inventory_is_deferred_never_pass() -> None:
    result = MODULE.validate_target(target(), [])
    assert result["overall"] == "DEFERRED"
    assert status(result)["T1_INVENTORIES_PRESENT"] == "DEFERRED"


def test_fifteen_nodes_are_deferred() -> None:
    result = MODULE.validate_target(target(), full_cluster()[:15])
    assert result["overall"] == "DEFERRED"
    assert status(result)["T4_NODE_COUNT"] == "DEFERRED"
    assert status(result)["T5_CORE_COUNT"] == "DEFERRED"


def test_one_big_node_does_not_demonstrate_a_cluster() -> None:
    result = MODULE.validate_target(target(), [node("big", 664, 4096.0)])
    assert result["overall"] == "DEFERRED"
    assert status(result)["T4_NODE_COUNT"] == "DEFERRED"


def test_duplicate_hostnames_fail() -> None:
    nodes = full_cluster()
    nodes[1] = dict(nodes[0])
    result = MODULE.validate_target(target(), nodes)
    assert result["overall"] == "FAIL"
    assert status(result)["T2_DISTINCT_NODES"] == "FAIL"


def test_an_affinity_mask_smaller_than_the_target_is_detected() -> None:
    nodes = full_cluster()
    nodes[0]["cpu_affinity_count"] = 8          # job only sees 8 cores there
    result = MODULE.validate_target(target(), nodes)
    assert status(result)["T5_CORE_COUNT"] == "DEFERRED"


def test_unknown_core_count_and_memory_are_deferred() -> None:
    nodes = full_cluster()
    nodes[0] = {"hostname": "HPC-01", "memory_gib": None, "mpi": "x"}
    result = MODULE.validate_target(target(), nodes)
    assert status(result)["T3_CORES_KNOWN_FOR_EVERY_NODE"] == "DEFERRED"
    assert status(result)["T6_RAM"] == "DEFERRED"


def test_missing_mpi_is_deferred() -> None:
    nodes = full_cluster()
    nodes[3]["mpi"] = None
    assert status(MODULE.validate_target(target(), nodes))["T7_MPI_PRESENT"] \
        == "DEFERRED"


def test_inconsistent_target_fails() -> None:
    t = target()
    t["physical_cores_total"] = 700
    result = MODULE.validate_target(t, full_cluster())
    assert status(result)["T0_TARGET_IS_INTERNALLY_CONSISTENT"] == "FAIL"
    assert result["overall"] == "FAIL"


def test_run_classification_separates_intra_node_from_distributed() -> None:
    t = target()
    assert MODULE.classify_run(1, 664, t) == "INTRA_NODE_ONLY"
    assert MODULE.classify_run(8, 336, t) == "PARTIAL_CLUSTER"
    assert MODULE.classify_run(16, 664, t) == "FULL_CLUSTER"


def test_collect_returns_the_documented_schema() -> None:
    inventory = MODULE.collect()
    assert inventory["schema"] == MODULE.SCHEMA
    assert isinstance(inventory["hostname"], str)
    assert inventory["logical_processors"] and inventory["logical_processors"] > 0
