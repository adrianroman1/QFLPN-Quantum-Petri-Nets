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
# Canonical target:
#   P3/hpc/config/hpc-target.json
#   qflpn-p3-hpc-target-v2
#
# Node inventory:
#   qflpn-p3-hpc-node-inventory-v1
#
# Aggregate inventory:
#   qflpn-p3-hpc-cluster-inventory-v1
#
# This script:
#   1. validates the canonical target configuration;
#   2. validates the Slurm allocation;
#   3. collects one inventory per allocated compute node;
#   4. checks inventory provenance and Slurm job membership;
#   5. validates all inventories using collect_hpc_inventory.py;
#   6. writes an explicit PASS / DEFERRED / FAIL summary.
#
# It does NOT:
#   - execute SpMV;
#   - measure performance or DRAM bandwidth;
#   - demonstrate 664-worker execution;
#   - demonstrate dimension 10,000,000 execution;
#   - declare P3_ACCEPTED.
#
# The target is a proposed reference configuration, not evidence of
# an already existing or verified 16-node cluster.
#
# Launch from repository root:
#   sbatch P3/hpc/slurm/p3-hpc-preflight.sbatch
#
# Optional output directory:
#   sbatch --export=ALL,P3_HPC_OUTPUT_DIR=/shared/p3/preflight \
#     P3/hpc/slurm/p3-hpc-preflight.sbatch
#
# Exit codes:
#   0 — preflight completed; result may be PASS or DEFERRED;
#   2 — invalid command, file, or target configuration;
#   3 — invalid Slurm allocation or inventory;
#   4 — unexpected execution error.

set -Eeuo pipefail
IFS=$'\n\t'
umask 027

readonly EXPECTED_NODES=16
readonly EXPECTED_TASKS=664
readonly TARGET_SCHEMA="qflpn-p3-hpc-target-v2"
readonly INVENTORY_SCHEMA="qflpn-p3-hpc-node-inventory-v1"

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
require_command find
require_command sort

[[ -n "${SLURM_JOB_ID:-}" ]] \
    || fail "SLURM_JOB_ID absent; scriptul trebuie lansat prin sbatch." 3

[[ -n "${SLURM_JOB_NODELIST:-}" ]] \
    || fail "SLURM_JOB_NODELIST absent." 3

[[ -n "${SLURM_NNODES:-}" ]] \
    || fail "SLURM_NNODES absent." 3

[[ -n "${SLURM_NTASKS:-}" ]] \
    || fail "SLURM_NTASKS absent." 3

readonly REPOSITORY_ROOT="${SLURM_SUBMIT_DIR:-$PWD}"
readonly CONFIG="${REPOSITORY_ROOT}/P3/hpc/config/hpc-target.json"
readonly COLLECTOR="${REPOSITORY_ROOT}/P3/hpc/tools/collect_hpc_inventory.py"

require_file "$CONFIG"
require_file "$COLLECTOR"

readonly OUTPUT_DIR="${P3_HPC_OUTPUT_DIR:-${REPOSITORY_ROOT}/P3/results/hpc/preflight-${SLURM_JOB_ID}}"
readonly INVENTORY_DIR="${OUTPUT_DIR}/node-inventories"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$INVENTORY_DIR"

[[ -d "$OUTPUT_DIR" && -w "$OUTPUT_DIR" ]] \
    || fail "Directorul de rezultate nu permite scrierea: ${OUTPUT_DIR}" 2

[[ -d "$INVENTORY_DIR" && -w "$INVENTORY_DIR" ]] \
    || fail "Directorul inventarelor nu permite scrierea: ${INVENTORY_DIR}" 2

log "Repository: ${REPOSITORY_ROOT}"
log "Target: ${CONFIG}"
log "Slurm job: ${SLURM_JOB_ID}"
log "Node list: ${SLURM_JOB_NODELIST}"
log "Allocated nodes: ${SLURM_NNODES}"
log "Allocated tasks: ${SLURM_NTASKS}"
log "Output: ${OUTPUT_DIR}"

# ---------------------------------------------------------------------------
# 1. Validarea configurației canonice qflpn-p3-hpc-target-v2.
# ---------------------------------------------------------------------------

python3 - \
    "$CONFIG" \
    "$TARGET_SCHEMA" \
    "$EXPECTED_NODES" \
    "$EXPECTED_TASKS" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected_schema = sys.argv[2]
expected_nodes = int(sys.argv[3])
expected_cores = int(sys.argv[4])

try:
    target = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"CONFIGURATION_ERROR: {exc}", file=sys.stderr)
    raise SystemExit(2)

if not isinstance(target, dict):
    print("CONFIGURATION_ERROR: JSON root must be an object.", file=sys.stderr)
    raise SystemExit(2)

if target.get("schema") != expected_schema:
    print(
        f"CONFIGURATION_ERROR: expected schema {expected_schema!r}; "
        f"received {target.get('schema')!r}.",
        file=sys.stderr,
    )
    raise SystemExit(2)

if target.get("status") != "PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE":
    print("CONFIGURATION_ERROR: invalid target status.", file=sys.stderr)
    raise SystemExit(2)

hardware = target.get("hardware_target")
benchmark = target.get("benchmark")

if not isinstance(hardware, dict):
    print("CONFIGURATION_ERROR: hardware_target must be an object.", file=sys.stderr)
    raise SystemExit(2)

if not isinstance(benchmark, dict):
    print("CONFIGURATION_ERROR: benchmark must be an object.", file=sys.stderr)
    raise SystemExit(2)

groups = hardware.get("node_groups")
if not isinstance(groups, list) or not groups:
    print("CONFIGURATION_ERROR: hardware_target.node_groups is invalid.", file=sys.stderr)
    raise SystemExit(2)

try:
    nodes = sum(int(group["nodes"]) for group in groups)
    cores = sum(
        int(group["nodes"]) * int(group["physical_cores_per_node"])
        for group in groups
    )
    configured_nodes = int(hardware["compute_nodes"])
    configured_cores = int(hardware["physical_cores_total"])
    ram_total = int(hardware["ram_gib_total"])
    ram_per_node = int(hardware["ram_gib_per_node"])
except (KeyError, TypeError, ValueError) as exc:
    print(f"CONFIGURATION_ERROR: invalid hardware field: {exc}", file=sys.stderr)
    raise SystemExit(2)

if nodes != expected_nodes or configured_nodes != expected_nodes:
    print("CONFIGURATION_ERROR: compute node count must be 16.", file=sys.stderr)
    raise SystemExit(2)

if cores != expected_cores or configured_cores != expected_cores:
    print("CONFIGURATION_ERROR: physical core total must be 664.", file=sys.stderr)
    raise SystemExit(2)

if ram_per_node != 256 or ram_total != 4096:
    print("CONFIGURATION_ERROR: expected RAM target is 16 x 256 GiB.", file=sys.stderr)
    raise SystemExit(2)

if ram_total != nodes * ram_per_node:
    print("CONFIGURATION_ERROR: RAM totals are inconsistent.", file=sys.stderr)
    raise SystemExit(2)

motherboard = hardware.get("motherboard")
if not isinstance(motherboard, dict):
    print("CONFIGURATION_ERROR: motherboard contract is missing.", file=sys.stderr)
    raise SystemExit(2)

if motherboard.get("collection_required") is not True:
    print("CONFIGURATION_ERROR: motherboard collection must be required.", file=sys.stderr)
    raise SystemExit(2)

if motherboard.get("fields") != ["manufacturer", "model", "version"]:
    print("CONFIGURATION_ERROR: invalid motherboard field contract.", file=sys.stderr)
    raise SystemExit(2)

if motherboard.get("missing_value") != "UNAVAILABLE":
    print("CONFIGURATION_ERROR: missing motherboard value must be UNAVAILABLE.", file=sys.stderr)
    raise SystemExit(2)

if benchmark.get("workload") != "SpMV":
    print("CONFIGURATION_ERROR: benchmark workload must be SpMV.", file=sys.stderr)
    raise SystemExit(2)

if benchmark.get("parallelism_target") != 664:
    print("CONFIGURATION_ERROR: parallelism_target must be 664.", file=sys.stderr)
    raise SystemExit(2)

if 664 not in benchmark.get("worker_counts", []):
    print("CONFIGURATION_ERROR: worker_counts must include 664.", file=sys.stderr)
    raise SystemExit(2)

if benchmark.get("maximum_target_dimension") != 10000000:
    print("CONFIGURATION_ERROR: maximum_target_dimension must be 10000000.", file=sys.stderr)
    raise SystemExit(2)

if 10000000 not in benchmark.get("thresholds", []):
    print("CONFIGURATION_ERROR: thresholds must include 10000000.", file=sys.stderr)
    raise SystemExit(2)

if benchmark.get("minimum_warmup") != 5:
    print("CONFIGURATION_ERROR: minimum_warmup must be 5.", file=sys.stderr)
    raise SystemExit(2)

if benchmark.get("minimum_valid_measurements") != 30:
    print("CONFIGURATION_ERROR: minimum_valid_measurements must be 30.", file=sys.stderr)
    raise SystemExit(2)

if benchmark.get("execution_status") != "NOT_EXECUTED":
    print("CONFIGURATION_ERROR: proposed benchmark must remain NOT_EXECUTED.", file=sys.stderr)
    raise SystemExit(2)

print("CONFIGURATION_STATUS=VALID")
print(f"TARGET_NODES={nodes}")
print(f"TARGET_PHYSICAL_CORES={cores}")
print(f"TARGET_RAM_GIB={ram_total}")
print("TARGET_PARALLELISM=664")
print("TARGET_MAXIMUM_DIMENSION=10000000")
print("BENCHMARK_EXECUTION_STATUS=NOT_EXECUTED")
PY

# ---------------------------------------------------------------------------
# 2. Verificarea alocării Slurm.
# ---------------------------------------------------------------------------

if [[ "$SLURM_NNODES" -ne "$EXPECTED_NODES" ]]; then
    fail "Alocarea are ${SLURM_NNODES} noduri; sunt necesare ${EXPECTED_NODES}." 3
fi

if [[ "$SLURM_NTASKS" -ne "$EXPECTED_TASKS" ]]; then
    fail "Alocarea are ${SLURM_NTASKS} task-uri; sunt necesare ${EXPECTED_TASKS}." 3
fi

scontrol show job "$SLURM_JOB_ID" \
    > "${OUTPUT_DIR}/slurm-job-${SLURM_JOB_ID}.txt" \
    || fail "Nu s-a putut salva descrierea jobului Slurm." 3

scontrol show hostnames "$SLURM_JOB_NODELIST" \
    > "${OUTPUT_DIR}/allocated-hosts.txt" \
    || fail "Nu s-a putut obține lista nodurilor alocate." 3

python3 - \
    "${OUTPUT_DIR}/allocated-hosts.txt" \
    "$EXPECTED_NODES" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected = int(sys.argv[2])

hosts = [
    line.strip()
    for line in path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

normalized = [host.split(".", 1)[0].lower() for host in hosts]

if len(hosts) != expected:
    print(
        f"SLURM_ERROR: expected {expected} host entries; got {len(hosts)}.",
        file=sys.stderr,
    )
    raise SystemExit(3)

if len(set(normalized)) != expected:
    print("SLURM_ERROR: duplicate allocated hostnames.", file=sys.stderr)
    raise SystemExit(3)

print(f"SLURM_HOST_COUNT={len(hosts)}")
print("SLURM_HOST_UNIQUENESS=PASS")
PY

# ---------------------------------------------------------------------------
# 3. Colectarea inventarului: un task pe fiecare nod.
#
# Alocarea rezervă 664 task-uri, dar colectarea inventarului pornește
# exact 16 task-uri, câte unul pe nod.
# ---------------------------------------------------------------------------

export P3_HPC_COLLECTOR="$COLLECTOR"
export P3_HPC_INVENTORY_DIR="$INVENTORY_DIR"

log "Colectare inventar pe ${EXPECTED_NODES} noduri..."

srun \
    --nodes="$EXPECTED_NODES" \
    --ntasks="$EXPECTED_NODES" \
    --ntasks-per-node=1 \
    --cpu-bind=none \
    --kill-on-bad-exit=1 \
    --export=ALL \
    bash -c '
        set -Eeuo pipefail

        [[ -n "${SLURM_PROCID:-}" ]] || {
            echo "SLURM_PROCID absent" >&2
            exit 3
        }

        [[ -n "${SLURM_JOB_ID:-}" ]] || {
            echo "SLURM_JOB_ID absent on node" >&2
            exit 3
        }

        output="${P3_HPC_INVENTORY_DIR}/node-${SLURM_PROCID}.json"
        temporary="${output}.tmp"

        python3 "$P3_HPC_COLLECTOR" collect > "$temporary"
        python3 -m json.tool "$temporary" > /dev/null
        mv "$temporary" "$output"
    ' \
    || fail "Colectarea inventarului a eșuat pe cel puțin un nod." 3

# ---------------------------------------------------------------------------
# 4. Verificarea inventarelor colectate.
# ---------------------------------------------------------------------------

python3 - \
    "$INVENTORY_DIR" \
    "$INVENTORY_SCHEMA" \
    "$EXPECTED_NODES" \
    "$SLURM_JOB_ID" <<'PY'
import json
import sys
from pathlib import Path

directory = Path(sys.argv[1])
expected_schema = sys.argv[2]
expected_count = int(sys.argv[3])
expected_job_id = str(sys.argv[4])

files = sorted(directory.glob("node-*.json"))

if len(files) != expected_count:
    print(
        f"INVENTORY_ERROR: expected {expected_count} inventories; "
        f"found {len(files)}.",
        file=sys.stderr,
    )
    raise SystemExit(3)

hostnames = []
process_ids = []

for path in files:
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"INVENTORY_ERROR: {path.name}: {exc}", file=sys.stderr)
        raise SystemExit(3)

    if not isinstance(item, dict):
        print(f"INVENTORY_ERROR: {path.name} root is not an object.", file=sys.stderr)
        raise SystemExit(3)

    if item.get("schema") != expected_schema:
        print(f"INVENTORY_ERROR: invalid schema in {path.name}.", file=sys.stderr)
        raise SystemExit(3)

    hostname = item.get("hostname")
    if not isinstance(hostname, str) or not hostname.strip():
        print(f"INVENTORY_ERROR: missing hostname in {path.name}.", file=sys.stderr)
        raise SystemExit(3)

    hostnames.append(hostname.strip().split(".", 1)[0].lower())

    slurm = item.get("slurm")
    if not isinstance(slurm, dict):
        print(f"INVENTORY_ERROR: missing slurm object in {path.name}.", file=sys.stderr)
        raise SystemExit(3)

    observed_job_id = slurm.get("SLURM_JOB_ID")
    if str(observed_job_id) != expected_job_id:
        print(
            f"INVENTORY_ERROR: {path.name} belongs to job "
            f"{observed_job_id!r}, expected {expected_job_id!r}.",
            file=sys.stderr,
        )
        raise SystemExit(3)

    try:
        process_id = int(slurm["SLURM_PROCID"])
    except (KeyError, TypeError, ValueError):
        print(f"INVENTORY_ERROR: invalid SLURM_PROCID in {path.name}.", file=sys.stderr)
        raise SystemExit(3)

    process_ids.append(process_id)

if len(set(hostnames)) != expected_count:
    print("INVENTORY_ERROR: duplicate inventory hostnames.", file=sys.stderr)
    raise SystemExit(3)

if sorted(process_ids) != list(range(expected_count)):
    print(
        "INVENTORY_ERROR: SLURM_PROCID values must cover 0..15 exactly.",
        file=sys.stderr,
    )
    raise SystemExit(3)

print("INVENTORY_SCHEMA_STATUS=VALID")
print(f"INVENTORY_COUNT={len(files)}")
print(f"DISTINCT_HOST_COUNT={len(set(hostnames))}")
print("SLURM_JOB_ID_CONSISTENCY=PASS")
print("SLURM_PROCID_COVERAGE=PASS")
PY

# ---------------------------------------------------------------------------
# 5. Validarea targetului și a inventarelor prin API-ul CLI canonic.
#
# Collector contract:
#   PASS     -> exit 0
#   DEFERRED -> exit 1
#   FAIL     -> exit 1
#
# DEFERRED este un rezultat valid al validării, nu o eroare de execuție.
# Nu este transformat în PASS.
# ---------------------------------------------------------------------------

mapfile -t INVENTORY_FILES < <(
    find "$INVENTORY_DIR" -maxdepth 1 -type f -name 'node-*.json' -print | sort
)

if [[ "${#INVENTORY_FILES[@]}" -ne "$EXPECTED_NODES" ]]; then
    fail "Numărul inventarelor nu este ${EXPECTED_NODES}." 3
fi

log "Validare inventare față de hpc-target.json..."

set +e
python3 "$COLLECTOR" validate "$CONFIG" "${INVENTORY_FILES[@]}" \
    > "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.json" \
    2> "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.stderr"
VALIDATION_EXIT=$?
set -e

if [[ ! -s "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.json" ]]; then
    cat "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.stderr" >&2 || true
    fail "Validatorul nu a produs un raport JSON." 3
fi

# Verificăm atât codul de ieșire, cât și verdictul JSON.
# Codul 0 este permis exclusiv pentru PASS.
# Codul 1 este permis exclusiv pentru DEFERRED sau FAIL.
# Orice alt cod sau combinație este o eroare de validare.

case "$VALIDATION_EXIT" in
    0)
        EXPECTED_VALIDATION_EXIT_CLASS="PASS"
        ;;
    1)
        EXPECTED_VALIDATION_EXIT_CLASS="DEFERRED_OR_FAIL"
        ;;
    *)
        cat "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.json" >&2
        cat "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.stderr" >&2 || true
        fail "Validatorul colectorului a returnat un cod neașteptat: ${VALIDATION_EXIT}." 3
        ;;
esac

python3 - \
    "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.json" \
    "$VALIDATION_EXIT" \
    "$EXPECTED_VALIDATION_EXIT_CLASS" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
exit_code = int(sys.argv[2])
exit_class = sys.argv[3]

try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"VALIDATION_CONTRACT_ERROR: invalid JSON: {exc}", file=sys.stderr)
    raise SystemExit(3)

if not isinstance(report, dict):
    print(
        "VALIDATION_CONTRACT_ERROR: validation report must be a JSON object.",
        file=sys.stderr,
    )
    raise SystemExit(3)

overall = report.get("overall")

if overall not in {"PASS", "DEFERRED", "FAIL"}:
    print(
        f"VALIDATION_CONTRACT_ERROR: unsupported overall status {overall!r}.",
        file=sys.stderr,
    )
    raise SystemExit(3)

if exit_class == "PASS":
    if exit_code != 0 or overall != "PASS":
        print(
            "VALIDATION_CONTRACT_ERROR: exit code 0 requires overall PASS.",
            file=sys.stderr,
        )
        raise SystemExit(3)

elif exit_class == "DEFERRED_OR_FAIL":
    if exit_code != 1 or overall not in {"DEFERRED", "FAIL"}:
        print(
            "VALIDATION_CONTRACT_ERROR: exit code 1 requires "
            "overall DEFERRED or FAIL.",
            file=sys.stderr,
        )
        raise SystemExit(3)

else:
    print(
        f"VALIDATION_CONTRACT_ERROR: unknown exit class {exit_class!r}.",
        file=sys.stderr,
    )
    raise SystemExit(3)

print(f"COLLECTOR_EXIT_CODE={exit_code}")
print(f"COLLECTOR_OVERALL_STATUS={overall}")
print("COLLECTOR_EXIT_STATUS_CONSISTENCY=PASS")
PY

# ---------------------------------------------------------------------------
# 6. Rezumatul final.
#
# PASS:
#   toate verificările hardware și de inventar au trecut.
#
# DEFERRED:
#   nu există FAIL, dar una sau mai multe verificări nu pot fi confirmate
#   (de exemplu, identificarea plăcii de bază este UNAVAILABLE).
#
# FAIL:
#   o verificare obligatorie a eșuat.
#
# Niciun rezultat nu reprezintă dovadă de performanță SpMV.
# ---------------------------------------------------------------------------

python3 - \
    "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.json" \
    "${OUTPUT_DIR}/PREFLIGHT_SUMMARY.json" \
    "$SLURM_JOB_ID" \
    "$EXPECTED_NODES" \
    "$EXPECTED_TASKS" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

validation_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
job_id = str(sys.argv[3])
expected_nodes = int(sys.argv[4])
expected_cores = int(sys.argv[5])

try:
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"SUMMARY_ERROR: invalid validation JSON: {exc}", file=sys.stderr)
    raise SystemExit(3)

if not isinstance(validation, dict):
    print("SUMMARY_ERROR: validation result must be an object.", file=sys.stderr)
    raise SystemExit(3)

overall = validation.get("overall")

if overall not in {"PASS", "DEFERRED", "FAIL"}:
    print(
        f"SUMMARY_ERROR: unsupported overall status {overall!r}.",
        file=sys.stderr,
    )
    raise SystemExit(3)

if overall == "FAIL":
    print("SUMMARY_STATUS=FAIL")
    raise SystemExit(3)

summary = {
    "schema": "qflpn-p3-hpc-preflight-summary-v2",
    "status": (
        "PREFLIGHT_PASSED"
        if overall == "PASS"
        else "PREFLIGHT_DEFERRED"
    ),
    "validation_status": overall,
    "slurm_job_id": job_id,
    "expected_nodes": expected_nodes,
    "expected_allocation_tasks": expected_cores,
    "target_validation": validation,
    "cluster_acceptance": "NOT_EVALUATED",
    "p3_verdict": "NOT_EVALUATED",
    "benchmark_execution_status": "NOT_EXECUTED",
    "limitations": [
        "Preflight-ul verifică inventarele hardware și configurația-țintă.",
        "Preflight-ul nu execută benchmarkul SpMV.",
        "Preflight-ul nu măsoară bandwidth DRAM.",
        "Preflight-ul nu demonstrează scalarea MPI.",
        "Preflight-ul nu demonstrează execuția cu 664 workeri.",
        "Preflight-ul nu demonstrează execuția la dimensiunea 10000000.",
        "Preflight-ul nu declară P3_ACCEPTED.",
        "Dovezile benchmarkului trebuie validate separat prin p3_validation.",
    ],
    "validated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
}

temporary = summary_path.with_suffix(".json.tmp")
temporary.write_text(
    json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
temporary.replace(summary_path)

print(f"SUMMARY_STATUS={overall}")
print(f"PREFLIGHT_STATUS={summary['status']}")
print(f"EXPECTED_NODES={expected_nodes}")
print(f"EXPECTED_PHYSICAL_CORES={expected_cores}")
print("CLUSTER_ACCEPTANCE=NOT_EVALUATED")
print("P3_VERDICT=NOT_EVALUATED")
print("BENCHMARK_EXECUTION_STATUS=NOT_EXECUTED")
print(f"SUMMARY_FILE={summary_path}")
PY

log "Preflight finalizat: ${OUTPUT_DIR}/PREFLIGHT_SUMMARY.json"
log "Acceptarea clusterului rămâne NOT_EVALUATED."
log "P3_ACCEPTED nu este declarat."
log "Validarea finală a dovezilor P3 rămâne în p3_validation."

exit 0
