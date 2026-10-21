# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-21T20:18:26.490077+00:00`
- Status: **PASS**
- Qubits: `4`
- Hilbert dimension: `16`
- Basis order: `big-endian`
- Operator order: `U = C3X @ U_rot`
- Warmups per operation: `5`
- Measured repetitions: `30`
- Timer: `time.perf_counter_ns`
- Numerical tolerance: `1.000e-12`
- Total benchmark runtime: **0.123776 seconds**
- Total production execution time: **0.054165350 seconds**
- Total independent execution time: **0.014280261 seconds**
- Total timed execution time (both implementations): **0.068445611 seconds**
- Initial evidence-generation time: **0.002763 seconds**
- Runtime measurement scope: Elapsed wall-clock time from benchmark CLI start, before configuration loading, through the first complete generation of the four evidence files. Final JSON and Markdown persistence of the measured duration is excluded to avoid a self-referential timing measurement.

## Numerical parity

PennyLane / independent NumPy state difference: `0.000000e+00`

## Paired operation measurements

| Operation | Production median (ns) | Independent median (ns) | Production reduction (%) | Paired median difference (ns) | Production wins (%) | World record |
|---|---:|---:|---:|---:|---:|---|
| rotation_operator | 108447.00 | 91676.00 | -18.294 | -15939.00 | 6.67 | N/A — no verified directly comparable record |
| c3x_operator | 2615.00 | 2650.00 | 1.321 | 85.00 | 50.00 | N/A — no verified directly comparable record |
| transition_operator | 118110.00 | 102936.50 | -14.741 | -13956.00 | 20.00 | N/A — no verified directly comparable record |
| state_evolution | 121191.00 | 103743.50 | -16.818 | -15829.50 | 13.33 | N/A — no verified directly comparable record |
| density_matrix | 19892.00 | 4409.00 | -351.168 | -15363.00 | 0.00 | N/A — no verified directly comparable record |
| reduced_density_q4 | 3626.50 | 9252.00 | 60.803 | 5669.50 | 100.00 | N/A — no verified directly comparable record |
| reduced_density_q123 | 3717.00 | 8966.00 | 58.543 | 5290.00 | 100.00 | N/A — no verified directly comparable record |
| pennylane_execution | 1397223.50 | 138472.50 | -909.026 | -1263258.50 | 0.00 | N/A — no verified directly comparable record |

## Full timing statistics

| Operation | Implementation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Samples |
|---|---|---:|---:|---:|---:|---:|---:|
| rotation_operator | production | 103573 | 108447.00 | 115205.37 | 167402 | 15749.40 | 30 |
| rotation_operator | independent | 86241 | 91676.00 | 93559.77 | 123300 | 8112.13 | 30 |
| c3x_operator | production | 2155 | 2615.00 | 2679.43 | 4629 | 519.24 | 30 |
| c3x_operator | independent | 2154 | 2650.00 | 2687.27 | 4909 | 536.31 | 30 |
| transition_operator | production | 112069 | 118110.00 | 121377.47 | 158035 | 11091.67 | 30 |
| transition_operator | independent | 96018 | 102936.50 | 110721.60 | 177972 | 19233.14 | 30 |
| state_evolution | production | 115456 | 121191.00 | 124284.03 | 153907 | 10384.99 | 30 |
| state_evolution | independent | 98644 | 103743.50 | 109293.13 | 166951 | 14662.56 | 30 |
| density_matrix | production | 18475 | 19892.00 | 21441.30 | 45475 | 4991.17 | 30 |
| density_matrix | independent | 4048 | 4409.00 | 4475.10 | 5891 | 351.89 | 30 |
| reduced_density_q4 | production | 3316 | 3626.50 | 3855.97 | 6983 | 707.83 | 30 |
| reduced_density_q4 | independent | 8576 | 9252.00 | 9789.20 | 13946 | 1358.44 | 30 |
| reduced_density_q123 | production | 3477 | 3717.00 | 3881.23 | 5530 | 467.87 | 30 |
| reduced_density_q123 | independent | 8276 | 8966.00 | 10008.23 | 33532 | 4406.87 | 30 |
| pennylane_execution | production | 1355757 | 1397223.50 | 1412786.87 | 1631149 | 54620.58 | 30 |
| pennylane_execution | independent | 119973 | 138472.50 | 135474.40 | 170959 | 13629.06 | 30 |

## Paired comparison interpretation

- Positive median difference means the independent implementation took longer.
- Production win rate is the fraction of paired samples where production was faster.
- Ties are reported separately and are not counted as production wins.
- The median ratio is independent median divided by production median.
- Production reduction is measured relative to the independent median.
- Execution order alternates between paired samples.
- Numerical validation is performed after each timed call.
- Both implementations must pass the configured absolute norm tolerance.

## World-record and literature comparison

No universal world-record registry exists for the exact P2 operation-level workload.
A published timing is accepted as a directly comparable record only when operation semantics, qubit count, numerical precision, hardware, software and measurement boundaries match.

| Literature source | Published scope | P2 status |
|---|---|---|
| [BENCHPRESS-2025](https://doi.org/10.1038/s43588-025-00792-y) | Benchpress suite with more than 1000 tests and circuits up to 930 qubits. | Methodological reference only. Not an equivalent four-qubit operation-level timing record. |
| [STATEVECTOR-HPC-2026](https://doi.org/10.1177/00375497261438515) | Seven statevector simulators, circuits from 3 to 30 qubits, runtime, memory and multicore scalability. | External simulator landscape. Hardware, circuits and measurement scope are not identical to P2. |

## Methodology

- At least five warm-up iterations per implementation and operation.
- At least 30 paired measured repetitions per operation.
- Timing uses `time.perf_counter_ns()`.
- Execution order alternates within each pair.
- Production and independent outputs are checked against the independent reference.
- Both implementations must pass the configured absolute norm tolerance.
- Production and independent statistics are computed separately.
- Total operation execution times are sums of measured call durations.
- Total benchmark runtime is measured separately and includes setup and initial evidence generation.
- The final persistence of the runtime field is excluded from the runtime interval.

## Interpretation and limitations

These measurements describe the canonical four-qubit P2 workload only.
The Hilbert-space dimension is 16.
They do not establish asymptotic scalability or performance for larger quantum systems.
They do not establish million-qubit, distributed or HPC performance.
A faster result in this benchmark is not evidence of quantum speedup.
Execution times depend on the processor, operating system, Python runtime, installed packages and system load.
Literature studies with different circuits and hardware are contextual references, not equivalent records.

## Generated evidence

- `benchmark_report.json` — structured paired measurements and metadata.
- `benchmark_results.csv` — production operation summary.
- `environment.txt` — execution environment.

**Overall numerical status: PASS**
