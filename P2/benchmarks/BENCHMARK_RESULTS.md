# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-20T17:43:57.422243+00:00`
- Status: **PASS**
- Qubits: `4`
- Hilbert dimension: `16`
- Basis order: `big-endian`
- Operator order: `U = C3X @ U_rot`
- Warmups per operation: `5`
- Measured repetitions: `30`
- Timer: `time.perf_counter_ns`
- Numerical tolerance: `1.000e-12`

## Numerical parity

PennyLane / independent NumPy state difference: `0.000000e+00`

## Operation measurements

| Operation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Throughput (ops/s) | Error | Check |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| rotation_operator | 46801 | 47257.00 | 48568.00 | 72359 | 4692.50 | 21160.886218 | 0.000e+00 | PASS |
| c3x_operator | 1091 | 1161.50 | 1217.13 | 1903 | 165.37 | 860955.660783 | 0.000e+00 | PASS |
| transition_operator | 49555 | 50275.50 | 51454.30 | 60762 | 2995.60 | 19890.403875 | 0.000e+00 | PASS |
| state_evolution | 50937 | 51347.00 | 52486.20 | 70736 | 3765.60 | 19475.334489 | 0.000e+00 | PASS |
| density_matrix | 7131 | 7406.00 | 8066.83 | 14872 | 1743.13 | 135025.654874 | 0.000e+00 | PASS |
| reduced_density_q4 | 1332 | 1377.00 | 1444.10 | 2313 | 186.33 | 726216.412491 | 0.000e+00 | PASS |
| reduced_density_q123 | 1372 | 1417.50 | 1463.50 | 2133 | 138.40 | 705467.372134 | 1.069e-16 | PASS |
| pennylane_execution | 600396 | 627927.50 | 635616.63 | 772536 | 31584.33 | 1592.540540 | 0.000e+00 | PASS |

## Methodology

- Five or more warm-up iterations are performed per operation.
- At least 30 measured repetitions are collected per operation.
- Timing uses `time.perf_counter_ns()`.
- Throughput is calculated as 1e9 divided by median nanoseconds.
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
