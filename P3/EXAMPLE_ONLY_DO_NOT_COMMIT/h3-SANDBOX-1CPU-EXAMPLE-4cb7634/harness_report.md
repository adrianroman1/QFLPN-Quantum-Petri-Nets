# P3 parallel SpMV harness report

- run_id: `h3-SANDBOX-1CPU-EXAMPLE-4cb7634`
- overall verdict: **FAIL**

## Criteria

| Criterion | Status | Detail |
|---|---|---|
| C0_INPUT_DATA_PRESENT_AND_VALID | PASS | 8 configuration(s), all observations valid, no duplicates |
| C1_SAMPLES_AT_LEAST_30 | PASS | all configurations have >= 30 samples |
| C8_DECLARED_CONFIGURATIONS_COMPLETE | PASS | all 8 declared configuration(s) observed |
| C2_BITWISE_IDENTICAL_TO_SEQUENTIAL | PASS | every strategy reproduced the sequential bits in every fork |
| C3_OVERHEAD_AT_P1_AT_MOST_5_PERCENT | FAIL | worst: STATIC UNIFORM_2 n=1000000 overhead=28.7%; 5 configuration(s) above 5.0% |
| C4_SPEEDUP_GT_1_AT_P2_N_GE_10M | NOT_EVALUATED | no p=2 rows with n >= 10M; this needs a machine with at least 2 cores and the 10M size |
| C5_NO_SIGNIFICANT_REGRESSION_AT_N_GE_1M | NOT_EVALUATED | no p >= 2 rows (single-core machine or filtered) |
| C6_BANDWIDTH_CEILING_RECORDED | PASS | 1 triad measurement(s) |
| C7_SKIPS_AND_PREFLIGHT_DOCUMENTED | PASS | 2 skipped configuration(s) with reasons, 0 preflight refusal(s) |

## Results

| workload | n | strategy | p | samples | median ms | CI95 low | CI95 high | speedup | speedup CI95 | eff | overhead % | GB/s | bw eff | bit exact |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| POWERLAW | 1000000 | FJ_PLAN_T1024 | 1 | 30 | 17.0118 | 16.5783 | 17.2456 | 0.871 | [0.868, 0.883] | 0.871 | 14.7 | 3.00 | 0.228 | True |
| POWERLAW | 1000000 | FJ_PLAN_T4096 | 1 | 30 | 16.3204 | 16.1242 | 16.7399 | 0.908 | [0.892, 0.912] | 0.908 | 10.1 | 3.13 | 0.237 | True |
| POWERLAW | 1000000 | SEQ | 1 | 30 | 14.8252 | 14.5328 | 15.1131 | 1.000 | [1.000, 1.000] | 1.000 | 0.0 | 3.45 | 0.261 | True |
| POWERLAW | 1000000 | STATIC | 1 | 30 | 15.3152 | 15.2853 | 15.4657 | 0.968 | [0.951, 0.976] | 0.968 | 3.3 | 3.34 | 0.253 | True |
| UNIFORM_2 | 1000000 | FJ_PLAN_T1024 | 1 | 30 | 3.5477 | 3.4652 | 5.4654 | 0.832 | [0.671, 0.855] | 0.832 | 20.2 | 12.40 | 0.939 | True |
| UNIFORM_2 | 1000000 | FJ_PLAN_T4096 | 1 | 30 | 3.5014 | 3.3138 | 4.1694 | 0.843 | [0.710, 0.894] | 0.843 | 18.6 | 12.57 | 0.952 | True |
| UNIFORM_2 | 1000000 | SEQ | 1 | 30 | 2.9521 | 2.6907 | 3.0838 | 1.000 | [1.000, 1.000] | 1.000 | 0.0 | 14.90 | 1.129 | True |
| UNIFORM_2 | 1000000 | STATIC | 1 | 30 | 3.7999 | 3.7714 | 3.9840 | 0.777 | [0.655, 0.814] | 0.777 | 28.7 | 11.58 | 0.877 | True |

Traffic model for GB/s: 12 B per stored entry, 4 B per row pointer, 8 B for x and 8 B for y per row (x assumed streamed once). `bw eff` divides it by the best STREAM-like triad measured at the same or the nearest lower parallelism.

> **Note:** bw eff above 1.0 means the working set (matrix + vectors) is at least partly cache resident, so the DRAM triad ceiling does not apply to that row; read bandwidth efficiency only at sizes well above the last-level cache (7M rows and above).

## Skipped configurations

| item | reason |
|---|---|
| p=2 | requires 2 cores but the JVM sees 1; skipped to avoid oversubscription |
| p=4 | requires 4 cores but the JVM sees 1; skipped to avoid oversubscription |

