# Inventory

## New (ADD/)
- P3/code/DistributedCsrPartition.java
- P3/code/DistributedSpmvSimulation.java
- P3/hpc/config/hpc-664.json
- P3/hpc/tools/collect_hpc_inventory.py
- P3/hpc/slurm/p3-hpc-intranode.sbatch (untested template)
- P3/tests/DistributedSpmvTest.java
- P3/tests/test_check_harness_gate.py
- P3/tests/test_hpc_inventory.py
- P3/tests/test_run_parallel_harness_build.py
- P3/tools/check_harness_gate.py

## Modified (REPLACE_MY_UPLOADED_FILES/, all from wave 1)
- P3/code/PlannedForkJoinSpmvStrategy.java  (public API only; explicit ThresholdMode)
- P3/code/StaticChunkSpmvStrategy.java      (public API only; no SparseMatrixCSR edit needed)
- P3/benchmarks/harness/ParallelSpmvHarness.java (threshold sweep)
- P3/results/run_parallel_harness.sh        (fail-closed build, THRESHOLDS, STRICT, HARNESS_OUT_DIR, P3_SRC_DIR)
- P3/tools/summarize_harness.py             (C0, C8, fail-closed validation, exit codes)
- P3/tools/generate_results_md.py           (--no-latest-copy)
- P3/tests/test_summarize_harness.py, P3/tests/test_generate_results_md.py
- P3/README.md

## Patched
- .github/workflows/p3-validation.yml (+49 lines, additive)

## Kept untouched
Everything else, including P1, `SparseMatrixCSR`, `MultiplyTask`, `SpmvPlan`,
`QFLPNCoreEngine`, all existing tests, manifests, CSV and reports.
