#!/usr/bin/env bash
#SBATCH --job-name=p3-hpc-preflight
#SBATCH --nodes=16
#SBATCH --ntasks=664
#SBATCH --hint=nomultithread
#SBATCH --time=00:20:00
#SBATCH --output=p3-hpc-preflight-%j.out
#SBATCH --error=p3-hpc-preflight-%j.err

# QFLPN P3 — HPC reference-cluster preflight.
#
# This script verifies the proposed 16-node / 664-physical-core topology.
# It does NOT run the SpMV benchmark and does NOT declare P3_ACCEPTED.
#
# Submit from the repository root:
#   sbatch P3/hpc/slurm/p3-hpc-preflight.sbatch
#
# Optional output directory:
#   sbatch --export=ALL,P3_HPC_OUTPUT_DIR=/shared/p3/preflight \
#     P3/hpc/slurm/p3-hpc-preflight.sbatch
#
# Requirements:
#   - Slurm allocation with 16 nodes and 664 tasks.
#   - Linux compute nodes.
#   - Python 3 on every compute node.
#   - Shared filesystem visible from all allocated nodes.
#   - P3/hpc/config/hpc-664.json present in the repository.
#   - P3/hpc/tools/collect_hpc_inventory.py present in the repository.
#
# Exit codes:
#   0: preflight passed; cluster benchmark remains NOT_EVALUATED.
#   2: missing command, file, or invalid configuration.
#   3: Slurm allocation or node inventory validation failed.
#   4: unexpected runtime failure.

set -Eeuo pipefail
IFS=$'\n\t'

readonly EXPECTED_NODES=16
readonly EXPECTED_TASKS=664

log() {
    printf '[P3-HPC-PREFLIGHT] %s\n' "$*"
}

fail() {
    local message="$1"
    local code="${2:-3}"
    log "FAIL: ${message}"
    exit "$code"
}

on_error() {
    local exit_code=$?
    local line="${1:-unknown}"
    log "UNEXPECTED_ERROR: line=${line}, exit_code=${exit_code}"
    exit 4
}
trap 'on_error "$LINENO"' ERR

require_command() {
    local command_name="$1"
    command -v "$command_name" >/dev/null 2>&1 \
        || fail "Comanda obligatorie lipsește: ${command_name}" 2
}

require_file() {
    local file_path="$1"
    [[ -f "$file_path" ]] \
        || fail "Fișier obligatoriu absent: ${file_path}" 2
}

require_command python3
require_command srun
require_command scontrol

[[ -n "${SLURM_JOB_ID:-}" ]] \
    || fail "Scriptul nu rulează într-o alocare Slurm activă." 3

[[ -n "${SLURM_JOB_NODELIST:-}" ]] \
    || fail "SLURM_JOB_NODELIST nu este definit." 3

[[ -n "${SLURM_NNODES:-}" ]] \
    || fail "SLURM_NNODES nu este definit." 3

[[ -n "${SLURM_NTASKS:-}" ]] \
    || fail "SLURM_NTASKS nu este definit." 3

readonly REPOSITORY_ROOT="${SLURM_SUBMIT_DIR:-$PWD}"
readonly CONFIG="${REPOSITORY_ROOT}/P3/hpc/config/hpc-664.json"
readonly COLLECTOR="${REPOSITORY_ROOT}/P3/hpc/tools/collect_hpc_inventory.py"

require_file "$CONFIG"
require_file "$COLLECTOR"

readonly OUTPUT_DIR="${P3_HPC_OUTPUT_DIR:-${REPOSITORY_ROOT}/P3/results/hpc/preflight-${SLURM_JOB_ID}}"

mkdir -p "$OUTPUT_DIR"
[[ -d "$OUTPUT_DIR" && -w "$OUTPUT_DIR" ]] \
    || fail "Directorul de rezultate nu este accesibil pentru scriere: ${OUTPUT_DIR}" 2

log "Repository: ${REPOSITORY_ROOT}"
log "Slurm job: ${SLURM_JOB_ID}"
log "Node list: ${SLURM_JOB_NODELIST}"
log "Allocated nodes: ${SLURM_NNODES}"
log "Allocated tasks: ${SLURM_NTASKS}"
log "Output: ${OUTPUT_DIR}"

# Verify the requested reference configuration.
python3 - "$CONFIG" "$EXPECTED_NODES" "$EXPECTED_TASKS" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
expected_nodes = int(sys.argv[2])
expected_tasks = int(sys.argv[3])

try:
    config = json.loads(config_path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"CONFIGURATION_ERROR: {exc}", file=sys.stderr)
    raise SystemExit(2)

if config.get("schema") != "qflpn-p3-hpc-configuration":
    print("CONFIGURATION_ERROR: schema invalidă.", file=sys.stderr)
    raise SystemExit(2)

hardware = config.get("hardware_reference", {})
if hardware.get("compute_nodes") != expected_nodes:
    print("CONFIGURATION_ERROR: compute_nodes diferă de configurația preflight.",
          file=sys.stderr)
    raise SystemExit(2)

if hardware.get("physical_cores_total") != expected_tasks:
    print("CONFIGURATION_ERROR: physical_cores_total diferă de configurația preflight.",
          file=sys.stderr)
    raise SystemExit(2)

groups = hardware.get("node_groups", [])
observed = {}
for group in groups:
    count = group.get("node_count")
    cores = group.get("physical_cores_per_node")
    if not isinstance(count, int) or count <= 0:
        print("CONFIGURATION_ERROR: node_count invalid.", file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(cores, int) or cores <= 0:
        print("CONFIGURATION_ERROR: physical_cores_per_node invalid.",
              file=sys.stderr)
        raise SystemExit(2)
    observed[cores] = observed.get(cores, 0) + count

if observed != {41: 8, 42: 8}:
    print(
        "CONFIGURATION_ERROR: distribuția de referință trebuie să fie "
        "8 noduri × 41 nuclee și 8 noduri × 42 nuclee.",
        file=sys.stderr,
    )
    raise SystemExit(2)

if sum(cores * count for cores, count in observed.items()) != expected_tasks:
    print("CONFIGURATION_ERROR: suma nucleelor nu este 664.",
          file=sys.stderr)
    raise SystemExit(2)

print("CONFIGURATION_STATUS=VALID")
print("REFERENCE_NODES=16")
print("REFERENCE_PHYSICAL_CORES=664")
PY

# Verify that Slurm granted the requested node and task counts.
if [[ "$SLURM_NNODES" -ne "$EXPECTED_NODES" ]]; then
    fail "Alocarea are ${SLURM_NNODES} noduri; sunt necesare ${EXPECTED_NODES}." 3
fi

if [[ "$SLURM_NTASKS" -ne "$EXPECTED_TASKS" ]]; then
    fail "Alocarea are ${SLURM_NTASKS} task-uri; sunt necesare ${EXPECTED_TASKS}." 3
fi

# Record the scheduler's view of the allocation.
scontrol show job "$SLURM_JOB_ID" \
    > "${OUTPUT_DIR}/slurm-job-${SLURM_JOB_ID}.txt" \
    || fail "Nu s-a putut interoga jobul Slurm." 3

scontrol show hostnames "$SLURM_JOB_NODELIST" \
    > "${OUTPUT_DIR}/allocated-hosts.txt" \
    || fail "Nu s-a putut determina lista nodurilor alocate." 3

HOST_COUNT="$(python3 - "${OUTPUT_DIR}/allocated-hosts.txt" <<'PY'
import sys
from pathlib import Path

hosts = [
    line.strip()
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    if line.strip()
]
print(len(set(hosts)))
PY
)"

if [[ "$HOST_COUNT" -ne "$EXPECTED_NODES" ]]; then
    fail "Lista Slurm conține ${HOST_COUNT} noduri unice; sunt necesare ${EXPECTED_NODES}." 3
fi

# Export paths to every task. One inventory process is launched per node.
export P3_HPC_CONFIG="$CONFIG"
export P3_HPC_COLLECTOR="$COLLECTOR"
export P3_HPC_OUTPUT_DIR="$OUTPUT_DIR"

log "Colectare inventar pe fiecare nod..."

srun \
    --nodes="$EXPECTED_NODES" \
    --ntasks="$EXPECTED_NODES" \
    --ntasks-per-node=1 \
    --overlap \
    --cpu-bind=none \
    --kill-on-bad-exit=1 \
    --export=ALL \
    bash -c '
        set -Eeuo pipefail

        [[ -n "${SLURM_PROCID:-}" ]] || {
            echo "SLURM_PROCID absent" >&2
            exit 3
        }

        output="${P3_HPC_OUTPUT_DIR}/node-${SLURM_PROCID}.json"

        python3 "$P3_HPC_COLLECTOR" \
            --config "$P3_HPC_CONFIG" \
            --output "$output" \
            --require-slurm
    ' \
    || fail "Colectarea inventarului a eșuat pe cel puțin un nod." 3

# Validate all node inventories and write one deterministic summary.
python3 - \
    "$CONFIG" \
    "$OUTPUT_DIR" \
    "$EXPECTED_NODES" \
    "$EXPECTED_TASKS" \
    "$SLURM_JOB_ID" <<'PY'
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

config_path = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
expected_nodes = int(sys.argv[3])
expected_tasks = int(sys.argv[4])
job_id = str(sys.argv[5])

def fail(message: str) -> None:
    print(f"PREFLIGHT_VALIDATION_FAILED: {message}", file=sys.stderr)
    raise SystemExit(3)

try:
    config = json.loads(config_path.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"Nu se poate reciti configurația: {exc}")

files = sorted(output_dir.glob("node-*.json"))

if len(files) != expected_nodes:
    fail(
        f"Număr incorect de inventare: {len(files)}; "
        f"necesar: {expected_nodes}."
    )

inventories = []
for path in files:
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"JSON invalid în {path.name}: {exc}")

    if item.get("schema") != "qflpn-p3-hpc-inventory":
        fail(f"Schema inventarului este invalidă în {path.name}.")

    validation = item.get("validation", {})
    if validation.get("status") != "PASS_LOCAL_PREFLIGHT":
        fail(f"Preflight local nereușit în {path.name}.")

    if validation.get("errors"):
        fail(f"Inventarul {path.name} conține erori.")

    if validation.get("cluster_acceptance") != "NOT_EVALUATED":
        fail(
            f"{path.name}: inventarul local nu trebuie să declare "
            "acceptarea clusterului."
        )

    slurm = item.get("scheduler", {}).get("slurm", {})
    if not slurm.get("active"):
        fail(f"{path.name}: procesul nu confirmă o alocare Slurm activă.")

    observed_job = (
        slurm.get("environment", {}).get("SLURM_JOB_ID")
    )
    if str(observed_job) != job_id:
        fail(
            f"{path.name}: SLURM_JOB_ID diferit "
            f"({observed_job!r} față de {job_id!r})."
        )

    cpu = item.get("hardware", {}).get("cpu", {})
    physical_cores = cpu.get("physical_core_count")
    if not isinstance(physical_cores, int) or physical_cores <= 0:
        fail(f"{path.name}: numărul de nuclee fizice nu este determinat.")

    hostname = item.get("host", {}).get("hostname")
    if not hostname:
        fail(f"{path.name}: hostname absent.")

    inventories.append({
        "file": path.name,
        "hostname": hostname,
        "physical_cores": physical_cores,
        "logical_processors": cpu.get("logical_processors"),
        "memory_total_bytes": (
            item.get("hardware", {}).get("memory", {}).get("total_bytes")
        ),
        "cpu_affinity_count": (
            item.get("hardware", {})
                .get("cpu_affinity", {})
                .get("cpu_count")
        ),
        "numa_node_count": (
            item.get("hardware", {})
                .get("numa", {})
                .get("node_count")
        ),
    })

hostnames = [item["hostname"] for item in inventories]
if len(set(hostnames)) != expected_nodes:
    fail("Hostname-urile inventarelor nu sunt unice.")

core_distribution = Counter(
    item["physical_cores"] for item in inventories
)

expected_distribution = Counter({41: 8, 42: 8})
if core_distribution != expected_distribution:
    fail(
        "Distribuția nucleelor fizice nu corespunde configurației propuse. "
        f"Observat: {dict(core_distribution)}; "
        f"așteptat: {dict(expected_distribution)}."
    )

observed_total_cores = sum(
    item["physical_cores"] for item in inventories
)
if observed_total_cores != expected_tasks:
    fail(
        f"Totalul observat este {observed_total_cores}, "
        f"nu {expected_tasks}."
    )

# Each node must report a positive RAM capacity. The proposed 256 GiB
# reference is recorded, but this check does not confuse host RAM with
# memory actually allocated to the Slurm job.
for item in inventories:
    memory = item["memory_total_bytes"]
    if not isinstance(memory, int) or memory <= 0:
        fail(f"{item['hostname']}: capacitatea RAM nu este determinată.")

summary = {
    "schema": "qflpn-p3-hpc-preflight-summary",
    "schema_version": "1.0.0",
    "status": "PREFLIGHT_PASSED",
    "cluster_acceptance": "NOT_EVALUATED",
    "p3_verdict": "NOT_EVALUATED",
    "slurm_job_id": job_id,
    "configuration_id": config.get("configuration_id"),
    "configuration_status": config.get("configuration_status"),
    "expected_nodes": expected_nodes,
    "observed_nodes": len(inventories),
    "expected_physical_cores": expected_tasks,
    "observed_physical_cores": observed_total_cores,
    "physical_core_distribution": {
        str(key): value
        for key, value in sorted(core_distribution.items())
    },
    "node_inventories": sorted(
        inventories,
        key=lambda item: item["hostname"],
    ),
    "limitations": [
        "Preflight-ul verifică topologia observată și alocarea Slurm.",
        "Nu execută benchmarkul SpMV.",
        "Nu măsoară bandwidth DRAM sau performanța rețelei.",
        "Nu demonstrează scalarea MPI.",
        "Nu poate declara P3_ACCEPTED.",
        "Rezultatele HPC trebuie validate ulterior prin p3_validation.",
    ],
    "validated_at_utc": datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    ),
}

destination = output_dir / "PREFLIGHT_SUMMARY.json"
temporary = destination.with_suffix(".json.tmp")
temporary.write_text(
    json.dumps(
        summary,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)
temporary.replace(destination)

print("PREFLIGHT_STATUS=PREFLIGHT_PASSED")
print(f"OBSERVED_NODES={len(inventories)}")
print(f"OBSERVED_PHYSICAL_CORES={observed_total_cores}")
print("CLUSTER_ACCEPTANCE=NOT_EVALUATED")
print("P3_VERDICT=NOT_EVALUATED")
print(f"SUMMARY_FILE={destination}")
PY

log "Preflight HPC trecut."
log "Acesta NU este un benchmark și NU reprezintă P3_ACCEPTED."
log "Următoarea validare a artefactelor trebuie făcută prin p3_validation."

exit 0
