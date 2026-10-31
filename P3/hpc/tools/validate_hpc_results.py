#!/usr/bin/env python3
"""Fail-closed validation of the QFLPN P3 HPC target and node inventories.

This validator checks:
- the qflpn-p3-hpc-target-v2 configuration;
- the 16-node / 664-physical-core hardware target;
- the 8x42 + 8x41 core distribution;
- per-node RAM and motherboard inventory;
- the SpMV proposal, including 664 workers and dimension 10,000,000.

It does NOT validate measured benchmark CSV data and does NOT claim that
the proposed benchmark has been executed.

Inventory input may be:
- one node inventory JSON file per --inventory argument; or
- one aggregate JSON file containing a "nodes" array.

Exit codes:
    0: configuration valid; inventory is PASS or DEFERRED
    2: invalid input or invalid configuration
    3: inventory contradicts the declared target
    4: unexpected runtime failure

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

CONFIG_SCHEMA = "qflpn-p3-hpc-target-v2"
NODE_SCHEMA = "qflpn-p3-hpc-node-inventory-v1"
AGGREGATE_SCHEMA = "qflpn-p3-hpc-cluster-inventory-v1"
REPORT_SCHEMA = "qflpn-p3-hpc-target-validation-v1"

EXPECTED_WORKLOAD = "SpMV"
EXPECTED_PARALLELISM = 664
EXPECTED_MAX_DIMENSION = 10_000_000
EXPECTED_WARMUP = 5
EXPECTED_MEASUREMENTS = 30


class InputError(ValueError):
    """Raised when an input file cannot be interpreted safely."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputError(f"Missing {label}: {path}") from exc
    except OSError as exc:
        raise InputError(f"Cannot read {label} {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"Invalid JSON in {label} {path}: {exc}") from exc

    if not isinstance(value, dict):
        raise InputError(f"{label} must be a JSON object: {path}")
    return value


def add_check(
    checks: list[dict[str, str]],
    check_id: str,
    status: str,
    detail: str,
) -> None:
    checks.append({
        "id": check_id,
        "status": status,
        "detail": detail,
    })


def is_positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and value > 0
    )


def expected_node_core_map(hardware: dict[str, Any]) -> dict[str, int]:
    groups = hardware.get("node_groups")
    if not isinstance(groups, list) or not groups:
        raise InputError("hardware_target.node_groups must be a non-empty list")

    expected: dict[str, int] = {}
    for group in groups:
        if not isinstance(group, dict):
            raise InputError("Every node_groups entry must be an object")

        names = group.get("names")
        count = group.get("nodes")
        cores = group.get("physical_cores_per_node")

        if not isinstance(names, str):
            raise InputError("node_groups.names must be a string")
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise InputError("node_groups.nodes must be a positive integer")
        if not isinstance(cores, int) or isinstance(cores, bool) or cores <= 0:
            raise InputError(
                "node_groups.physical_cores_per_node must be a positive integer"
            )

        match = re.fullmatch(
            r"\s*([A-Za-z0-9_-]+)-(\d+)\.\.([A-Za-z0-9_-]+)-(\d+)\s*",
            names,
        )
        if not match or match.group(1).lower() != match.group(3).lower():
            raise InputError(
                f"Unsupported node group range {names!r}; "
                "expected a range such as HPC-01..HPC-08"
            )

        prefix = match.group(1)
        first = int(match.group(2))
        last = int(match.group(4))

        if last - first + 1 != count:
            raise InputError(
                f"Node range {names!r} contains {last - first + 1} "
                f"names but declares {count} nodes"
            )

        for number in range(first, last + 1):
            hostname = f"{prefix}-{number:02d}".lower()
            if hostname in expected:
                raise InputError(f"Duplicate node in target groups: {hostname}")
            expected[hostname] = cores

    return expected


def validate_configuration(
    config: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    checks: list[dict[str, str]] = []

    if config.get("schema") != CONFIG_SCHEMA:
        add_check(
            checks, "CONFIG_SCHEMA", "FAIL",
            f"Expected {CONFIG_SCHEMA}; got {config.get('schema')!r}",
        )
        return checks, {}

    if config.get("status") != "PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE":
        add_check(
            checks, "CONFIG_STATUS", "FAIL",
            "Configuration must remain explicitly marked as proposed, not evidence.",
        )
    else:
        add_check(
            checks, "CONFIG_STATUS", "PASS",
            "Configuration is explicitly marked as proposed reference configuration.",
        )

    hardware = config.get("hardware_target")
    benchmark = config.get("benchmark")

    if not isinstance(hardware, dict):
        add_check(checks, "HARDWARE_TARGET_OBJECT", "FAIL",
                  "hardware_target must be a JSON object")
        return checks, {}

    if not isinstance(benchmark, dict):
        add_check(checks, "BENCHMARK_OBJECT", "FAIL",
                  "benchmark must be a JSON object")
        return checks, {}

    try:
        expected_cores_by_node = expected_node_core_map(hardware)
    except InputError as exc:
        add_check(checks, "NODE_GROUPS", "FAIL", str(exc))
        expected_cores_by_node = {}

    nodes = hardware.get("compute_nodes")
    cores = hardware.get("physical_cores_total")
    ram_total = hardware.get("ram_gib_total")
    ram_per_node = hardware.get("ram_gib_per_node")

    numeric_hardware_valid = (
        isinstance(nodes, int) and not isinstance(nodes, bool)
        and isinstance(cores, int) and not isinstance(cores, bool)
        and is_positive_number(ram_total)
        and is_positive_number(ram_per_node)
    )

    if not numeric_hardware_valid:
        add_check(
            checks, "HARDWARE_NUMERIC_FIELDS", "FAIL",
            "Node, core and RAM target fields have invalid types or values.",
        )
    else:
        add_check(
            checks, "HARDWARE_NUMERIC_FIELDS", "PASS",
            "Node, core and RAM target fields are valid positive values.",
        )

    group_nodes = len(expected_cores_by_node)
    group_cores = sum(expected_cores_by_node.values())

    consistent = (
        numeric_hardware_valid
        and nodes == group_nodes == 16
        and cores == group_cores == 664
        and math.isclose(
            float(ram_total),
            float(nodes) * float(ram_per_node),
            rel_tol=0,
            abs_tol=0.001,
        )
        and math.isclose(float(ram_total), 4096.0, abs_tol=0.001)
        and math.isclose(float(ram_per_node), 256.0, abs_tol=0.001)
    )

    add_check(
        checks,
        "HARDWARE_TARGET_INTERNAL_CONSISTENCY",
        "PASS" if consistent else "FAIL",
        (
            f"{group_nodes} nodes / {group_cores} physical cores; "
            f"declared {nodes} nodes / {cores} cores; "
            f"RAM {ram_total} GiB total / {ram_per_node} GiB per node."
        ),
    )

    motherboard = hardware.get("motherboard")
    motherboard_valid = (
        isinstance(motherboard, dict)
        and motherboard.get("collection_required") is True
        and motherboard.get("fields") == ["manufacturer", "model", "version"]
        and motherboard.get("source") == "/sys/class/dmi/id/"
        and motherboard.get("missing_value") == "UNAVAILABLE"
    )

    add_check(
        checks,
        "MOTHERBOARD_COLLECTION_CONTRACT",
        "PASS" if motherboard_valid else "FAIL",
        (
            "Motherboard manufacturer, model and version are required "
            "from the DMI sysfs inventory."
            if motherboard_valid
            else "Motherboard collection contract is missing or inconsistent."
        ),
    )

    worker_counts = benchmark.get("worker_counts")
    thresholds = benchmark.get("thresholds")

    benchmark_valid = (
        benchmark.get("workload") == EXPECTED_WORKLOAD
        and benchmark.get("parallelism_target") == EXPECTED_PARALLELISM
        and isinstance(worker_counts, list)
        and all(isinstance(x, int) and not isinstance(x, bool) for x in worker_counts)
        and worker_counts == sorted(set(worker_counts))
        and EXPECTED_PARALLELISM in worker_counts
        and isinstance(thresholds, list)
        and all(isinstance(x, int) and not isinstance(x, bool) for x in thresholds)
        and thresholds == sorted(set(thresholds))
        and EXPECTED_MAX_DIMENSION in thresholds
        and benchmark.get("maximum_target_dimension") == EXPECTED_MAX_DIMENSION
        and benchmark.get("minimum_warmup") == EXPECTED_WARMUP
        and benchmark.get("minimum_valid_measurements") == EXPECTED_MEASUREMENTS
        and benchmark.get("execution_status") == "NOT_EXECUTED"
    )

    add_check(
        checks,
        "SPMV_BENCHMARK_PROPOSAL",
        "PASS" if benchmark_valid else "FAIL",
        (
            "SpMV proposal declares 664 workers, dimension 10,000,000, "
            "5 warm-ups and 30 valid measurements; execution remains NOT_EXECUTED."
            if benchmark_valid
            else "SpMV proposal does not match the required HPC target contract."
        ),
    )

    return checks, {
        "expected_cores_by_node": expected_cores_by_node,
        "expected_nodes": nodes,
        "expected_physical_cores": cores,
        "expected_ram_gib_total": ram_total,
        "expected_ram_gib_per_node": ram_per_node,
        "benchmark": benchmark,
        "motherboard": motherboard,
    }


def normalize_hostname(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().split(".", 1)[0].lower()


def usable_cores(node: dict[str, Any]) -> float | None:
    """Return the minimum known CPU capacity limit for the node."""
    limits: list[float] = []

    physical = node.get("physical_cores")
    affinity = node.get("cpu_affinity_count")
    quota = node.get("cgroup_cpu_quota_cores")

    for value in (physical, affinity, quota):
        if is_positive_number(value):
            limits.append(float(value))

    return min(limits) if limits else None


def load_inventory_files(paths: list[Path]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    for path in paths:
        value = load_json(path, "node inventory")

        if value.get("schema") == NODE_SCHEMA:
            nodes.append(value)
            continue

        if value.get("schema") == AGGREGATE_SCHEMA:
            aggregate_nodes = value.get("nodes")
            if not isinstance(aggregate_nodes, list):
                raise InputError(
                    f"Aggregate inventory {path} must contain a nodes array"
                )
            if not all(isinstance(item, dict) for item in aggregate_nodes):
                raise InputError(
                    f"Aggregate inventory {path} contains a non-object node"
                )
            nodes.extend(aggregate_nodes)
            continue

        raise InputError(
            f"Unsupported inventory schema in {path}: {value.get('schema')!r}"
        )

    return nodes


def validate_inventory(
    nodes: list[dict[str, Any]],
    target: dict[str, Any],
) -> tuple[str, list[dict[str, str]], dict[str, Any]]:
    checks: list[dict[str, str]] = []

    expected_map = target.get("expected_cores_by_node", {})
    expected_count = target.get("expected_nodes")
    expected_total_cores = target.get("expected_physical_cores")
    expected_ram = target.get("expected_ram_gib_total")
    expected_ram_per_node = target.get("expected_ram_gib_per_node")

    if not nodes:
        add_check(
            checks, "INVENTORY_PRESENT", "DEFERRED",
            "No node inventories were supplied; hardware targets are not demonstrated.",
        )
        add_check(
            checks, "MOTHERBOARD_INVENTORY", "DEFERRED",
            "No per-node motherboard information is available.",
        )
        return "DEFERRED", checks, {"node_count_observed": 0}

    invalid_schema = [
        n for n in nodes if n.get("schema") != NODE_SCHEMA
    ]
    if invalid_schema:
        add_check(
            checks, "NODE_INVENTORY_SCHEMA", "FAIL",
            f"{len(invalid_schema)} node inventory entries have an unsupported schema.",
        )
        return "FAIL", checks, {"node_count_observed": len(nodes)}

    hosts = [normalize_hostname(n.get("hostname")) for n in nodes]
    if any(host is None for host in hosts):
        add_check(
            checks, "NODE_HOSTNAMES", "FAIL",
            "Every node inventory must contain a non-empty hostname.",
        )
        return "FAIL", checks, {"node_count_observed": len(nodes)}

    duplicates = sorted({
        host for host in hosts if hosts.count(host) > 1
    })
    add_check(
        checks, "DISTINCT_COMPUTE_NODES",
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

    add_check(
        checks, "COMPUTE_NODE_SET",
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

    for node, hostname in zip(nodes, hosts):
        physical = node.get("physical_cores")
        if not isinstance(physical, int) or isinstance(physical, bool) or physical <= 0:
            physical_unknown.append(str(hostname))
            continue

        physical_total += physical
        expected = expected_map.get(hostname)
        if expected is not None and physical != expected:
            physical_mismatch.append(
                f"{hostname}: observed {physical}, expected {expected}"
            )

    if physical_mismatch:
        core_status = "FAIL"
        core_detail = "; ".join(physical_mismatch)
    elif physical_unknown or not host_set_ok:
        core_status = "DEFERRED"
        core_detail = (
            f"Physical cores observed={physical_total}; expected={expected_total_cores}; "
            f"unknown={physical_unknown}."
        )
    elif physical_total == expected_total_cores:
        core_status = "PASS"
        core_detail = f"Observed {physical_total} physical cores as declared."
    else:
        core_status = "FAIL"
        core_detail = (
            f"Observed {physical_total} physical cores; "
            f"expected {expected_total_cores}."
        )

    add_check(checks, "PHYSICAL_CORE_TOPOLOGY", core_status, core_detail)

    ram_values = [n.get("memory_gib") for n in nodes]
    ram_unknown = [
        str(host) for host, value in zip(hosts, ram_values)
        if not is_positive_number(value)
    ]

    if ram_unknown or not host_set_ok:
        ram_status = "DEFERRED"
        ram_detail = f"RAM unknown on {ram_unknown}; complete node set required."
    else:
        ram_total = sum(float(value) for value in ram_values)
        # Allow up to 3% OS-visible memory reduction.
        if ram_total >= 0.97 * float(expected_ram):
            ram_status = "PASS"
            ram_detail = (
                f"Observed {ram_total:.2f} GiB; target {expected_ram} GiB "
                "(3% OS-visible memory tolerance)."
            )
        else:
            ram_status = "FAIL"
            ram_detail = (
                f"Observed {ram_total:.2f} GiB; target {expected_ram} GiB."
            )

    add_check(checks, "TOTAL_RAM", ram_status, ram_detail)

    per_node_ram_mismatch: list[str] = []
    for node, hostname in zip(nodes, hosts):
        memory = node.get("memory_gib")
        if is_positive_number(memory) and (
            float(memory) < 0.97 * float(expected_ram_per_node)
        ):
            per_node_ram_mismatch.append(
                f"{hostname}: {float(memory):.2f} GiB"
            )

    if per_node_ram_mismatch:
        add_check(
            checks, "RAM_PER_NODE", "FAIL",
            "Nodes below the 97% visible-memory threshold: "
            + "; ".join(per_node_ram_mismatch),
        )
    elif ram_unknown or not host_set_ok:
        add_check(
            checks, "RAM_PER_NODE", "DEFERRED",
            "Per-node RAM cannot be fully evaluated without all node inventories.",
        )
    else:
        add_check(
            checks, "RAM_PER_NODE", "PASS",
            f"All nodes meet the visible-memory target of "
            f"{expected_ram_per_node} GiB within 3%.",
        )

    motherboard_missing: list[str] = []
    for node, hostname in zip(nodes, hosts):
        motherboard = node.get("motherboard")
        if not isinstance(motherboard, dict):
            motherboard_missing.append(str(hostname))
            continue

        for field in ("manufacturer", "model", "version"):
            value = motherboard.get(field)
            if (
                not isinstance(value, str)
                or not value.strip()
                or value.strip().upper() == "UNAVAILABLE"
            ):
                motherboard_missing.append(str(hostname))
                break

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

    add_check(
        checks, "MOTHERBOARD_INVENTORY",
        motherboard_status, motherboard_detail,
    )

    usable = [usable_cores(node) for node in nodes]
    usable_unknown = [
        str(host) for host, value in zip(hosts, usable) if value is None
    ]

    if usable_unknown or not host_set_ok:
        usable_status = "DEFERRED"
        usable_detail = f"Effective CPU capacity unknown for: {usable_unknown}"
    else:
        usable_total = sum(float(value) for value in usable if value is not None)
        usable_status = (
            "PASS" if usable_total >= EXPECTED_PARALLELISM else "DEFERRED"
        )
        usable_detail = (
            f"Known effective CPU capacity: {usable_total:g}; "
            f"parallelism target: {EXPECTED_PARALLELISM}."
        )

    add_check(checks, "EFFECTIVE_CPU_CAPACITY", usable_status, usable_detail)

    statuses = {check["status"] for check in checks}
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "DEFERRED" in statuses:
        overall = "DEFERRED"
    else:
        overall = "PASS"

    summary = {
        "node_count_observed": len(nodes),
        "physical_cores_observed": physical_total,
        "expected_node_count": expected_count,
        "expected_physical_cores": expected_total_cores,
        "motherboard_nodes_missing": sorted(set(motherboard_missing)),
    }
    return overall, checks, summary


def validate(
    config_path: Path,
    inventory_paths: list[Path],
) -> dict[str, Any]:
    config = load_json(config_path, "HPC target configuration")
    config_checks, target = validate_configuration(config)

    config_status = (
        "FAIL"
        if any(check["status"] == "FAIL" for check in config_checks)
        else "PASS"
    )

    nodes = load_inventory_files(inventory_paths) if inventory_paths else []
    if config_status == "PASS":
        inventory_status, inventory_checks, inventory_summary = validate_inventory(
            nodes, target
        )
    else:
        inventory_status = "NOT_EVALUATED"
        inventory_checks = [{
            "id": "INVENTORY_VALIDATION",
            "status": "NOT_EVALUATED",
            "detail": "Configuration validation failed; inventory was not evaluated.",
        }]
        inventory_summary = {"node_count_observed": len(nodes)}

    if config_status == "FAIL":
        overall = "FAIL"
    elif inventory_status == "FAIL":
        overall = "FAIL"
    elif inventory_status == "DEFERRED":
        overall = "DEFERRED"
    else:
        overall = "PASS"

    return {
        "schema": REPORT_SCHEMA,
        "schema_version": "1.0.0",
        "validated_at_utc": utc_now(),
        "configuration": {
            "path": str(config_path),
            "schema": config.get("schema"),
            "status": config.get("status"),
        },
        "configuration_validation": {
            "status": config_status,
            "checks": config_checks,
        },
        "inventory_validation": {
            "status": inventory_status,
            "checks": inventory_checks,
            "summary": inventory_summary,
            "input_files": [str(path) for path in inventory_paths],
        },
        "overall_status": overall,
        "execution_evidence": {
            "benchmark_execution_status": "NOT_EXECUTED",
            "664_worker_execution_demonstrated": False,
            "dimension_10000000_execution_demonstrated": False,
            "this_report_is_not_performance_evidence": True,
        },
        "acceptance_effect": (
            "NO_HPC_EXECUTION_CLAIM"
            if overall in {"PASS", "DEFERRED"}
            else "HPC_TARGET_VALIDATION_FAILED"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("P3/hpc/config/hpc-target.json"),
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        action="append",
        default=[],
        help="Node or aggregate inventory JSON; may be supplied more than once.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("P3/hpc/reports/hpc-target-validation.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        report = validate(args.config, args.inventory)
        args.output.parent.mkdir(parents=True, exist_ok=True)

        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(args.output)

        print(f"HPC_TARGET_VALIDATION_REPORT={args.output}")
        print(f"HPC_CONFIGURATION_STATUS={report['configuration_validation']['status']}")
        print(f"HPC_INVENTORY_STATUS={report['inventory_validation']['status']}")
        print(f"HPC_OVERALL_STATUS={report['overall_status']}")
        print("HPC_BENCHMARK_EXECUTION=NOT_EXECUTED")

        if report["overall_status"] == "FAIL":
            return 3
        return 0

    except InputError as exc:
        print(f"HPC_VALIDATION_INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            f"HPC_VALIDATION_RUNTIME_ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
