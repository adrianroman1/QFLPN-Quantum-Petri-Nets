# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-20T17:41:08.637392+00:00`
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
| rotation_operator | 102919 | 106827.50 | 113645.57 | 157530 | 16707.62 | 0.000e+00 | PASS |
| c3x_operator | 2435 | 2580.00 | 2722.30 | 4971 | 471.42 | 0.000e+00 | PASS |
| transition_operator | 113721 | 118510.50 | 124836.17 | 174194 | 14099.38 | 0.000e+00 | PASS |
| state_evolution | 114603 | 118796.50 | 124637.80 | 173762 | 15572.54 | 0.000e+00 | PASS |
| density_matrix | 17545 | 18723.00 | 20794.57 | 56384 | 7026.19 | 0.000e+00 | PASS |
| reduced_density_q4 | 2676 | 2816.00 | 2965.43 | 5060 | 484.22 | 0.000e+00 | PASS |
| reduced_density_q123 | 2825 | 2951.00 | 3071.93 | 4589 | 381.47 | 1.069e-16 | PASS |
| pennylane_execution | 1341955 | 1378499.50 | 1386352.27 | 1524316 | 40465.91 | 0.000e+00 | PASS |

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
