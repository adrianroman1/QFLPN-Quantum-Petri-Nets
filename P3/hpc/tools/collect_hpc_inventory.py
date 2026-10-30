#!/usr/bin/env python3
"""
QFLPN P3 — Hardware and software inventory.

Collects observed resources from the current Linux node and compares them
with P3/hpc/config/hpc-664.json.

Important:
- A single-node inventory never certifies a 16-node cluster.
- Proposed hardware values are targets, not observed facts.
- Slurm is mandatory only when --require-slurm is supplied.
- Unknown measurements remain null/UNKNOWN; they are never fabricated.

Exit codes:
    0: inventory successfully collected; local checks passed
    2: invalid configuration or arguments
    3: local preflight failed
    4: unexpected runtime failure
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
SCHEMA_VERSION = "1.1.0"
SUPPORTED_CONFIG_SCHEMAS = {
    "qflpn-p3-hpc-configuration",
    "qflpn-p3-hpc-configuration-v1",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()
    except OSError:
        return None


def read_int(path: Path) -> int | None:
    value = read_text(path)
    if value is None:
        return None

    match = re.fullmatch(r"\s*(\d+)\s*", value)
    return int(match.group(1)) if match else None


def run_command(
    command: list[str],
    timeout: int = 5,
) -> dict[str, Any]:
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

    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "return_code": None,
            "stdout": "",
            "stderr": f"COMMAND_TIMEOUT_AFTER_{timeout}_SECONDS",
        }

    except OSError as exc:
        return {
            "available": True,
            "return_code": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


def parse_cpuinfo() -> dict[str, Any]:
    cpuinfo = read_text(Path("/proc/cpuinfo"))

    if not cpuinfo:
        return {
            "model_names": [],
            "logical_processors": None,
            "physical_core_ids": [],
            "physical_core_count": None,
            "socket_ids": [],
            "socket_count": None,
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

    physical_ids = sorted(
        f"{socket}:{core}"
        for socket, core in physical_pairs
    )

    return {
        "model_names": sorted(model_names),
        "logical_processors": logical_processors or None,
        "physical_core_ids": physical_ids,
        "physical_core_count": len(physical_ids) if physical_ids else None,
        "socket_ids": sorted(socket_ids),
        "socket_count": len(socket_ids) if socket_ids else None,
    }


def parse_cpu_list(value: str | None) -> list[int] | None:
    """Parse Linux CPU-list syntax, e.g. 0-3,8,10-11."""
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
            "source": "os.sched_getaffinity",
        }

    except (AttributeError, OSError):
        return {
            "available": False,
            "cpu_ids": None,
            "cpu_count": None,
            "source": "UNAVAILABLE",
        }


def discover_cgroup() -> dict[str, Any]:
    result: dict[str, Any] = {
        "version": "UNKNOWN",
        "cpu_quota_cores": None,
        "cpu_period_us": None,
        "cpu_max": None,
        "cpuset_cpus": None,
        "cpuset_cpu_ids": None,
        "memory_limit_bytes": None,
        "memory_current_bytes": None,
        "cgroup_mount_detected": False,
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

        cpuset = (
            read_text(base / "cpuset.cpus.effective")
            or read_text(base / "cpuset.cpus")
        )

        result["cpuset_cpus"] = cpuset
        result["cpuset_cpu_ids"] = parse_cpu_list(cpuset)

        memory_max = read_text(base / "memory.max")

        if memory_max and memory_max != "max":
            try:
                result["memory_limit_bytes"] = int(memory_max)
            except ValueError:
                pass

        result["memory_current_bytes"] = read_int(
            base / "memory.current"
        )

    else:
        result["version"] = "V1_OR_UNKNOWN"

        cpu_candidates = [
            Path("/sys/fs/cgroup/cpu"),
            Path("/sys/fs/cgroup/cpu,cpuacct"),
        ]

        for base in cpu_candidates:
            quota = read_int(base / "cpu.cfs_quota_us")
            period = read_int(base / "cpu.cfs_period_us")

            if quota is not None and period and quota > 0 and period > 0:
                result["cpu_quota_cores"] = quota / period
                result["cpu_period_us"] = period
                break

        for base in cpu_candidates:
            cpuset = read_text(base / "cpuset.cpus")

            if cpuset:
                result["cpuset_cpus"] = cpuset
                result["cpuset_cpu_ids"] = parse_cpu_list(cpuset)
                break

        memory_candidates = [
            Path("/sys/fs/cgroup/memory"),
            Path("/sys/fs/cgroup"),
        ]

        for base in memory_candidates:
            limit = read_int(base / "memory.limit_in_bytes")
            current = read_int(base / "memory.usage_in_bytes")

            if limit is not None:
                # Large sentinel values represent unlimited/unknown.
                if limit < (1 << 60):
                    result["memory_limit_bytes"] = limit

                result["memory_current_bytes"] = current
                break

    result["cgroup_mount_detected"] = (
        " - cgroup " in mount_text
        or " - cgroup2 " in mount_text
    )

    return result


def discover_memory() -> dict[str, Any]:
    meminfo = read_text(Path("/proc/meminfo")) or ""
    values: dict[str, int] = {}

    for line in meminfo.splitlines():
        match = re.match(
            r"^([A-Za-z_()]+):\s+(\d+)\s+kB$",
            line,
        )

        if match:
            values[match.group(1)] = int(match.group(2)) * 1024

    total = values.get("MemTotal")
    available = values.get("MemAvailable")

    return {
        "total_bytes": total,
        "available_bytes": available,
        "free_bytes": values.get("MemFree"),
        "total_gib": round(total / (1024**3), 3) if total else None,
        "available_gib": (
            round(available / (1024**3), 3)
            if available else None
        ),
    }


def discover_numa() -> dict[str, Any]:
    node_root = Path("/sys/devices/system/node")
    nodes: list[dict[str, Any]] = []

    if node_root.exists():
        for node_path in sorted(node_root.glob("node[0-9]*")):
            node_id = node_path.name.removeprefix("node")
            cpulist = read_text(node_path / "cpulist")

            nodes.append({
                "node_id": node_id,
                "cpu_list": cpulist,
                "cpu_ids": parse_cpu_list(cpulist),
                "memory_info": read_text(node_path / "meminfo"),
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
            "line_size_bytes": read_int(
                index / "coherency_line_size"
            ),
            "shared_cpu_list": read_text(
                index / "shared_cpu_list"
            ),
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

    if active:
        scontrol = run_command([
            "scontrol",
            "show",
            "job",
            str(env["SLURM_JOB_ID"]),
        ])
    else:
        scontrol = {
            "available": False,
            "return_code": None,
            "stdout": "",
            "stderr": "",
        }

    return {
        "active": active,
        "environment": env,
        "scontrol_job_query": scontrol,
    }


def discover_software() -> dict[str, Any]:
    mpi_commands = {
        name: run_command([name, "--version"])
        for name in ("mpirun", "mpiexec", "mpicc", "srun")
    }

    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "java": run_command(["java", "-version"]),
        "maven": run_command(["mvn", "-version"]),
        "mpi_and_scheduler_commands": mpi_commands,
    }


def positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value > 0
    )


def read_reference_targets(
    config: dict[str, Any],
) -> tuple[int | None, int | None, float | None]:
    """
    Read both the current v1 schema and the earlier reference schema.
    Returns (node_count, total_physical_cores, memory_gib_per_node).
    """
    schema = config.get("schema")

    if schema not in SUPPORTED_CONFIG_SCHEMAS:
        raise ValueError(
            "CONFIG_SCHEMA_INVALID: "
            f"schema={schema!r}; supported={sorted(SUPPORTED_CONFIG_SCHEMAS)}"
        )

    if schema == "qflpn-p3-hpc-configuration-v1":
        cluster = config.get("cluster")
        if not isinstance(cluster, dict):
            raise ValueError("CONFIG_CLUSTER_INVALID")

        node_count = cluster.get("node_count")
        total_cores = cluster.get("physical_cores_target")

        memory_total = cluster.get("memory_gib_total")
        if not positive_number(memory_total) or not positive_number(node_count):
            memory_per_node = None
        else:
            memory_per_node = float(memory_total) / int(node_count)

        allocation = config.get("node_allocation")
        if isinstance(allocation, dict):
            groups = allocation.get("groups", [])

            if not isinstance(groups, list) or not groups:
                raise ValueError("CONFIG_NODE_ALLOCATION_GROUPS_INVALID")

            calculated_nodes = 0
            calculated_cores = 0
            calculated_memory = 0.0

            for group in groups:
                if not isinstance(group, dict):
                    raise ValueError("CONFIG_NODE_ALLOCATION_GROUP_INVALID")

                count = group.get("node_count")
                cores = group.get("physical_cores_per_node")
                memory = group.get("memory_gib_per_node")

                if (
                    not isinstance(count, int)
                    or isinstance(count, bool)
                    or count <= 0
                    or not isinstance(cores, int)
                    or isinstance(cores, bool)
                    or cores <= 0
                    or not positive_number(memory)
                ):
                    raise ValueError("CONFIG_NODE_ALLOCATION_VALUE_INVALID")

                calculated_nodes += count
                calculated_cores += count * cores
                calculated_memory += count * float(memory)

            if calculated_nodes != node_count:
                raise ValueError(
                    "CONFIG_NODE_COUNT_INCONSISTENT: "
                    f"cluster={node_count}, allocation={calculated_nodes}"
                )

            if calculated_cores != total_cores:
                raise ValueError(
                    "CONFIG_CORE_COUNT_INCONSISTENT: "
                    f"cluster={total_cores}, allocation={calculated_cores}"
                )

            if positive_number(memory_total):
                if abs(calculated_memory - float(memory_total)) > 1e-6:
                    raise ValueError("CONFIG_MEMORY_TOTAL_INCONSISTENT")

        if not isinstance(node_count, int) or node_count <= 0:
            raise ValueError("CONFIG_NODE_COUNT_INVALID")

        if not isinstance(total_cores, int) or total_cores <= 0:
            raise ValueError("CONFIG_CORE_COUNT_INVALID")

        if memory_per_node is None:
            raise ValueError("CONFIG_MEMORY_PER_NODE_INVALID")

        return node_count, total_cores, memory_per_node

    hardware = config.get("hardware_reference", {})

    if not isinstance(hardware, dict):
        raise ValueError("CONFIG_HARDWARE_REFERENCE_INVALID")

    return (
        hardware.get("compute_nodes"),
        hardware.get("physical_cores_total"),
        hardware.get("memory_per_node_gib"),
    )


def validate_reference(
    config: dict[str, Any],
    inventory: dict[str, Any],
    require_slurm: bool,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    try:
        expected_nodes, expected_cores, expected_memory = (
            read_reference_targets(config)
        )
    except ValueError as exc:
        return [{
            "code": "CONFIGURATION_INVALID",
            "message": str(exc),
        }]

    cpu = inventory["hardware"]["cpu"]
    affinity = inventory["hardware"]["cpu_affinity"]
    memory = inventory["hardware"]["memory"]
    cgroup = inventory["hardware"]["cgroup"]
    slurm = inventory["scheduler"]["slurm"]

    observed_physical = cpu.get("physical_core_count")
    observed_affinity = affinity.get("cpu_count")
    observed_memory = memory.get("total_gib")

    local_expected_cores = None
    local_expected_memory = expected_memory

    allocation = config.get("node_allocation", {})
    groups = allocation.get("groups", []) if isinstance(allocation, dict) else []

    if groups:
        slurm_node_id = os.environ.get("SLURM_NODEID")

        # The allocation is heterogeneous: a node can have 41 or 42 cores.
        allowed_cores = sorted({
            group["physical_cores_per_node"]
            for group in groups
            if isinstance(group, dict)
            and isinstance(group.get("physical_cores_per_node"), int)
        })

        inventory["reference_comparison"] = {
            "expected_cluster_nodes": expected_nodes,
            "expected_cluster_physical_cores": expected_cores,
            "expected_local_physical_cores_options": allowed_cores,
            "expected_local_memory_gib": local_expected_memory,
            "observed_local_physical_cores": observed_physical,
            "observed_local_logical_processors": cpu.get(
                "logical_processors"
            ),
            "observed_process_affinity_cpu_count": observed_affinity,
            "observed_local_memory_gib": observed_memory,
            "slurm_node_id": slurm_node_id,
            "cluster_wide_verification": (
                "NOT_POSSIBLE_FROM_SINGLE_NODE_INVENTORY"
            ),
        }

        if observed_physical is not None and allowed_cores:
            if observed_physical not in allowed_cores:
                errors.append({
                    "code": "LOCAL_PHYSICAL_CORE_TARGET_MISMATCH",
                    "message": (
                        f"Nodul are {observed_physical} nuclee fizice; "
                        f"configurația admite {allowed_cores}."
                    ),
                })

    else:
        inventory["reference_comparison"] = {
            "expected_cluster_nodes": expected_nodes,
            "expected_cluster_physical_cores": expected_cores,
            "expected_local_memory_gib": local_expected_memory,
            "observed_local_physical_cores": observed_physical,
            "observed_local_logical_processors": cpu.get(
                "logical_processors"
            ),
            "observed_process_affinity_cpu_count": observed_affinity,
            "observed_local_memory_gib": observed_memory,
            "cluster_wide_verification": (
                "NOT_POSSIBLE_FROM_SINGLE_NODE_INVENTORY"
            ),
        }

    if inventory["host"]["operating_system"] != "Linux":
        errors.append({
            "code": "UNSUPPORTED_OPERATING_SYSTEM",
            "message": "Inventarul HPC de referință necesită Linux.",
        })

    if observed_affinity is None or observed_affinity <= 0:
        errors.append({
            "code": "CPU_AFFINITY_UNKNOWN",
            "message": "CPU affinity nu a putut fi determinată.",
        })

    if memory.get("total_bytes") is None:
        errors.append({
            "code": "MEMORY_TOTAL_UNKNOWN",
            "message": "Memoria RAM locală nu a putut fi determinată.",
        })

    if (
        positive_number(local_expected_memory)
        and positive_number(observed_memory)
        and float(observed_memory) < float(local_expected_memory) * 0.95
    ):
        errors.append({
            "code": "LOCAL_MEMORY_TARGET_MISMATCH",
            "message": (
                f"Memorie locală observată {observed_memory} GiB; "
                f"ținta per nod este {local_expected_memory} GiB."
            ),
        })

    memory_limit = cgroup.get("memory_limit_bytes")
    if memory_limit is not None and memory.get("total_bytes"):
        if memory_limit < memory["total_bytes"] * 0.80:
            inventory["resource_warnings"] = [{
                "code": "CGROUP_MEMORY_LIMIT_BELOW_HOST_RAM",
                "message": (
                    "Limita cgroup este semnificativ sub memoria RAM "
                    "a gazdei; experimentele trebuie dimensionate după "
                    "limita efectivă a procesului."
                ),
            }]

    if require_slurm and not slurm.get("active"):
        errors.append({
            "code": "SLURM_ALLOCATION_ABSENT",
            "message": (
                "--require-slurm a fost solicitat, dar nu există "
                "o alocare Slurm activă."
            ),
        })

    if slurm.get("active"):
        slurm_nodes = slurm["environment"].get("SLURM_NNODES")

        if slurm_nodes:
            try:
                observed_nodes = int(slurm_nodes)
            except ValueError:
                errors.append({
                    "code": "SLURM_NODE_COUNT_INVALID",
                    "message": "SLURM_NNODES nu este numeric.",
                })
            else:
                if observed_nodes > expected_nodes:
                    errors.append({
                        "code": "SLURM_NODE_COUNT_EXCEEDS_REFERENCE",
                        "message": (
                            f"Alocarea Slurm are {observed_nodes} noduri, "
                            f"peste ținta de {expected_nodes}."
                        ),
                    })

    inventory["reference_comparison"]["expected_cluster_physical_cores"] = (
        expected_cores
    )

    return errors


def collect(
    config_path: Path,
    require_slurm: bool = False,
) -> dict[str, Any]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"Nu se poate citi configurația JSON: {exc}"
        ) from exc

    if not isinstance(config, dict):
        raise ValueError("Rădăcina configurației trebuie să fie obiect JSON.")

    expected_nodes, expected_cores, expected_memory = (
        read_reference_targets(config)
    )

    cpuinfo = parse_cpuinfo()
    frequency = discover_frequency()

    inventory: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "collected_at_utc": utc_now(),
        "configuration": {
            "path": str(config_path),
            "schema": config.get("schema"),
            "configuration_id": config.get("configuration_id"),
            "status": config.get(
                "status",
                config.get("configuration_status"),
            ),
            "acceptance_gate": config.get("acceptance_gate"),
            "expected_cluster_nodes": expected_nodes,
            "expected_cluster_physical_cores": expected_cores,
            "expected_memory_gib_per_node": expected_memory,
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
                "os_cpu_count": os.cpu_count(),
                "frequency": frequency,
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
            "cpu_governor_observed": frequency.get(
                "scaling_governor"
            ),
        },
        "limitations": [
            "Inventarul descrie numai nodul curent.",
            "Inventarul unui singur nod nu certifică toate cele 16 noduri.",
            "Nucleele fizice, procesoarele logice și CPU affinity sunt "
            "mărimi distincte.",
            "Memoria gazdei nu este neapărat memoria disponibilă jobului.",
            "Limitele cgroup pot restrânge memoria și CPU disponibile.",
            "Bandwidth-ul DRAM și al rețelei nu este măsurat de acest colector.",
            "Statusul PASS_LOCAL_PREFLIGHT nu certifică un cluster HPC.",
        ],
    }

    errors = validate_reference(
        config,
        inventory,
        require_slurm=require_slurm,
    )

    inventory["validation"] = {
        "status": "FAIL" if errors else "PASS_LOCAL_PREFLIGHT",
        "errors": errors,
        "cluster_acceptance": "NOT_EVALUATED",
        "acceptance_gate": "p3_validation",
        "note": (
            "Inventarul local nu permite declararea P3_ACCEPTED. "
            "Validarea clusterului necesită inventar separat pe fiecare "
            "nod și proveniență comună a campaniei."
        ),
    }

    return inventory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Configurația HPC JSON.",
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Calea fișierului JSON de inventar.",
    )

    parser.add_argument(
        "--require-slurm",
        action="store_true",
        help="Eșuează dacă nu există alocare Slurm activă.",
    )

    return parser.parse_args()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise ValueError(f"Refuz scrierea peste o cale symlink: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_name(path.name + ".tmp")

    if temporary.exists() and temporary.is_symlink():
        raise ValueError(f"Fișier temporar symlink nesigur: {temporary}")

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


def main() -> int:
    args = parse_args()

    try:
        inventory = collect(
            args.config,
            require_slurm=args.require_slurm,
        )

        write_json_atomic(args.output, inventory)

        status = inventory["validation"]["status"]

        print(f"INVENTORY_FILE={args.output}")
        print(f"INVENTORY_STATUS={status}")
        print("CLUSTER_ACCEPTANCE=NOT_EVALUATED")
        print("ACCEPTANCE_GATE=p3_validation")

        if status != "PASS_LOCAL_PREFLIGHT":
            for error in inventory["validation"]["errors"]:
                print(
                    f"INVENTORY_ERROR[{error['code']}]: "
                    f"{error['message']}",
                    file=sys.stderr,
                )
            return 3

        return 0

    except ValueError as exc:
        print(f"CONFIGURATION_ERROR: {exc}", file=sys.stderr)
        return 2

    except OSError as exc:
        print(
            f"INVENTORY_IO_ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 4

    except Exception as exc:
        print(
            f"INVENTORY_RUNTIME_ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
