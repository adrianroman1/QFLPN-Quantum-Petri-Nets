#!/usr/bin/env python3
"""Collect and aggregate QFLPN P3 HPC node inventories.

Commands
--------
collect
    Collect the current node inventory and write JSON to stdout.

aggregate OUTPUT NODE.json [NODE.json ...]
    Combine node inventory files into one cluster inventory.

validate TARGET.json NODE.json [NODE.json ...]
    Validate the nested hardware_target configuration and supplied node
    inventories. The output is JSON and includes an "overall" field for
    compatibility with the existing Slurm preflight contract.

Schemas
-------
Node:
    qflpn-p3-hpc-node-inventory-v1

Aggregate:
    qflpn-p3-hpc-cluster-inventory-v1

The collector records observed hardware and runtime limits. It does not
execute SpMV, measure performance, or prove that the proposed 664-worker /
10,000,000-dimension benchmark has run.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


NODE_SCHEMA = "qflpn-p3-hpc-node-inventory-v1"
AGGREGATE_SCHEMA = "qflpn-p3-hpc-cluster-inventory-v1"
CONFIG_SCHEMA = "qflpn-p3-hpc-target-v2"

# Backward-compatible public constant used by existing tests/tools.
SCHEMA = NODE_SCHEMA

DMI_ROOT = Path("/sys/class/dmi/id/")
MOTHERBOARD_FILES = {
    "manufacturer": "board_vendor",
    "model": "board_name",
    "version": "board_version",
}


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: str | Path) -> str:
    """Read a text file; return an empty string when unavailable."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def normalize_inventory_value(value: str | None) -> str:
    """Normalize absent or unusable hardware-identification values."""
    if not isinstance(value, str):
        return "UNAVAILABLE"

    normalized = value.strip()
    if not normalized or normalized.lower() in {
        "none",
        "null",
        "unknown",
        "not specified",
        "to be filled by o.e.m.",
        "default string",
    }:
        return "UNAVAILABLE"

    return normalized


def collect_motherboard(dmi_root: str | Path = DMI_ROOT) -> dict[str, str]:
    """Collect motherboard manufacturer, model and version from DMI sysfs.

    Missing, unreadable, empty, or placeholder values are represented by the
    literal string "UNAVAILABLE". No motherboard identity is inferred.
    """
    root = Path(dmi_root)
    result: dict[str, str] = {}

    for field, filename in MOTHERBOARD_FILES.items():
        result[field] = normalize_inventory_value(
            read_text(root / filename)
        )

    return result


def parse_cpuinfo(text: str) -> dict[str, Any]:
    """Parse logical processors, physical cores, sockets and CPU model."""
    logical = 0
    core_pairs: set[tuple[str, str]] = set()
    sockets: set[str] = set()
    model: str | None = None

    current_physical_id: str | None = None
    current_core_id: str | None = None

    def finish_processor() -> None:
        if current_physical_id is not None and current_core_id is not None:
            core_pairs.add((current_physical_id, current_core_id))
            sockets.add(current_physical_id)

    for line in text.splitlines() + [""]:
        if not line.strip():
            finish_processor()
            current_physical_id = None
            current_core_id = None
            continue

        key, separator, value = line.partition(":")
        if not separator:
            continue

        key = key.strip()
        value = value.strip()

        if key == "processor":
            logical += 1
        elif key == "physical id":
            current_physical_id = value
        elif key == "core id":
            current_core_id = value
        elif key == "model name" and value and model is None:
            model = value

    return {
        "logical_processors": logical,
        "physical_cores": len(core_pairs) or None,
        "sockets": len(sockets) or None,
        "cpu_model": model,
    }


def parse_meminfo_gib(text: str) -> float | None:
    """Parse MemTotal from /proc/meminfo and return GiB."""
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB", text, re.MULTILINE)
    if not match:
        return None
    return round(int(match.group(1)) / 1024 / 1024, 3)


def parse_cgroup_cpu_max(text: str) -> float | None:
    """Parse cgroup v2 cpu.max and return the quota in CPU cores."""
    parts = text.split()
    if len(parts) != 2 or parts[0] == "max":
        return None

    try:
        quota = int(parts[0])
        period = int(parts[1])
        if quota <= 0 or period <= 0:
            return None
        return round(quota / period, 3)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def parse_cgroup_v1_cpu_quota(
    quota_text: str,
    period_text: str,
) -> float | None:
    """Parse cgroup v1 cpu.cfs_quota_us and cpu.cfs_period_us."""
    try:
        quota = int(quota_text.strip())
        period = int(period_text.strip())
    except (TypeError, ValueError):
        return None

    # A negative quota means unlimited in cgroup v1.
    if quota <= 0 or period <= 0:
        return None

    return round(quota / period, 3)


def collect_cgroup_cpu_quota() -> float | None:
    """Read CPU quota from cgroup v2, falling back to cgroup v1."""
    v2 = parse_cgroup_cpu_max(read_text("/sys/fs/cgroup/cpu.max"))
    if v2 is not None:
        return v2

    return parse_cgroup_v1_cpu_quota(
        read_text("/sys/fs/cgroup/cpu/cpu.cfs_quota_us"),
        read_text("/sys/fs/cgroup/cpu/cpu.cfs_period_us"),
    )


def run_version(command: list[str]) -> str | None:
    """Return the first output line of a version command, if available."""
    if not command or shutil.which(command[0]) is None:
        return None

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        output = (completed.stdout or completed.stderr).strip()
        return output.splitlines()[0] if output else None
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


def collect_slurm_environment() -> dict[str, str]:
    """Collect the selected Slurm variables relevant to node provenance."""
    allowed = {
        "SLURM_JOB_ID",
        "SLURM_JOB_NODELIST",
        "SLURM_NNODES",
        "SLURM_CPUS_ON_NODE",
        "SLURM_CPUS_PER_TASK",
        "SLURM_NTASKS",
        "SLURM_PROCID",
        "SLURM_NODEID",
        "SLURM_LOCALID",
        "SLURM_CPU_BIND",
    }

    return {
        key: os.environ[key]
        for key in sorted(allowed)
        if key in os.environ
    }


def collect_numa_nodes() -> list[str]:
    """Return visible NUMA node directory names."""
    root = Path("/sys/devices/system/node")
    if not root.is_dir():
        return []

    return sorted(
        path.name
        for path in root.glob("node[0-9]*")
        if path.is_dir()
    )


def collect() -> dict[str, Any]:
    """Collect the current node's hardware and execution environment."""
    cpu = parse_cpuinfo(read_text("/proc/cpuinfo"))

    try:
        affinity_ids = sorted(os.sched_getaffinity(0))
        affinity_count: int | None = len(affinity_ids)
    except (AttributeError, OSError):
        affinity_ids = []
        affinity_count = None

    logical_processors = cpu["logical_processors"] or os.cpu_count()

    return {
        "schema": NODE_SCHEMA,
        "collected_utc": utc_now(),
        "hostname": platform.node() or "UNAVAILABLE",
        "os": platform.platform(),
        "kernel": platform.release(),
        "python": platform.python_version(),
        "cpu_model": cpu["cpu_model"] or "UNAVAILABLE",
        "sockets": cpu["sockets"],
        "physical_cores": cpu["physical_cores"],
        "logical_processors": logical_processors,
        "cpu_affinity_count": affinity_count,
        "cpu_affinity_ids": affinity_ids,
        "cgroup_cpu_quota_cores": collect_cgroup_cpu_quota(),
        "memory_gib": parse_meminfo_gib(read_text("/proc/meminfo")),
        "numa_nodes": collect_numa_nodes(),
        "motherboard": collect_motherboard(),
        "slurm": collect_slurm_environment(),
        "java": run_version(["java", "-version"]),
        "maven": run_version(["mvn", "-version"]),
        "mpi": (
            run_version(["mpirun", "--version"])
            or run_version(["mpiexec", "--version"])
        ),
    }


def usable_cores(node: dict[str, Any]) -> float | None:
    """Return the minimum known physical, affinity and cgroup CPU limit."""
    limits: list[float] = []

    for key in (
        "physical_cores",
        "cpu_affinity_count",
        "cgroup_cpu_quota_cores",
    ):
        value = node.get(key)
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            and value > 0
        ):
            limits.append(float(value))

    return min(limits) if limits else None


def normalize_hostname(value: Any) -> str | None:
    """Normalize a hostname for comparison with the target node ranges."""
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().split(".", 1)[0].lower()


def expected_node_core_map(hardware: dict[str, Any]) -> dict[str, int]:
    """Expand hardware_target.node_groups into hostname -> core-count map."""
    groups = hardware.get("node_groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("hardware_target.node_groups must be a non-empty list")

    expected: dict[str, int] = {}

    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("Every node_groups entry must be an object")

        names = group.get("names")
        count = group.get("nodes")
        cores = group.get("physical_cores_per_node")

        if not isinstance(names, str):
            raise ValueError("node_groups.names must be a string")
        if (
            not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
        ):
            raise ValueError("node_groups.nodes must be a positive integer")
        if (
            not isinstance(cores, int)
            or isinstance(cores, bool)
            or cores <= 0
        ):
            raise ValueError(
                "node_groups.physical_cores_per_node must be a positive integer"
            )

        match = re.fullmatch(
            r"\s*([A-Za-z0-9_-]+)-(\d+)\.\.([A-Za-z0-9_-]+)-(\d+)\s*",
            names,
        )
        if not match or match.group(1).lower() != match.group(3).lower():
            raise ValueError(
                f"Unsupported node range {names!r}; expected HPC-01..HPC-08"
            )

        prefix = match.group(1)
        first = int(match.group(2))
        last = int(match.group(4))

        if last < first or last - first + 1 != count:
            raise ValueError(
                f"Node range {names!r} does not match declared count {count}"
            )

        for number in range(first, last + 1):
            hostname = f"{prefix}-{number:02d}".lower()
            if hostname in expected:
                raise ValueError(f"Duplicate target hostname: {hostname}")
            expected[hostname] = cores

    return expected


def validate_configuration(target: dict[str, Any]) -> dict[str, Any]:
    """Validate the actual nested hpc-target.json structure."""
    checks: list[dict[str, str]] = []

    def add(check_id: str, status: str, detail: str) -> None:
        checks.append({
            "id": check_id,
            "status": status,
            "detail": detail,
        })

    if target.get("schema") != CONFIG_SCHEMA:
        add(
            "CONFIG_SCHEMA",
            "FAIL",
            f"Expected {CONFIG_SCHEMA}; got {target.get('schema')!r}",
        )
        return {
            "overall": "FAIL",
            "checks": checks,
            "expected_cores_by_node": {},
        }

    if target.get("status") != "PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE":
        add(
            "CONFIG_STATUS",
            "FAIL",
            "Target must remain marked as proposed reference configuration, not evidence.",
        )
    else:
        add(
            "CONFIG_STATUS",
            "PASS",
            "Target is explicitly marked as proposed, not execution evidence.",
        )

    hardware = target.get("hardware_target")
    benchmark = target.get("benchmark")

    if not isinstance(hardware, dict):
        add("HARDWARE_TARGET_OBJECT", "FAIL",
            "hardware_target must be a JSON object.")
        return {"overall": "FAIL", "checks": checks,
                "expected_cores_by_node": {}}

    if not isinstance(benchmark, dict):
        add("BENCHMARK_OBJECT", "FAIL",
            "benchmark must be a JSON object.")
        return {"overall": "FAIL", "checks": checks,
                "expected_cores_by_node": {}}

    try:
        expected_map = expected_node_core_map(hardware)
    except ValueError as exc:
        expected_map = {}
        add("NODE_GROUPS", "FAIL", str(exc))

    compute_nodes = hardware.get("compute_nodes")
    physical_cores = hardware.get("physical_cores_total")
    ram_total = hardware.get("ram_gib_total")
    ram_per_node = hardware.get("ram_gib_per_node")

    integer_fields_valid = (
        isinstance(compute_nodes, int)
        and not isinstance(compute_nodes, bool)
        and isinstance(physical_cores, int)
        and not isinstance(physical_cores, bool)
    )
    ram_fields_valid = all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and value > 0
        for value in (ram_total, ram_per_node)
    )

    if not integer_fields_valid or not ram_fields_valid:
        add(
            "HARDWARE_NUMERIC_FIELDS",
            "FAIL",
            "Node, physical-core and RAM target values have invalid types or values.",
        )
        consistent = False
    else:
        group_nodes = len(expected_map)
        group_cores = sum(expected_map.values())
        consistent = (
            compute_nodes == group_nodes == 16
            and physical_cores == group_cores == 664
            and math.isclose(
                float(ram_total),
                float(compute_nodes) * float(ram_per_node),
                rel_tol=0,
                abs_tol=0.001,
            )
            and math.isclose(float(ram_total), 4096.0, abs_tol=0.001)
            and math.isclose(float(ram_per_node), 256.0, abs_tol=0.001)
        )
        add(
            "HARDWARE_NUMERIC_FIELDS",
            "PASS",
            "Node, physical-core and RAM target fields have valid numeric values.",
        )

    add(
        "HARDWARE_TARGET_INTERNAL_CONSISTENCY",
        "PASS" if consistent else "FAIL",
        (
            f"{len(expected_map)} nodes / {sum(expected_map.values())} physical cores; "
            f"declared {compute_nodes} nodes / {physical_cores} cores; "
            f"RAM {ram_total} GiB total / {ram_per_node} GiB per node."
        ),
    )

    motherboard = hardware.get("motherboard")
    motherboard_contract_valid = (
        isinstance(motherboard, dict)
        and motherboard.get("collection_required") is True
        and motherboard.get("fields") == [
            "manufacturer",
            "model",
            "version",
        ]
        and motherboard.get("source") == "/sys/class/dmi/id/"
        and motherboard.get("missing_value") == "UNAVAILABLE"
    )

    add(
        "MOTHERBOARD_COLLECTION_CONTRACT",
        "PASS" if motherboard_contract_valid else "FAIL",
        (
            "Motherboard manufacturer, model and version are required from DMI sysfs."
            if motherboard_contract_valid
            else "Motherboard collection contract is missing or inconsistent."
        ),
    )

    worker_counts = benchmark.get("worker_counts")
    thresholds = benchmark.get("thresholds")

    benchmark_valid = (
        benchmark.get("workload") == "SpMV"
        and benchmark.get("parallelism_target") == 664
        and isinstance(worker_counts, list)
        and all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in worker_counts
        )
        and worker_counts == sorted(set(worker_counts))
        and 664 in worker_counts
        and isinstance(thresholds, list)
        and all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in thresholds
        )
        and thresholds == sorted(set(thresholds))
        and 10_000_000 in thresholds
        and benchmark.get("maximum_target_dimension") == 10_000_000
        and benchmark.get("minimum_warmup") == 5
        and benchmark.get("minimum_valid_measurements") == 30
        and benchmark.get("execution_status") == "NOT_EXECUTED"
    )

    add(
        "SPMV_BENCHMARK_PROPOSAL",
        "PASS" if benchmark_valid else "FAIL",
        (
            "SpMV proposal declares 664 workers, dimension 10,000,000, "
            "5 warm-ups and 30 valid measurements; execution remains NOT_EXECUTED."
            if benchmark_valid
            else "SpMV proposal does not match the declared HPC target contract."
        ),
    )

    statuses = {item["status"] for item in checks}
    overall = "FAIL" if "FAIL" in statuses else "PASS"

    return {
        "overall": overall,
        "checks": checks,
        "expected_cores_by_node": expected_map,
        "expected_nodes": compute_nodes,
        "expected_physical_cores": physical_cores,
        "expected_ram_gib_total": ram_total,
        "expected_ram_gib_per_node": ram_per_node,
        "motherboard_contract": motherboard,
        "benchmark_proposal": benchmark,
    }


def validate_inventory(
    nodes: list[dict[str, Any]],
    target_validation: dict[str, Any],
) -> dict[str, Any]:
    """Validate node records using the same fields as validate_hpc_results.py."""
    checks: list[dict[str, str]] = []

    def add(check_id: str, status: str, detail: str) -> None:
        checks.append({
            "id": check_id,
            "status": status,
            "detail": detail,
        })

    expected_map = target_validation.get("expected_cores_by_node", {})
    expected_count = target_validation.get("expected_nodes")
    expected_cores = target_validation.get("expected_physical_cores")
    expected_ram = target_validation.get("expected_ram_gib_total")
    expected_ram_per_node = target_validation.get("expected_ram_gib_per_node")

    if not nodes:
        add("INVENTORY_PRESENT", "DEFERRED",
            "No node inventories supplied; hardware target is not demonstrated.")
        add("MOTHERBOARD_INVENTORY", "DEFERRED",
            "No motherboard inventory is available.")
        return {"overall": "DEFERRED", "checks": checks}

    invalid_schema = [
        item for item in nodes
        if item.get("schema") != NODE_SCHEMA
    ]
    if invalid_schema:
        add(
            "NODE_INVENTORY_SCHEMA",
            "FAIL",
            f"{len(invalid_schema)} node record(s) have an unsupported schema.",
        )
        return {"overall": "FAIL", "checks": checks}

    hosts = [normalize_hostname(item.get("hostname")) for item in nodes]
    if any(host is None for host in hosts):
        add("NODE_HOSTNAMES", "FAIL",
            "Every node inventory must contain a non-empty hostname.")
        return {"overall": "FAIL", "checks": checks}

    duplicates = sorted({
        host for host in hosts if hosts.count(host) > 1
    })
    add(
        "DISTINCT_COMPUTE_NODES",
        "FAIL" if duplicates else "PASS",
        f"Duplicate hostnames: {duplicates}" if duplicates
        else f"{len(set(hosts))} distinct hostnames.",
    )

    observed_hosts = set(hosts)
    expected_hosts = set(expected_map)
    missing_hosts = sorted(expected_hosts - observed_hosts)
    unexpected_hosts = sorted(observed_hosts - expected_hosts)

    host_set_ok = (
        len(nodes) == expected_count
        and not missing_hosts
        and not unexpected_hosts
        and not duplicates
    )

    add(
        "COMPUTE_NODE_SET",
        "PASS" if host_set_ok else "DEFERRED",
        (
            f"Observed all {expected_count} configured compute nodes."
            if host_set_ok
            else f"Missing={missing_hosts}; unexpected={unexpected_hosts}; "
                 f"observed={len(observed_hosts)}; expected={expected_count}."
        ),
    )

    physical_total = 0
    physical_unknown: list[str] = []
    physical_mismatch: list[str] = []

    for item, hostname in zip(nodes, hosts):
        physical = item.get("physical_cores")
        if (
            not isinstance(physical, int)
            or isinstance(physical, bool)
            or physical <= 0
        ):
            physical_unknown.append(str(hostname))
            continue

        physical_total += physical
        expected = expected_map.get(hostname)
        if expected is not None and physical != expected:
            physical_mismatch.append(
                f"{hostname}: observed {physical}, expected {expected}"
            )

    if physical_mismatch:
        physical_status = "FAIL"
        physical_detail = "; ".join(physical_mismatch)
    elif physical_unknown or not host_set_ok:
        physical_status = "DEFERRED"
        physical_detail = (
            f"Physical cores observed={physical_total}; expected={expected_cores}; "
            f"unknown={physical_unknown}."
        )
    elif physical_total == expected_cores:
        physical_status = "PASS"
        physical_detail = f"Observed {physical_total} physical cores as declared."
    else:
        physical_status = "FAIL"
        physical_detail = (
            f"Observed {physical_total} physical cores; expected={expected_cores}."
        )

    add("PHYSICAL_CORE_TOPOLOGY", physical_status, physical_detail)

    ram_values = [item.get("memory_gib") for item in nodes]
    ram_unknown = [
        str(hostname)
        for hostname, value in zip(hosts, ram_values)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or value <= 0
        )
    ]

    if ram_unknown or not host_set_ok:
        ram_status = "DEFERRED"
        ram_detail = f"RAM unknown on {ram_unknown}; complete node set required."
    else:
        ram_observed = sum(float(value) for value in ram_values)
        if ram_observed >= 0.97 * float(expected_ram):
            ram_status = "PASS"
            ram_detail = (
                f"Observed {ram_observed:.2f} GiB; target {expected_ram} GiB "
                "(3% OS-visible memory tolerance)."
            )
        else:
            ram_status = "FAIL"
            ram_detail = (
                f"Observed {ram_observed:.2f} GiB; target {expected_ram} GiB."
            )

    add("TOTAL_RAM", ram_status, ram_detail)

    ram_per_node_failures: list[str] = []
    for item, hostname in zip(nodes, hosts):
        value = item.get("memory_gib")
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            and value > 0
            and float(value) < 0.97 * float(expected_ram_per_node)
        ):
            ram_per_node_failures.append(f"{hostname}: {float(value):.2f} GiB")

    if ram_per_node_failures:
        per_node_status = "FAIL"
        per_node_detail = (
            "Nodes below the 97% visible-memory threshold: "
            + "; ".join(ram_per_node_failures)
        )
    elif ram_unknown or not host_set_ok:
        per_node_status = "DEFERRED"
        per_node_detail = "Complete per-node RAM inventory is required."
    else:
        per_node_status = "PASS"
        per_node_detail = (
            f"All nodes meet the {expected_ram_per_node} GiB target within 3%."
        )

    add("RAM_PER_NODE", per_node_status, per_node_detail)

    motherboard_missing: list[str] = []
    for item, hostname in zip(nodes, hosts):
        board = item.get("motherboard")
        if not isinstance(board, dict):
            motherboard_missing.append(str(hostname))
            continue

        if any(
            not isinstance(board.get(field), str)
            or not board[field].strip()
            or board[field].strip().upper() == "UNAVAILABLE"
            for field in ("manufacturer", "model", "version")
        ):
            motherboard_missing.append(str(hostname))

    if motherboard_missing:
        motherboard_status = "DEFERRED"
        motherboard_detail = (
            "Motherboard manufacturer/model/version unavailable for: "
            + ", ".join(sorted(set(motherboard_missing)))
        )
    elif not host_set_ok:
        motherboard_status = "DEFERRED"
        motherboard_detail = "Complete configured node set is required."
    else:
        motherboard_status = "PASS"
        motherboard_detail = (
            "Manufacturer, model and version are present for every compute node."
        )

    add("MOTHERBOARD_INVENTORY", motherboard_status, motherboard_detail)

    effective_values = [usable_cores(item) for item in nodes]
    effective_unknown = [
        str(hostname)
        for hostname, value in zip(hosts, effective_values)
        if value is None
    ]

    if effective_unknown or not host_set_ok:
        effective_status = "DEFERRED"
        effective_detail = (
            f"Effective CPU capacity unknown for: {effective_unknown}"
        )
    else:
        effective_total = sum(
            float(value) for value in effective_values if value is not None
        )
        effective_status = (
            "PASS" if effective_total >= 664 else "DEFERRED"
        )
        effective_detail = (
            f"Known effective CPU capacity: {effective_total:g}; "
            "parallelism target: 664."
        )

    add("EFFECTIVE_CPU_CAPACITY", effective_status, effective_detail)

    statuses = {item["status"] for item in checks}
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "DEFERRED" in statuses:
        overall = "DEFERRED"
    else:
        overall = "PASS"

    return {
        "overall": overall,
        "checks": checks,
        "summary": {
            "node_count_observed": len(nodes),
            "physical_cores_observed": physical_total,
            "expected_node_count": expected_count,
            "expected_physical_cores": expected_cores,
            "motherboard_nodes_missing": sorted(set(motherboard_missing)),
        },
    }


def validate_target(
    target: dict[str, Any],
    nodes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate configuration and node inventory as one preflight report."""
    config_result = validate_configuration(target)

    if config_result["overall"] == "FAIL":
        inventory_result = {
            "overall": "NOT_EVALUATED",
            "checks": [{
                "id": "INVENTORY_VALIDATION",
                "status": "NOT_EVALUATED",
                "detail": "Configuration validation failed.",
            }],
        }
        overall = "FAIL"
    else:
        inventory_result = validate_inventory(nodes, config_result)
        if inventory_result["overall"] == "FAIL":
            overall = "FAIL"
        elif inventory_result["overall"] == "DEFERRED":
            overall = "DEFERRED"
        else:
            overall = "PASS"

    return {
        "schema": "qflpn-p3-hpc-preflight-validation-v2",
        "configuration_validation": config_result,
        "inventory_validation": inventory_result,
        "overall": overall,
        "execution_evidence": {
            "benchmark_execution_status": "NOT_EXECUTED",
            "664_worker_execution_demonstrated": False,
            "dimension_10000000_execution_demonstrated": False,
            "this_report_is_not_performance_evidence": True,
        },
    }


def load_node_inventory(path: str | Path) -> dict[str, Any]:
    """Load and validate one node inventory JSON file."""
    file_path = Path(path)
    try:
        value = json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing inventory file: {file_path}") from exc
    except OSError as exc:
        raise ValueError(f"Cannot read inventory file {file_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {file_path}: {exc}") from exc

    if not isinstance(value, dict):
        raise ValueError(f"Inventory must be a JSON object: {file_path}")
    if value.get("schema") != NODE_SCHEMA:
        raise ValueError(
            f"Unsupported node inventory schema in {file_path}: "
            f"{value.get('schema')!r}"
        )
    return value


def aggregate(
    nodes: list[dict[str, Any]],
    *,
    collected_utc: str | None = None,
) -> dict[str, Any]:
    """Create the canonical aggregate object consumed by the validator."""
    normalized_nodes: list[dict[str, Any]] = []

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(f"Node inventory at index {index} is not an object.")
        if node.get("schema") != NODE_SCHEMA:
            raise ValueError(
                f"Node inventory at index {index} has schema "
                f"{node.get('schema')!r}; expected {NODE_SCHEMA}."
            )
        normalized_nodes.append(node)

    hostnames = [
        normalize_hostname(node.get("hostname"))
        for node in normalized_nodes
    ]

    return {
        "schema": AGGREGATE_SCHEMA,
        "schema_version": "1.0.0",
        "collected_utc": collected_utc or utc_now(),
        "node_count": len(normalized_nodes),
        "distinct_hostname_count": len({
            hostname for hostname in hostnames if hostname is not None
        }),
        "nodes": normalized_nodes,
        "aggregation_scope": (
            "Inventory aggregation only; this document is not benchmark "
            "execution or performance evidence."
        ),
    }


def load_target(path: str | Path) -> dict[str, Any]:
    """Load the nested HPC target configuration."""
    file_path = Path(path)
    try:
        value = json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing target configuration: {file_path}") from exc
    except OSError as exc:
        raise ValueError(f"Cannot read target configuration {file_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid target JSON in {file_path}: {exc}") from exc

    if not isinstance(value, dict):
        raise ValueError("Target configuration root must be a JSON object.")
    return value


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    """Write JSON atomically to the requested path."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("collect", help="Collect this node's inventory.")

    aggregate_parser = subparsers.add_parser(
        "aggregate",
        help="Aggregate node inventory JSON files.",
    )
    aggregate_parser.add_argument("output", type=Path)
    aggregate_parser.add_argument("inventories", nargs="+")

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate target configuration and node inventories.",
    )
    validate_parser.add_argument("target", type=Path)
    validate_parser.add_argument("inventories", nargs="*")

    args = parser.parse_args(argv)

    try:
        if args.command == "collect":
            json.dump(collect(), sys.stdout, indent=2, ensure_ascii=False)
            print()
            return 0

        if args.command == "aggregate":
            nodes = [
                load_node_inventory(path)
                for path in args.inventories
            ]
            result = aggregate(nodes)
            write_json(args.output, result)
            print(f"HPC_AGGREGATE_SCHEMA={result['schema']}")
            print(f"HPC_AGGREGATE_NODES={result['node_count']}")
            print(f"HPC_AGGREGATE_OUTPUT={args.output}")
            return 0

        if args.command == "validate":
            target = load_target(args.target)
            nodes: list[dict[str, Any]] = []

            for path in args.inventories:
                loaded = json.loads(
                    Path(path).read_text(encoding="utf-8")
                )
                if not isinstance(loaded, dict):
                    raise ValueError(f"Inventory root must be an object: {path}")

                if loaded.get("schema") == NODE_SCHEMA:
                    nodes.append(loaded)
                elif loaded.get("schema") == AGGREGATE_SCHEMA:
                    aggregate_nodes = loaded.get("nodes")
                    if not isinstance(aggregate_nodes, list):
                        raise ValueError(
                            f"Aggregate inventory has no nodes array: {path}"
                        )
                    if not all(isinstance(item, dict) for item in aggregate_nodes):
                        raise ValueError(
                            f"Aggregate inventory contains a non-object node: {path}"
                        )
                    nodes.extend(aggregate_nodes)
                else:
                    raise ValueError(
                        f"Unsupported inventory schema in {path}: "
                        f"{loaded.get('schema')!r}"
                    )

            result = validate_target(target, nodes)
            json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
            print()
            return 0 if result["overall"] == "PASS" else 1

        parser.print_help()
        return 2

    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"HPC_INVENTORY_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
