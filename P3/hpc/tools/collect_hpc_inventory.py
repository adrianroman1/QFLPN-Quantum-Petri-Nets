#!/usr/bin/env python3
"""Collect a hardware inventory and validate the HPC target (stdlib only).

Two uses:

  collect   python collect_hpc_inventory.py collect  > node.json
            Run on every compute node (for example through srun). Records what
            the node and the job REALLY expose: logical CPUs, the CPU affinity
            mask, the cgroup CPU quota, physical cores/sockets from
            /proc/cpuinfo, memory, NUMA nodes, Slurm variables, JDK and MPI.

  validate  python collect_hpc_inventory.py validate hpc-664.json node1.json ...
            Merges node inventories and checks them against the target.

The target is demonstrated by inventories, never inferred from the number of
workers configured in an application. A single JVM with parallelism = 664 on
one node is NOT a distributed run; the validator reports it as such.

Verdicts: PASS only if every target quantity is met by distinct nodes;
DEFERRED when the inventories are insufficient or absent (never PASS);
FAIL when inventories contradict the target (for example duplicate hosts).
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "qflpn-p3-hpc-node-inventory-v1"


# ---------------------------------------------------------------------------
# parsing helpers (pure functions, testable without the hardware)
# ---------------------------------------------------------------------------

def parse_cpuinfo(text: str) -> dict[str, Any]:
    """Logical processors, physical cores and sockets from /proc/cpuinfo."""
    logical = 0
    pairs: set[tuple[str, str]] = set()
    sockets: set[str] = set()
    model = ""
    physical_id = core_id = None

    for line in text.splitlines() + [""]:
        if not line.strip():
            if physical_id is not None and core_id is not None:
                pairs.add((physical_id, core_id))
                sockets.add(physical_id)
            physical_id = core_id = None
            continue

        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()

        if key == "processor":
            logical += 1
        elif key == "physical id":
            physical_id = value
        elif key == "core id":
            core_id = value
        elif key == "model name" and not model:
            model = value

    return {
        "logical_processors": logical,
        "physical_cores": len(pairs) or None,
        "sockets": len(sockets) or None,
        "cpu_model": model or None,
    }


def parse_meminfo_gib(text: str) -> float | None:
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB", text, re.MULTILINE)
    return round(int(match.group(1)) / 1024 / 1024, 3) if match else None


def parse_cgroup_cpu_max(text: str) -> float | None:
    """CPU quota in cores from cgroup v2 'cpu.max' ('max 100000' = none)."""
    parts = text.split()
    if len(parts) != 2 or parts[0] == "max":
        return None
    try:
        return round(int(parts[0]) / int(parts[1]), 3)
    except (ValueError, ZeroDivisionError):
        return None


def read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def run_version(command: list[str]) -> str | None:
    if shutil.which(command[0]) is None:
        return None
    try:
        out = subprocess.run(command, capture_output=True, text=True,
                             timeout=20)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


# ---------------------------------------------------------------------------
# collection
# ---------------------------------------------------------------------------

def collect() -> dict[str, Any]:
    cpu = parse_cpuinfo(read_text("/proc/cpuinfo"))
    affinity = (len(os.sched_getaffinity(0))
                if hasattr(os, "sched_getaffinity") else None)
    numa = sorted(
        p.name for p in Path("/sys/devices/system/node").glob("node[0-9]*")
    ) if Path("/sys/devices/system/node").is_dir() else []

    slurm = {k: v for k, v in os.environ.items()
             if k.startswith("SLURM_") and k in {
                 "SLURM_JOB_ID", "SLURM_JOB_NODELIST", "SLURM_NNODES",
                 "SLURM_CPUS_ON_NODE", "SLURM_CPUS_PER_TASK",
                 "SLURM_NTASKS", "SLURM_NODEID", "SLURM_CPU_BIND"}}

    return {
        "schema": SCHEMA,
        "collected_utc": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "hostname": platform.node(),
        "os": platform.platform(),
        "kernel": platform.release(),
        "python": platform.python_version(),
        "cpu_model": cpu["cpu_model"],
        "sockets": cpu["sockets"],
        "physical_cores": cpu["physical_cores"],
        "logical_processors": cpu["logical_processors"] or os.cpu_count(),
        "cpu_affinity_count": affinity,
        "cgroup_cpu_quota_cores": parse_cgroup_cpu_max(
            read_text("/sys/fs/cgroup/cpu.max")),
        "memory_gib": parse_meminfo_gib(read_text("/proc/meminfo")),
        "numa_nodes": numa,
        "slurm": slurm,
        "java": run_version(["java", "-version"]),
        "maven": run_version(["mvn", "-version"]),
        "mpi": (run_version(["mpirun", "--version"])
                or run_version(["mpiexec", "--version"])),
    }


def usable_cores(node: dict[str, Any]) -> int | None:
    """Cores really available to the job: the minimum of every known limit."""
    limits = [v for v in (
        node.get("physical_cores"),
        node.get("cpu_affinity_count"),
        node.get("cgroup_cpu_quota_cores"),
    ) if isinstance(v, (int, float)) and v > 0]

    return int(min(limits)) if limits else None


# ---------------------------------------------------------------------------
# target validation
# ---------------------------------------------------------------------------

def validate_target(
    target: dict[str, Any], nodes: list[dict[str, Any]]
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def add(cid: str, status: str, detail: str) -> None:
        checks.append({"id": cid, "status": status, "detail": detail})

    # internal consistency of the declared target
    groups = target.get("node_groups", [])
    declared_cores = sum(g["nodes"] * g["physical_cores_per_node"]
                         for g in groups)
    declared_nodes = sum(g["nodes"] for g in groups)

    add("T0_TARGET_IS_INTERNALLY_CONSISTENT",
        "PASS" if (declared_cores == target["physical_cores_total"]
                   and declared_nodes == target["compute_nodes"]
                   and target["compute_nodes"] * target["ram_gib_per_node"]
                   == target["ram_gib_total"]) else "FAIL",
        f"groups give {declared_nodes} nodes / {declared_cores} cores; "
        f"target says {target['compute_nodes']} / "
        f"{target['physical_cores_total']}")

    if not nodes:
        add("T1_INVENTORIES_PRESENT", "DEFERRED",
            "no node inventory supplied; the target is not demonstrated")
        return finish(checks)

    add("T1_INVENTORIES_PRESENT", "PASS", f"{len(nodes)} inventory file(s)")

    hosts = [n.get("hostname") for n in nodes]
    duplicates = sorted({h for h in hosts if hosts.count(h) > 1})
    add("T2_DISTINCT_NODES",
        "FAIL" if duplicates else "PASS",
        f"duplicate hostnames: {duplicates}" if duplicates
        else f"{len(set(hosts))} distinct hosts")

    cores = [usable_cores(n) for n in nodes]
    unknown = [h for h, c in zip(hosts, cores) if c is None]

    if unknown:
        add("T3_CORES_KNOWN_FOR_EVERY_NODE", "DEFERRED",
            f"core count could not be determined on {unknown}")
    else:
        add("T3_CORES_KNOWN_FOR_EVERY_NODE", "PASS", "all nodes report cores")

    total_cores = sum(c for c in cores if c)
    needed_nodes = target["compute_nodes"]
    needed_cores = target["physical_cores_total"]

    add("T4_NODE_COUNT",
        "PASS" if len(set(hosts)) >= needed_nodes else "DEFERRED",
        f"{len(set(hosts))} of {needed_nodes} compute nodes")

    add("T5_CORE_COUNT",
        "PASS" if total_cores >= needed_cores and not unknown
        else "DEFERRED",
        f"{total_cores} usable cores of {needed_cores} "
        "(minimum of physical cores, affinity mask and cgroup quota)")

    ram = [n.get("memory_gib") for n in nodes]
    if any(r is None for r in ram):
        add("T6_RAM", "DEFERRED", "memory unknown on at least one node")
    else:
        total_ram = sum(ram)
        add("T6_RAM",
            "PASS" if total_ram >= 0.97 * target["ram_gib_total"]
            else "DEFERRED",
            f"{total_ram:.0f} GiB of {target['ram_gib_total']} GiB "
            "(OS-reserved memory makes the visible total slightly lower)")

    add("T7_MPI_PRESENT",
        "PASS" if all(n.get("mpi") for n in nodes) else "DEFERRED",
        "mpirun/mpiexec found on every node" if all(
            n.get("mpi") for n in nodes) else "MPI not found on every node")

    return finish(checks)


def finish(checks: list[dict[str, str]]) -> dict[str, Any]:
    statuses = {c["status"] for c in checks}

    if "FAIL" in statuses:
        overall = "FAIL"
    elif "DEFERRED" in statuses:
        overall = "DEFERRED"
    else:
        overall = "PASS"

    return {"overall": overall, "checks": checks}


def classify_run(
    nodes_used: int, workers: int, target: dict[str, Any]
) -> str:
    """Name what a run with this shape can demonstrate."""
    if nodes_used < 1 or workers < 1:
        raise ValueError("nodes_used and workers must be positive")

    if nodes_used == 1:
        return "INTRA_NODE_ONLY"

    if nodes_used < target["compute_nodes"]:
        return "PARTIAL_CLUSTER"

    return "FULL_CLUSTER"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    if args and args[0] == "collect":
        json.dump(collect(), sys.stdout, indent=2)
        print()
        return 0

    if len(args) >= 2 and args[0] == "validate":
        target = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        nodes = [json.loads(Path(p).read_text(encoding="utf-8"))
                 for p in args[2:]]
        result = validate_target(target, nodes)
        print(json.dumps(result, indent=2))
        return 0 if result["overall"] == "PASS" else 1

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
