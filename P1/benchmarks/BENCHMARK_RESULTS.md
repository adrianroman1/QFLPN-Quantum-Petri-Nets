# P1 Benchmark Results

## Scope

- Canonical register: **q = 4 qubits**
- Hilbert-space dimension: **D = 16**
- Operation: global QFLPN transition-operator construction
- Samples per implementation: **30**
- Warm-up iterations: **5**
- Measurement order: **balanced_alternating_paired_measurements**
- Timer: `time.perf_counter_ns()`
- Numerical equivalence: **PASS**
- Frobenius difference: `0.000000e+00`
- Tolerance: `1.0e-12`

## Measured execution times

| Metric | Production implementation | Independent implementation | Comparative indicator |
|---|---:|---:|---:|
| Minimum (ms) | 0.079799 | 0.096130 | — |
| Median (ms) | **0.081743** | 0.101536 | **1.242131×** (reference / P1) |
| Mean (ms) | 0.088288 | 0.106188 | — |
| Maximum (ms) | 0.146304 | 0.185017 | — |
| Standard deviation (ms) | 0.015833 | 0.016720 | — |
| Samples | 30 | 30 | — |

## Paired comparison

- Median paired difference (independent − production): **0.017433 ms**
- Production wins among paired measurements: **90.00%**
- Number of paired measurements: **30**

A positive paired difference means production was faster in that pair.
A production win rate above 50% means production was faster in more than
half of the measured pairs. These statistics describe this execution only.

## Comparative indicators

- Independent / production median-time ratio: **1.242131×**
- Median-time difference (independent − production): **0.019793 ms**
- Production median-time reduction relative to the independent reference:
  **19.493%**

A ratio above 1 means the independent reference had a greater
median execution time than P1 in this measured run.

This is a relative runtime comparison, not a quantum speedup
or an HPC scalability result.

## Reproducibility

- Timestamp (UTC): `2026-10-20T16:37:17.743639+00:00`
- Git commit: `42fb8289c9eeca8b9ff868dbf24619771418e355`
- Python: `3.11.17`
- NumPy: `2.3.5`
- SciPy: `1.17.0`
- Platform: `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39`
- CPU: `AMD EPYC 7763 64-Core Processor`

Raw paired samples are stored in `benchmark_results.csv`.
Structured results are stored in `benchmark_report.json`.
The captured environment is stored in `environment.txt`.

## Interpretation and limitations

This benchmark measures construction of the **canonical four-qubit P1
operator only**. It is not a benchmark of a scalable quantum simulator,
a million-qubit system, a distributed implementation, or an HPC workload.

The ratio compares two implementations of the same fixed-size operation;
it must not be interpreted as an asymptotic complexity result.

Alternating measurement order reduces systematic order bias but does not
eliminate virtual-machine contention, CPU-frequency variation, or other
environmental noise.

The measurements are machine- and environment-dependent.
They are evidence for this execution only, not a universal performance guarantee.
