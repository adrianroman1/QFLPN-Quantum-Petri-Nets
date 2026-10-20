# P1 Benchmark Results

## Scope

- Canonical register: **q = 4 qubits**
- Hilbert-space dimension: **D = 16**
- Operation: global QFLPN transition-operator construction
- Samples per implementation: **30**
- Warm-up iterations: **5**
- Timer: `time.perf_counter_ns()`
- Numerical equivalence: **PASS**
- Frobenius difference: `0.000000e+00`
- Tolerance: `1.0e-12`

## Measured execution times

| Metric | Production implementation | Independent implementation | Comparative indicator |
|---|---:|---:|---:|
| Minimum (ms) | 0.152896 | 0.095699 | — |
| Median (ms) | **0.185652** | 0.189543 | **1.020961×** (reference / P1) |
| Mean (ms) | 0.184993 | 0.172343 | — |
| Maximum (ms) | 0.237473 | 0.292146 | — |
| Standard deviation (ms) | 0.023609 | 0.068176 | — |
| Samples | 30 | 30 | — |

## Comparative indicators

- Independent / production median-time ratio: **1.020961×**
- Median-time difference (independent − production): **0.003891 ms**
- Production median-time reduction relative to the independent reference: **2.053%**

A ratio above 1 means the independent reference had a greater
median execution time than P1 in this measured run.

This is a relative runtime comparison, not a quantum speedup
or an HPC scalability result.

## Reproducibility

- Timestamp (UTC): `2026-10-20T03:33:14.359088+00:00`
- Git commit: `0b6fce8b927c27aae4b50553ef5b637d7abd5880`
- Python: `3.11.17`
- NumPy: `2.3.5`
- SciPy: `1.17.0`
- Platform: `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39`
- CPU: `AMD EPYC 7763 64-Core Processor`

Raw samples are stored in `benchmark_results.csv`.
Structured results are stored in `benchmark_report.json`.
The captured environment is stored in `environment.txt`.

## Interpretation and limitations

This benchmark measures construction of the **canonical four-qubit P1
operator only**. It is not a benchmark of a scalable quantum simulator,
a million-qubit system, a distributed implementation, or an HPC workload.

The ratio compares two implementations of the same fixed-size operation;
it must not be interpreted as an asymptotic complexity result.

The measurements are machine- and environment-dependent.
They are evidence for this execution only, not a universal performance guarantee.
