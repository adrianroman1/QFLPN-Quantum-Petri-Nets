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
# Contracte canonice:
#   Target:    qflpn-p3-hpc-target-v1
#   Inventory: qflpn-p3-hpc-node-inventory-v1
#
# Colector:
#   collect_hpc_inventory.py collect
#   collect_hpc_inventory.py validate TARGET INVENTORY...
#
# Acest script:
#   - verifică alocarea Slurm;
#   - colectează un inventar independent pe fiecare nod;
#   - validează inventarele față de hpc-664.json;
#   - verifică apartenența inventarelor la același job Slurm.
#
# Nu execută benchmark SpMV.
# Nu validează scalarea MPI.
# Nu declară P3_ACCEPTED.
#
# Lansare din rădăcina repository-ului:
#   sbatch P3/hpc/slurm/p3-hpc-preflight.sbatch
#
# Director opțional:
#   sbatch --export=ALL,P3_HPC_OUTPUT_DIR=/shared/p3/preflight \
#     P3/hpc/slurm/p3-hpc-preflight.sbatch
#
# Coduri de ieșire:
#   0 — preflight PASS; acceptarea clusterului rămâne neevaluată;
#   2 — comandă, fișier sau configurație invalidă;
#   3 — alocare Slurm sau inventar invalid;
#   4 — eroare neașteptată de execuție.

set -Eeuo pipefail
IFS=$'\n\t'
umask 027

readonly EXPECTED_NODES=16
readonly EXPECTED_TASKS=664
readonly TARGET_SCHEMA="qflpn-p3-hpc-target-v1"
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

[[ -n "${SLURM_JOB_ID:-}" ]] \
    || fail "Nu există SLURM_JOB_ID; scriptul trebuie executat prin sbatch." 3

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
    || fail "Directorul de rezultate nu permite scrierea: ${OUTPUT_DIR}" 2

readonly INVENTORY_DIR="${OUTPUT_DIR}/node-inventories"
mkdir -p "$INVENTORY_DIR"

log "Repository: ${REPOSITORY_ROOT}"
log "Slurm job: ${SLURM_JOB_ID}"
log "Node list: ${SLURM_JOB_NODELIST}"
log "Allocated nodes: ${SLURM_NNODES}"
log "Allocated tasks: ${SLURM_NTASKS}"
log "Output: ${OUTPUT_DIR}"

# ---------------------------------------------------------------------------
# 1. Validarea configurației-țintă canonice.
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
    print("CONFIGURATION_ERROR: rădăcina JSON nu este obiect.", file=sys.stderr)
    raise SystemExit(2)

if target.get("schema") != expected_schema:
    print(
        f"CONFIGURATION_ERROR: schema trebuie să fie {expected_schema}.",
        file=sys.stderr,
    )
    raise SystemExit(2)

if target.get("status") != "PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE":
    print(
        "CONFIGURATION_ERROR: statusul configurației-țintă este invalid.",
        file=sys.stderr,
    )
    raise SystemExit(2)

groups = target.get("node_groups")
if not isinstance(groups, list) or not groups:
    print("CONFIGURATION_ERROR: node_groups absent sau invalid.", file=sys.stderr)
    raise SystemExit(2)

try:
    nodes = sum(int(group["nodes"]) for group in groups)
    cores = sum(
        int(group["nodes"]) * int(group["physical_cores_per_node"])
        for group in groups
    )
    ram_total = int(target["ram_gib_total"])
    ram_per_node = int(target["ram_gib_per_node"])
except (KeyError, TypeError, ValueError) as exc:
    print(f"CONFIGURATION_ERROR: câmp invalid: {exc}", file=sys.stderr)
    raise SystemExit(2)

if nodes != expected_nodes or target.get("compute_nodes") != expected_nodes:
    print("CONFIGURATION_ERROR: numărul de noduri nu este 16.", file=sys.stderr)
    raise SystemExit(2)

if cores != expected_cores or target.get("physical_cores_total") != expected_cores:
    print("CONFIGURATION_ERROR: totalul nucleelor nu este 664.", file=sys.stderr)
    raise SystemExit(2)

if ram_per_node <= 0 or ram_total != nodes * ram_per_node:
    print("CONFIGURATION_ERROR: configurația RAM este inconsistentă.", file=sys.stderr)
    raise SystemExit(2)

print("CONFIGURATION_STATUS=VALID")
print(f"TARGET_NODES={nodes}")
print(f"TARGET_PHYSICAL_CORES={cores}")
print(f"TARGET_RAM_GIB={ram_total}")
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

HOST_COUNT="$(
    python3 - "${OUTPUT_DIR}/allocated-hosts.txt" <<'PY'
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
    fail "Slurm a raportat ${HOST_COUNT} noduri unice; sunt necesare ${EXPECTED_NODES}." 3
fi

# ---------------------------------------------------------------------------
# 3. Colectarea inventarului: un proces pe fiecare nod.
#
# Fiecare task scrie într-un fișier distinct. Nu există concurență la
# scrierea aceluiași fișier JSON.
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
            echo "SLURM_JOB_ID absent pe nod" >&2
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
# 4. Verificarea numărului de inventare, a schemei și a jobului Slurm.
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
expected_nodes = int(sys.argv[3])
expected_job_id = str(sys.argv[4])

files = sorted(directory.glob("node-*.json"))

if len(files) != expected_nodes:
    print(
        f"INVENTORY_ERROR: {len(files)} inventare; "
        f"necesare {expected_nodes}.",
        file=sys.stderr,
    )
    raise SystemExit(3)

hostnames = []

for path in files:
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"INVENTORY_ERROR: {path.name}: {exc}", file=sys.stderr)
        raise SystemExit(3)

    if item.get("schema") != expected_schema:
        print(
            f"INVENTORY_ERROR: schemă invalidă în {path.name}.",
            file=sys.stderr,
        )
        raise SystemExit(3)

    hostname = item.get("hostname")
    if not isinstance(hostname, str) or not hostname.strip():
        print(f"INVENTORY_ERROR: hostname absent în {path.name}.", file=sys.stderr)
        raise SystemExit(3)

    hostnames.append(hostname)

    slurm = item.get("slurm")
    if not isinstance(slurm, dict):
        print(f"INVENTORY_ERROR: câmpul slurm absent în {path.name}.", file=sys.stderr)
        raise SystemExit(3)

    observed_job_id = slurm.get("SLURM_JOB_ID")
    if str(observed_job_id) != expected_job_id:
        print(
            f"INVENTORY_ERROR: {path.name} aparține jobului "
            f"{observed_job_id!r}, nu {expected_job_id!r}.",
            file=sys.stderr,
        )
        raise SystemExit(3)

if len(set(hostnames)) != expected_nodes:
    print(
        "INVENTORY_ERROR: hostname-urile inventarelor nu sunt distincte.",
        file=sys.stderr,
    )
    raise SystemExit(3)

print("INVENTORY_SCHEMA_STATUS=VALID")
print(f"INVENTORY_COUNT={len(files)}")
print(f"DISTINCT_HOST_COUNT={len(set(hostnames))}")
print("SLURM_JOB_ID_CONSISTENCY=PASS")
PY

# ---------------------------------------------------------------------------
# 5. Validarea targetului cu validatorul canonic al colectorului.
#
# Rezultatul JSON este păstrat chiar și în cazul unui verdict DEFERRED/FAIL.
# Codul de ieșire al colectorului este tratat explicit.
# ---------------------------------------------------------------------------

mapfile -t INVENTORY_FILES < <(
    find "$INVENTORY_DIR" -maxdepth 1 -type f -name 'node-*.json' -print | sort
)

if [[ "${#INVENTORY_FILES[@]}" -ne "$EXPECTED_NODES" ]]; then
    fail "Numărul inventarelor după colectare nu este ${EXPECTED_NODES}." 3
fi

log "Validare inventare față de configurația-țintă..."

set +e
python3 "$COLLECTOR" validate "$CONFIG" "${INVENTORY_FILES[@]}" \
    > "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.json" \
    2> "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.stderr"
VALIDATION_EXIT=$?
set -e

if [[ ! -s "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.json" ]]; then
    cat "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.stderr" >&2 || true
    fail "Validatorul inventarului nu a produs un rezultat JSON." 3
fi

if [[ "$VALIDATION_EXIT" -ne 0 ]]; then
    cat "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.json"
    cat "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.stderr" >&2 || true
    fail "Validarea targetului HPC nu a returnat PASS (exit=${VALIDATION_EXIT})." 3
fi

# ---------------------------------------------------------------------------
# 6. Rezumat explicit. PASS aici înseamnă numai preflight hardware.
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
    print(f"SUMMARY_ERROR: rezultat de validare invalid: {exc}", file=sys.stderr)
    raise SystemExit(3)

if not isinstance(validation, dict) or validation.get("overall") != "PASS":
    print(
        "SUMMARY_ERROR: validatorul targetului nu a returnat overall=PASS.",
        file=sys.stderr,
    )
    raise SystemExit(3)

summary = {
    "schema": "qflpn-p3-hpc-preflight-summary-v1",
    "status": "PREFLIGHT_PASSED",
    "slurm_job_id": job_id,
    "target_validation": validation,
    "expected_nodes": expected_nodes,
    "expected_physical_cores": expected_cores,
    "cluster_acceptance": "NOT_EVALUATED",
    "p3_verdict": "NOT_EVALUATED",
    "limitations": [
        "Preflight-ul verifică inventarele hardware și targetul declarat.",
        "Preflight-ul nu execută benchmarkul SpMV.",
        "Preflight-ul nu măsoară bandwidth DRAM.",
        "Preflight-ul nu demonstrează scalarea MPI.",
        "Preflight-ul nu declară P3_ACCEPTED.",
        "Dovezile benchmarkului HPC trebuie integrate și verificate prin p3_validation.",
    ],
    "validated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
}

temporary = summary_path.with_suffix(".json.tmp")
temporary.write_text(
    json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
temporary.replace(summary_path)

print("PREFLIGHT_STATUS=PREFLIGHT_PASSED")
print(f"EXPECTED_NODES={expected_nodes}")
print(f"EXPECTED_PHYSICAL_CORES={expected_cores}")
print("CLUSTER_ACCEPTANCE=NOT_EVALUATED")
print("P3_VERDICT=NOT_EVALUATED")
print(f"SUMMARY_FILE={summary_path}")
PY

log "Preflight HPC trecut."
log "Acceptarea clusterului rămâne NOT_EVALUATED."
log "P3_ACCEPTED nu poate fi declarat de acest script."
log "Validarea finală a dovezilor P3 rămâne în p3_validation."

exit 0
