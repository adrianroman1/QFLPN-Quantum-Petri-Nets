#!/usr/bin/env bash
# Reproduces run h3-SANDBOX-1CPU-EXAMPLE-4cb7634 (commit 4cb7634) with the same parameters.
# Note: results depend on the machine; compare environment.json first.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git checkout 4cb7634
SIZES="1000000" WORKLOADS="UNIFORM_2 POWERLAW" STRATEGIES="SEQ FJ_PLAN STATIC" \
PARALLELISMS="1 2 4" THRESHOLDS="1024 4096" \
THRESHOLD_MODE=ROW_THRESHOLD FORKS=3 WARMUP=5 \
ITERATIONS=10 HEAP_MB=2048 STRICT=0 \
bash P3/results/run_parallel_harness.sh
