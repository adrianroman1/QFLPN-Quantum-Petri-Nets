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

| Metric | Production implementation | Independent implementation |
|---|---:|---:|
| Minimum (ms) | 0.047301 | 0.057447 |
| Median (ms) | 0.047923 | 0.058218 |
| Mean (ms) | 0.049608 | 0.060762 |
| Maximum (ms) | 0.077727 | 0.108313 |
| Standard deviation (ms) | 0.005632 | 0.009395 |
| Samples | 30 | 30 |

## Relative execution time

- Independent / production median-time ratio: **1.214836×**
- Interpretation: values above 1 indicate that the production implementation
  had a lower median time in this measured run. Values below 1 indicate the
  opposite.

## Reproducibility

- Timestamp (UTC): `2026-10-20T03:13:31.968780+00:00`
- Git commit: `c15aa65f8267eebd70e1d1a6db4e4d9965f3ef59`
- Python: `3.11.17`
- NumPy: `2.3.5`
- SciPy: `1.17.0`
- Platform: `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39`
- CPU: `AMD EPYC 9V45 96-Core Processor`

Raw samples are stored in `benchmark_results.csv`.
Structured results are stored in `benchmark_report.json`.
The captured environment is stored in `environment.txt`.

## Interpretation and limitations

This benchmark measures construction of the **canonical four-qubit P1
operator only**. It is not a benchmark of a scalable quantum simulator,
a million-qubit system, a distributed implementation, or an HPC workload.
The ratio compares two implementations of the same fixed-size operation;
it must not be interpreted as an asymptotic complexity result.

The measurements are machine- and environment-dependent. They are evidence
for this execution only, not a universal performance guarantee.
