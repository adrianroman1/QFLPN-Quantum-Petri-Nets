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
| Minimum (ms) | 0.113170 | 0.096810 | — |
| Median (ms) | **0.119382** | 0.100752 | **0.843946×** (reference / P1) |
| Mean (ms) | 0.123829 | 0.107410 | — |
| Maximum (ms) | 0.163264 | 0.161540 | — |
| Standard deviation (ms) | 0.013822 | 0.017992 | — |
| Samples | 30 | 30 | — |

## Comparative indicators

- Independent / production median-time ratio: **0.843946×**
- Median-time difference (independent − production): **-0.018630 ms**
- Production median-time reduction relative to the independent reference: **-18.491%**

A ratio above 1 means the independent reference had a greater
median execution time than P1 in this measured run.

This is a relative runtime comparison, not a quantum speedup
or an HPC scalability result.

## Reproducibility

- Timestamp (UTC): `2026-10-20T03:34:52.214632+00:00`
- Git commit: `667312916eca4057977ac61dcc1b06756d77e9f5`
- Python: `3.11.17`
- NumPy: `2.3.5`
- SciPy: `1.17.0`
- Platform: `Linux-7.0.0-1017-azure-x86_64-with-glibc2.39`
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
