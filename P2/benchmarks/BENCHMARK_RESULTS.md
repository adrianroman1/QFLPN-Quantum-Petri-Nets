# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-20T17:55:58.460094+00:00`
- Status: **PASS**
- Qubits: `4`
- Hilbert dimension: `16`
- Basis order: `big-endian`
- Operator order: `U = C3X @ U_rot`
- Warmups per operation: `5`
- Measured repetitions: `30`
- Timer: `time.perf_counter_ns`
- Numerical tolerance: `1.000e-12`
- Total benchmark runtime: **0.098942 seconds**
- Runtime measurement scope: Elapsed wall-clock time from benchmark CLI start, before configuration loading, through the first complete generation of the four evidence files. Final JSON and Markdown persistence of the measured duration is excluded to avoid a self-referential timing measurement.

## Numerical parity

PennyLane / independent NumPy state difference: `0.000000e+00`

## Operation measurements

| Operation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Throughput (ops/s) | Error | Check |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| rotation_operator | 99926 | 107114.50 | 118240.27 | 195023 | 23588.84 | 9335.804210 | 0.000e+00 | PASS |
| c3x_operator | 2344 | 2464.50 | 2736.47 | 6061 | 804.04 | 405761.817813 | 0.000e+00 | PASS |
| transition_operator | 110546 | 114327.50 | 119606.83 | 154317 | 12104.49 | 8746.801951 | 0.000e+00 | PASS |
| state_evolution | 112940 | 116431.00 | 119952.93 | 144128 | 7995.84 | 8588.777903 | 0.000e+00 | PASS |
| density_matrix | 17352 | 18129.00 | 19725.63 | 39143 | 4327.06 | 55160.240499 | 0.000e+00 | PASS |
| reduced_density_q4 | 2685 | 2770.00 | 3018.27 | 4999 | 570.08 | 361010.830325 | 0.000e+00 | PASS |
| reduced_density_q123 | 2816 | 2910.00 | 3139.33 | 5140 | 546.67 | 343642.611684 | 1.069e-16 | PASS |
| pennylane_execution | 1320335 | 1354839.00 | 1367460.87 | 1609813 | 56956.55 | 738.095080 | 0.000e+00 | PASS |

## Methodology

- Five or more warm-up iterations are performed per operation.
- At least 30 measured repetitions are collected per operation.
- Timing uses `time.perf_counter_ns()`.
- Throughput is calculated as 1e9 divided by median nanoseconds.
- Total runtime is measured separately from individual operation timings.
- The total runtime includes configuration loading, initialization, operation measurements and the first complete generation of all four evidence files.
- Final JSON and Markdown persistence of the runtime field is excluded from the measured interval.
- Numerical references are constructed independently of the timed production callables.
- PennyLane state evolution is compared with the independent NumPy state.
- All numerical comparisons use the configured absolute norm tolerance.

## Interpretation and limitations

These measurements describe the canonical four-qubit P2 workload only.
They do not establish asymptotic scalability or performance for larger quantum systems.
Execution times depend on the processor, operating system, Python runtime, installed packages and virtual-machine load.
Benchmark timings are supplementary performance evidence and do not independently establish mathematical acceptance.

## Generated evidence

- `benchmark_report.json` — structured measurements and metadata.
- `benchmark_results.csv` — operation-level measurements.
- `environment.txt` — execution environment.

**Overall numerical status: PASS**
