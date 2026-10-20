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
| Minimum (ms) | 0.046951 | 0.056886 | — |
| Median (ms) | **0.047967** | 0.057727 | **1.203473×** (reference / P1) |
| Mean (ms) | 0.051006 | 0.058036 | — |
| Maximum (ms) | 0.094713 | 0.065608 | — |
| Standard deviation (ms) | 0.010660 | 0.001590 | — |
| Samples | 30 | 30 | — |

## Paired comparison

- Median paired difference (independent − production): **0.009695 ms**
- Production wins among paired measurements: **93.33%**
- Number of paired measurements: **30**

A positive paired difference means production was faster in that pair.
A production win rate above 50% means production was faster in more than
half of the measured pairs. These statistics describe this execution only.

## Comparative indicators

- Independent / production median-time ratio: **1.203473×**
- Median-time difference (independent − production): **0.009760 ms**
- Production median-time reduction relative to the independent reference:
  **16.907%**

A ratio above 1 means the independent reference had a greater
median execution time than P1 in this measured run.

This is a relative runtime comparison, not a quantum speedup
or an HPC scalability result.

## Reproducibility

- Timestamp (UTC): `2026-10-20T16:02:14.241954+00:00`
- Git commit: `266c7991dd2697820241a813b679be9feb1332a8`
- Python: `3.11.17`
- NumPy: `2.3.5`
- SciPy: `1.17.0`
- Platform: `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39`
- CPU: `AMD EPYC 9V45 96-Core Processor`

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
