# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-20T17:15:41.944616+00:00`
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
| rotation_operator | 102632 | 106474.00 | 109866.77 | 141665 | 9228.91 | 0.000e+00 | PASS |
| c3x_operator | 2424 | 2579.50 | 2731.40 | 5450 | 563.44 | 0.000e+00 | PASS |
| transition_operator | 113332 | 117254.50 | 121751.30 | 154960 | 9941.50 | 0.000e+00 | PASS |
| state_evolution | 116428 | 119037.50 | 123468.80 | 163145 | 10346.09 | 0.000e+00 | PASS |
| density_matrix | 17262 | 17939.00 | 18767.43 | 27482 | 2244.41 | 0.000e+00 | PASS |
| reduced_density_q4 | 2675 | 2760.50 | 3061.07 | 6011 | 835.63 | 0.000e+00 | PASS |
| reduced_density_q123 | 2805 | 2890.00 | 3022.63 | 4499 | 365.94 | 1.069e-16 | PASS |
| pennylane_execution | 1347310 | 1379760.00 | 1389127.90 | 1560227 | 38306.11 | 0.000e+00 | PASS |

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
