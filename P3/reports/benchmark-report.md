# QFLPN P3 — Benchmark Results and HPC Scaling Report

## 1. Experimental scope

This report defines the benchmark campaign for four state-space
dimensions:

- 1,000,000 states
- 10,000,000 states
- 70,000,000 states
- 100,000,000 states

The parallel execution campaign covers 1–664 physical cores.

All benchmark evidence must be generated, validated, and retained
through the `p3_validation` workflow.

The required integrity chain is:

p3_validation
    -> benchmark evidence
    -> validation reports
    -> MANIFEST.txt
    -> SHA256SUMS.txt
    -> final package verification

No unmeasured performance value is reported as an experimental result.

## 2. Latest verified benchmark execution

| Field | Value |
|---|---|
| Workflow | P3 Validation — Full Evidence and Integrity Chain |
| RUN_ID | p3-41240843414-1 |
| Commit | 4ed8a67ee6ff78d7753455128e10788e229700dd |
| Validation | PASS |
| Schema | qflpn-benchmark-v2 |
| Valid CSV records | 81 |
| Benchmark ID | QFLPN-1M |
| State dimension | 1,000,000 |
| Non-zero values | 2,000,000 |
| Warm-up iterations | 5 |
| Measured iterations | 10 |

## 3. Measured V2 results — 1 million states

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean time (ms) | 3.035330 | 3.792832 |
| Median time (ms) | 2.688117 | 3.914198 |
| Standard deviation (ms) | 0.712947 | 0.671135 |
| Throughput (states/s) | 329453447.931 | 263655203.958 |
| Oracle error | 0.000000000000e+00 | 0.000000000000e+00 |

Measured speedup:

0.800281×

The parallel execution is slower than the sequential execution
for this measured configuration.

Maximum absolute numerical error:

0.000000000000e+00

The CSV row and JSON validation report were matched using the
exact RUN_ID.

## 4. Required state-dimension campaign

| State dimension | Sequential benchmark | Parallel benchmark | Speedup | Numerical error | Status |
|---:|---|---|---|---|---|
| 1,000,000 | 3.035330 ms mean | 3.792832 ms mean | 0.800281× | 0 | MEASURED |
| 10,000,000 | Pending | Pending | Pending | Pending | NOT MEASURED |
| 70,000,000 | Pending | Pending | Pending | Pending | NOT MEASURED |
| 100,000,000 | Pending | Pending | Pending | Pending | NOT MEASURED |

Each dimension must be benchmarked independently.
Results must not be extrapolated from the 1-million-state run.

## 5. Parallelism campaign — 1 to 664 physical cores

The following table defines the reporting structure.
Every row requires an actual execution and hardware inventory.

| Physical cores | 1M states | 10M states | 70M states | 100M states |
|---:|---|---|---|---|
| 1 | Pending | Pending | Pending | Pending |
| 2 | Pending | Pending | Pending | Pending |
| 4 | Pending | Pending | Pending | Pending |
| 8 | Pending | Pending | Pending | Pending |
| 16 | Pending | Pending | Pending | Pending |
| 32 | Pending | Pending | Pending | Pending |
| 64 | Pending | Pending | Pending | Pending |
| 128 | Pending | Pending | Pending | Pending |
| 256 | Pending | Pending | Pending | Pending |
| 512 | Pending | Pending | Pending | Pending |
| 640 | Pending | Pending | Pending | Pending |
| 664 | Pending | Pending | Pending | Pending |

Intermediate core counts may be included in the complete
machine-readable benchmark inventory when actually executed.

No result may be assigned to a core count that was not measured.

## 6. SpMV threshold campaign

The following thresholds must be evaluated:

| SpMV threshold | 1M states | 10M states | 70M states | 100M states |
|---:|---|---|---|---|
| 256 | Pending | Pending | Pending | Pending |
| 512 | Pending | Pending | Pending | Pending |
| 1,024 | Pending | Pending | Pending | Pending |
| 2,048 | Pending | Pending | Pending | Pending |
| 4,096 | Pending | Pending | Pending | Pending |
| 8,192 | Pending | Pending | Pending | Pending |
| 16,384 | Pending | Pending | Pending | Pending |

Each threshold must be evaluated against the same input,
hardware configuration, and measurement protocol.

## 7. Required performance metrics

Every valid benchmark configuration must record:

| Metric | Definition |
|---|---|
| Sequential mean | Arithmetic mean of sequential measurements |
| Sequential median | Median sequential execution time |
| Parallel mean | Arithmetic mean of parallel measurements |
| Parallel median | Median parallel execution time |
| Standard deviation | Measurement dispersion |
| Speedup | T_sequential / T_parallel |
| Parallel efficiency | Speedup / number of workers |
| Throughput | Processed states per second |
| Memory consumption | Measured peak resident memory |
| Numerical error | Maximum absolute deviation from oracle |
| Physical cores | Verified physical-core inventory |
| Worker count | Actual workers used |
| SpMV threshold | Actual threshold used |
| RUN_ID | Unique workflow execution identity |

Minimum experimental protocol:

- At least 5 warm-up iterations.
- At least 30 valid measured iterations for the final HPC campaign.
- Identical input data for sequential and parallel comparisons.
- Numerical equivalence verification.
- Explicit recording of failed and incomplete configurations.

## 8. Hardware and environment evidence

A physical-core scaling claim requires evidence from the
actual execution environment.

Required inventory:

- CPU model and architecture.
- Physical cores and logical processors.
- NUMA topology.
- RAM capacity.
- Operating system and kernel.
- Java runtime.
- Maven version.
- Compiler and runtime options.
- Worker count.
- Process affinity and CPU allocation.
- Benchmark RUN_ID and source commit.

The proposed 664-core reference configuration is not,
by itself, proof of an available HPC system.

## 9. Required evidence artifacts

Every benchmark campaign must preserve:

| Artifact | Requirement |
|---|---|
| benchmark_results_v2.csv | Raw V2 measurements |
| benchmark_results_v3.csv | V3 configuration measurements |
| benchmark-report.md | Human-readable benchmark report |
| benchmark-report.json | Machine-readable benchmark report |
| benchmark-report.txt | Plain-text report |
| validation-report.json | Validation result |
| environment.json | Runtime and hardware metadata |
| benchmark logs | Execution logs |
| checksums | File integrity evidence |
| MANIFEST.txt | Global evidence inventory |
| SHA256SUMS.txt | SHA-256 integrity verification |

All artifacts must be connected to the same `p3_validation`
execution identity.

## 10. Current evidence-based verdict

| Validation item | Result |
|---|---|
| Latest V2 benchmark | PASS |
| V2 numerical oracle | PASS |
| V2 CSV/JSON RUN_ID consistency | PASS |
| V3 validation stage | PASS |
| MPI validation stage | PASS |
| MANIFEST generation | PASS |
| SHA256SUMS generation | PASS |
| Final package verification | PASS |
| 1M-state benchmark | MEASURED |
| 10M-state benchmark | NOT MEASURED |
| 70M-state benchmark | NOT MEASURED |
| 100M-state benchmark | NOT MEASURED |
| Full 1–664 physical-core campaign | NOT DEMONSTRATED |

The latest `p3_validation` execution passed its configured
validation gates.

This PASS does not establish that the complete large-scale
HPC campaign has been executed.

The four required state dimensions and the physical-core
scaling campaign remain separate experimental obligations.
