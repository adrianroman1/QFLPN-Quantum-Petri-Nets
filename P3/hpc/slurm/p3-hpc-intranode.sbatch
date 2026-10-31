#!/usr/bin/env bash
# =============================================================================
# UNTESTED TEMPLATE - no Slurm cluster was available when this was written.
# Review the directives against your site's policy before use.
#
# Single-node (intra-node) harness campaign. It does NOT run MPI and it does
# NOT demonstrate a distributed or 664-core result: one JVM sees only the
# cores of one node. Use collect_hpc_inventory.py on every node to demonstrate
# what hardware a campaign really had.
# =============================================================================
#SBATCH --job-name=p3-hpc-intranode
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --cpus-per-task=42
#SBATCH --mem=0
#SBATCH --time=04:00:00
#SBATCH --output=p3-hpc-intranode-%j.log

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"

# The inventory is recorded first: the allocation, not the application
# settings, is what the campaign is allowed to claim.
python3 P3/hpc/tools/collect_hpc_inventory.py collect \
  > "node-inventory-${SLURM_JOB_ID}-${SLURMD_NODENAME:-$(hostname)}.json"

SIZES="${SIZES:-10000000}" \
PARALLELISMS="${PARALLELISMS:-1 2 4 8 16 32 42}" \
THRESHOLDS="${THRESHOLDS:-256 1024 4096 16384}" \
FORKS="${FORKS:-5}" ITERATIONS="${ITERATIONS:-10}" WARMUP="${WARMUP:-10}" \
HEAP_MB="${HEAP_MB:-65536}" \
RUN_ID="h3-slurm-${SLURM_JOB_ID}" \
STRICT=1 \
bash P3/results/run_parallel_harness.sh
