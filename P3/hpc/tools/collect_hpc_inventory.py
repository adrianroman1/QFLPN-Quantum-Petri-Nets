#!/usr/bin/env python3
"""
Collect a reproducible, fail-closed hardware/software inventory for QFLPN P3.

This program observes the machine on which it runs. It does not assume that
the proposed 16-node / 664-core reference cluster exists.

Examples:
    python3 P3/hpc/tools/collect_hpc_inventory.py \
        --config P3/hpc/config/hpc-664.json \
        --output P3/results/hpc/inventory/node_inventory.json

    python3 P3/hpc/tools/collect_hpc_inventory.py \
        --config P3/hpc/config/hpc-664.json \
        --output node_inventory.json \
        --require-slurm

Exit codes:
    0: inventory collected; no mandatory local preflight failure
    2: invalid arguments or configuration
    3: inventory/preflight failure
    4: unexpected runtime failure

Only Python's standard library is used.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA = "qflpn-p3-hpc-inventory"
SCHEMA_VERSION = "1.0.0"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, UnicodeError):
        return None


def read_int(path: Path) -> int | None:
    value = read_text(path)
    if value is None:
        return None
    match = re.search(r"-?\d+", value)
    return int(match.group(0)) if match else None


def run_command(command: list[str], timeout: int = 5) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if executable is None:
        return {
            "available": False,
            "return_code": None,
            "stdout": "",
            "stderr": "",
        }

    try:
        result = subprocess.run(
            [executable, *command[1:]],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "available": True,
            "return_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "available": True,
            "return_code": None,
            "stdout": "",
            "stderr": str(exc),
        }


def parse_cpuinfo() -> dict[str, Any]:
    cpuinfo = read_text(Path("/proc/cpuinfo"))
    if not cpuinfo:
        return {
            "model_names": [],
            "logical_processors": None,
            "physical_core_ids": [],
            "socket_ids": [],
        }

    model_names: set[str] = set()
    physical_pairs: set[tuple[str, str]] = set()
    socket_ids: set[str] = set()
    logical_processors = 0

    for block in re.split(r"\n\s*\n", cpuinfo):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()

        if not fields:
            continue

        if "processor" in fields:
            logical_processors += 1

        model = fields.get("model name") or fields.get("Hardware")
        if model:
            model_names.add(model)

        physical_id = fields.get("physical id")
        core_id = fields.get("core id")
        if physical_id is not None:
            socket_ids.add(physical_id)
        if physical_id is not None and core_id is not None:
            physical_pairs.add((physical_id, core_id))

    return {
        "model_names": sorted(model_names),
        "logical_processors": logical_processors or None,
        "physical_core_ids": sorted(
            f"{socket}:{core}" for socket, core in physical_pairs
        ),
        "socket_ids": sorted(socket_ids),
    }


def parse_cpu_list(value: str | None) -> list[int] | None:
    """Parse Linux CPU-list syntax, for example '0-3,8,10-11'."""
    if not value:
        return None

    cpus: set[int] = set()
    try:
        for item in value.split(","):
            item = item.strip()
            if not item:
                continue
            if "-" in item:
                left, right = item.split("-", 1)
                start, end = int(left), int(right)
                if start < 0 or end < start:
                    return None
                cpus.update(range(start, end + 1))
            else:
                cpu = int(item)
                if cpu < 0:
                    return None
                cpus.add(cpu)
    except ValueError:
        return None

    return sorted(cpus)


def discover_affinity() -> dict[str, Any]:
    try:
        affinity = sorted(os.sched_getaffinity(0))
        return {
            "available": True,
            "cpu_ids": affinity,
            "cpu_count": len(affinity),
        }
    except (AttributeError, OSError):
        return {
            "available": False,
            "cpu_ids": None,
            "cpu_count": None,
        }


def discover_cgroup() -> dict[str, Any]:
    result: dict[str, Any] = {
        "version": "UNKNOWN",
        "cpu_quota_cores": None,
        "cpu_period_us": None,
        "cpu_max": None,
        "cpuset_cpus": None,
        "memory_limit_bytes": None,
        "memory_current_bytes": None,
    }

    cgroup_text = read_text(Path("/proc/self/cgroup")) or ""
    mount_text = read_text(Path("/proc/self/mountinfo")) or ""

    if re.search(r"(^|:)0::", cgroup_text):
        result["version"] = "V2"
        relative = ""
        for line in cgroup_text.splitlines():
            if line.startswith("0::"):
                relative = line.split("::", 1)[1].lstrip("/")
                break

        base = Path("/sys/fs/cgroup") / relative
        cpu_max = read_text(base / "cpu.max")
        if cpu_max:
            result["cpu_max"] = cpu_max
            parts = cpu_max.split()
            if len(parts) == 2 and parts[0] != "max":
                try:
                    quota = int(parts[0])
                    period = int(parts[1])
                    if quota > 0 and period > 0:
                        result["cpu_quota_cores"] = quota / period
                        result["cpu_period_us"] = period
                except ValueError:
                    pass

        result["cpuset_cpus"] = (
            read_text(base / "cpuset.cpus.effective")
            or read_text(base / "cpuset.cpus")
        )
        result["memory_limit_bytes"] = read_int(base / "memory.max")
        result["memory_current_bytes"] = read_int(base / "memory.current")

    else:
        result["version"] = "V1_OR_UNKNOWN"
        # Common cgroup-v1 mount points. Missing files remain explicitly unknown.
        candidates = [
            Path("/sys/fs/cgroup/cpu"),
            Path("/sys/fs/cgroup/cpu,cpuacct"),
        ]
        for base in candidates:
            quota = read_int(base / "cpu.cfs_quota_us")
            period = read_int(base / "cpu.cfs_period_us")
            if quota is not None and period and quota > 0 and period > 0:
                result["cpu_quota_cores"] = quota / period
                result["cpu_period_us"] = period
                break

        for base in candidates:
            cpuset = read_text(base / "cpuset.cpus")
            if cpuset:
                result["cpuset_cpus"] = cpuset
                break

        for base in (
            Path("/sys/fs/cgroup/memory"),
            Path("/sys/fs/cgroup"),
        ):
            limit = read_int(base / "memory.limit_in_bytes")
            current = read_int(base / "memory.usage_in_bytes")
            if limit is not None:
                # Very large sentinel values are treated as unlimited/unknown.
                if limit < (1 << 60):
                    result["memory_limit_bytes"] = limit
                result["memory_current_bytes"] = current
                break

    # Keep mount information as a diagnostic, not as a source of assumptions.
    result["cgroup_mount_detected"] = " - cgroup " in mount_text or " - cgroup2 " in mount_text
    return result


def discover_memory() -> dict[str, Any]:
    meminfo = read_text(Path("/proc/meminfo")) or ""
    values: dict[str, int] = {}

    for line in meminfo.splitlines():
        match = re.match(r"^([A-Za-z_()]+):\s+(\d+)\s+kB$", line)
        if match:
            values[match.group(1)] = int(match.group(2)) * 1024

    return {
        "total_bytes": values.get("MemTotal"),
        "available_bytes": values.get("MemAvailable"),
        "free_bytes": values.get("MemFree"),
        "total_gib": (
            round(values["MemTotal"] / (1024**3), 3)
            if "MemTotal" in values else None
        ),
        "available_gib": (
            round(values["MemAvailable"] / (1024**3), 3)
            if "MemAvailable" in values else None
        ),
    }


def discover_numa() -> dict[str, Any]:
    node_root = Path("/sys/devices/system/node")
    nodes: list[dict[str, Any]] = []

    if node_root.exists():
        for node_path in sorted(node_root.glob("node[0-9]*")):
            node_id = node_path.name.removeprefix("node")
            cpulist = read_text(node_path / "cpulist")
            meminfo = read_text(node_path / "meminfo")
            nodes.append({
                "node_id": node_id,
                "cpu_list": cpulist,
                "cpu_ids": parse_cpu_list(cpulist),
                "memory_info": meminfo,
            })

    return {
        "available": bool(nodes),
        "node_count": len(nodes) if nodes else None,
        "nodes": nodes,
    }


def discover_cache() -> list[dict[str, Any]]:
    root = Path("/sys/devices/system/cpu")
    caches: list[dict[str, Any]] = []

    for index in sorted(root.glob("cpu0/cache/index*")):
        caches.append({
            "level": read_text(index / "level"),
            "type": read_text(index / "type"),
            "size": read_text(index / "size"),
            "line_size_bytes": read_int(index / "coherency_line_size"),
            "shared_cpu_list": read_text(index / "shared_cpu_list"),
        })

    return caches


def discover_frequency() -> dict[str, Any]:
    root = Path("/sys/devices/system/cpu/cpu0/cpufreq")
    if not root.exists():
        return {
            "available": False,
            "scaling_governor": None,
            "scaling_min_khz": None,
            "scaling_max_khz": None,
            "cpuinfo_max_khz": None,
        }

    return {
        "available": True,
        "scaling_governor": read_text(root / "scaling_governor"),
        "scaling_min_khz": read_int(root / "scaling_min_freq"),
        "scaling_max_khz": read_int(root / "scaling_max_freq"),
        "cpuinfo_max_khz": read_int(root / "cpuinfo_max_freq"),
    }


def discover_slurm() -> dict[str, Any]:
    names = (
        "SLURM_JOB_ID",
        "SLURM_JOB_NAME",
        "SLURM_JOB_PARTITION",
        "SLURM_JOB_NODELIST",
        "SLURM_NNODES",
        "SLURM_NTASKS",
        "SLURM_CPUS_ON_NODE",
        "SLURM_CPUS_PER_TASK",
        "SLURM_MEM_PER_NODE",
        "SLURM_MEM_PER_CPU",
        "SLURM_JOB_ACCOUNT",
        "SLURM_CLUSTER_NAME",
        "SLURM_NODEID",
        "SLURM_PROCID",
        "SLURM_LOCALID",
    )
    env = {name: os.environ.get(name) for name in names}
    active = bool(env.get("SLURM_JOB_ID"))
    scontrol = run_command(["scontrol", "show", "job", str(env.get("SLURM_JOB_ID"))]) if active else {
        "available": False, "return_code": None, "stdout": "", "stderr": ""
    }
    return {
        "active": active,
        "environment": env,
        "scontrol_job_query": scontrol,
    }


def discover_software() -> dict[str, Any]:
    java = run_command(["java", "-version"])
    maven = run_command(["mvn", "-version"])
    mpi_commands = {
        name: run_command([name, "--version"])
        for name in ("mpirun", "mpiexec", "srun")
    }

    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "java": java,
        "maven": maven,
        "mpi_and_scheduler_commands": mpi_commands,
    }


def validate_reference(config: dict[str, Any], inventory: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    if config.get("schema") != "qflpn-p3-hpc-configuration":
        errors.append({
            "code": "CONFIG_SCHEMA_INVALID",
            "message": "Configurația nu are schema QFLPN P3 HPC așteptată.",
        })
        return errors

    hardware = config.get("hardware_reference", {})
    expected_cores = hardware.get("physical_cores_total")
    expected_nodes = hardware.get("compute_nodes")
    expected_memory = hardware.get("memory_per_node_gib")

    cpu = inventory["hardware"]["cpu"]
    affinity = inventory["hardware"]["cpu_affinity"]
    memory = inventory["hardware"]["memory"]
    slurm = inventory["scheduler"]["slurm"]

    # Local inventory cannot prove cluster-wide node count or total core count.
    inventory["reference_comparison"] = {
        "expected_cluster_nodes": expected_nodes,
        "expected_cluster_physical_cores": expected_cores,
        "observed_local_logical_processors": cpu.get("logical_processors"),
        "observed_local_physical_cores_from_cpuinfo": cpu.get("physical_core_count"),
        "observed_process_affinity_cpu_count": affinity.get("cpu_count"),
        "observed_local_memory_gib": memory.get("total_gib"),
        "cluster_wide_verification": "NOT_POSSIBLE_FROM_SINGLE_NODE_INVENTORY",
    }

    if inventory["host"]["operating_system"] != "Linux":
        errors.append({
            "code": "UNSUPPORTED_OPERATING_SYSTEM",
            "message": "Inventarul HPC de referință necesită Linux.",
        })

    if not isinstance(expected_nodes, int) or expected_nodes <= 0:
        errors.append({
            "code": "CONFIG_NODE_COUNT_INVALID",
            "message": "Numărul de noduri din configurație este invalid.",
        })

    if not isinstance(expected_cores, int) or expected_cores <= 0:
        errors.append({
            "code": "CONFIG_CORE_COUNT_INVALID",
            "message": "Numărul total de nuclee din configurație este invalid.",
        })

    if not isinstance(expected_memory, (int, float)) or expected_memory <= 0:
        errors.append({
            "code": "CONFIG_MEMORY_INVALID",
            "message": "Memoria de referință per nod este invalidă.",
        })

    if affinity.get("cpu_count") is None:
        errors.append({
            "code": "CPU_AFFINITY_UNKNOWN",
            "message": "Nu s-a putut determina CPU affinity a procesului.",
        })

    if memory.get("total_bytes") is None:
        errors.append({
            "code": "MEMORY_TOTAL_UNKNOWN",
            "message": "Nu s-a putut determina memoria RAM locală.",
        })

    if not slurm.get("active"):
        errors.append({
            "code": "SLURM_ALLOCATION_ABSENT",
            "message": "Nu există o alocare Slurm activă; preflight HPC nu poate fi acceptat.",
        })

    return errors


def collect(config_path: Path, require_slurm: bool) -> dict[str, Any]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Nu se poate citi configurația JSON: {exc}") from exc

    if not isinstance(config, dict):
        raise ValueError("Rădăcina configurației trebuie să fie un obiect JSON.")

    cpuinfo = parse_cpuinfo()
    physical_count = (
        len(cpuinfo["physical_core_ids"])
        if cpuinfo["physical_core_ids"] else None
    )

    inventory: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "collected_at_utc": utc_now(),
        "configuration": {
            "path": str(config_path),
            "configuration_id": config.get("configuration_id"),
            "configuration_status": config.get("configuration_status"),
        },
        "host": {
            "hostname": socket.gethostname(),
            "fqdn": socket.getfqdn(),
            "operating_system": platform.system(),
            "platform": platform.platform(),
            "kernel_release": platform.release(),
            "architecture": platform.machine(),
        },
        "hardware": {
            "cpu": {
                **cpuinfo,
                "physical_core_count": physical_count,
                "os_cpu_count": os.cpu_count(),
                "frequency": discover_frequency(),
                "cache": discover_cache(),
            },
            "cpu_affinity": discover_affinity(),
            "cgroup": discover_cgroup(),
            "memory": discover_memory(),
            "numa": discover_numa(),
        },
        "scheduler": {
            "slurm": discover_slurm(),
        },
        "software": discover_software(),
        "measurement_capabilities": {
            "dram_hardware_counters": "NOT_PROBED",
            "network_bandwidth": "NOT_MEASURED",
            "network_latency": "NOT_MEASURED",
            "storage_bandwidth": "NOT_MEASURED",
            "cpu_governor_observed": discover_frequency().get("scaling_governor"),
        },
        "limitations": [
            "Acest fișier descrie numai nodul pe care a rulat colectorul.",
            "Inventarul unui singur nod nu certifică topologia celor 16 noduri.",
            "Numărul de procesoare logice nu este echivalent cu numărul de nuclee fizice.",
            "Capacitatea RAM raportată de sistem poate fi diferită de memoria alocată jobului.",
            "Bandwidth-ul DRAM și al rețelei nu este măsurat de acest colector.",
        ],
    }

    errors = validate_reference(config, inventory)
    if require_slurm and not inventory["scheduler"]["slurm"]["active"]:
        if not any(item["code"] == "SLURM_ALLOCATION_ABSENT" for item in errors):
            errors.append({
                "code": "SLURM_REQUIRED_BUT_ABSENT",
                "message": "Opțiunea --require-slurm a fost solicitată, dar Slurm nu este activ.",
            })

    inventory["validation"] = {
        "status": "FAIL" if errors else "PASS_LOCAL_PREFLIGHT",
        "errors": errors,
        "cluster_acceptance": "NOT_EVALUATED",
        "note": (
            "PASS_LOCAL_PREFLIGHT nu înseamnă validarea clusterului complet "
            "și nu permite declararea P3_ACCEPTED."
        ),
    }
    return inventory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Calea către P3/hpc/config/hpc-664.json.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Fișierul JSON în care se salvează inventarul.",
    )
    parser.add_argument(
        "--require-slurm",
        action="store_true",
        help="Eșuează dacă procesul nu rulează într-o alocare Slurm.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        inventory = collect(args.config, args.require_slurm)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(
            json.dumps(inventory, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(args.output)

        print(f"INVENTORY_FILE={args.output}")
        print(f"INVENTORY_STATUS={inventory['validation']['status']}")
        print("CLUSTER_ACCEPTANCE=NOT_EVALUATED")

        return 0 if inventory["validation"]["status"] == "PASS_LOCAL_PREFLIGHT" else 3

    except ValueError as exc:
        print(f"CONFIGURATION_ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # Last-resort fail-closed boundary.
        print(f"INVENTORY_RUNTIME_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
