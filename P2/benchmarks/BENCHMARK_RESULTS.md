# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-20T17:16:30.612523+00:00`
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

| Operation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Error | Check |
|---|---:|---:|---:|---:|---:|---:|---|
| rotation_operator | 61464 | 65081.00 | 67020.67 | 91861 | 6542.65 | 0.000e+00 | PASS |
| c3x_operator | 1324 | 1487.00 | 1523.77 | 2379 | 186.96 | 0.000e+00 | PASS |
| transition_operator | 62716 | 65558.50 | 68021.17 | 94931 | 7835.12 | 0.000e+00 | PASS |
| state_evolution | 64535 | 70036.00 | 74198.63 | 109739 | 12034.21 | 0.000e+00 | PASS |
| density_matrix | 8358 | 9050.50 | 9658.90 | 17068 | 1901.70 | 0.000e+00 | PASS |
| reduced_density_q4 | 1371 | 1508.50 | 1570.60 | 3045 | 294.78 | 0.000e+00 | PASS |
| reduced_density_q123 | 1499 | 1609.00 | 1664.47 | 2583 | 196.11 | 1.069e-16 | PASS |
| pennylane_execution | 740714 | 780155.00 | 790970.50 | 929097 | 39279.47 | 0.000e+00 | PASS |

## Methodology

- Five or more warm-up iterations are performed per operation.
- At least 30 measured repetitions are collected per operation.
- Timing uses `time.perf_counter_ns()`.
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
