# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-21T20:52:50.547029+00:00`
- Status: **PASS**
- Qubits: `4`
- Hilbert dimension: `16`
- Basis order: `big-endian`
- Operator order: `U = C3X @ U_rot`
- Warmups per operation: `5`
- Measured repetitions: `30`
- Timer: `time.perf_counter_ns`
- Numerical tolerance: `1.000e-12`
- Total benchmark runtime: **0.320453 seconds**
- Total production execution time: **0.035417622 seconds**
- Total independent execution time: **0.008858840 seconds**
- Total timed execution time (both implementations): **0.044276462 seconds**
- Initial evidence-generation time: **0.164429 seconds**
- Runtime measurement scope: Elapsed wall-clock time from benchmark CLI start, before configuration loading, through the first complete generation of the four evidence files. Final JSON and Markdown persistence of the measured duration is excluded to avoid a self-referential timing measurement.

## Numerical parity

PennyLane / independent NumPy state difference: `0.000000e+00`

## Paired operation measurements

| Operation | Production median (ns) | Independent median (ns) | Production reduction (%) | Paired median difference (ns) | Production wins (%) | World record |
|---|---:|---:|---:|---:|---:|---|
| rotation_operator | 67772.50 | 58118.00 | -16.612 | -9354.50 | 10.00 | N/A — no verified directly comparable record |
| c3x_operator | 1807.50 | 1823.00 | 0.850 | 20.50 | 53.33 | N/A — no verified directly comparable record |
| transition_operator | 72019.00 | 62684.50 | -14.891 | -9294.00 | 3.33 | N/A — no verified directly comparable record |
| state_evolution | 73982.00 | 64512.50 | -14.679 | -9649.00 | 6.67 | N/A — no verified directly comparable record |
| density_matrix | 11066.50 | 2844.00 | -289.117 | -8217.50 | 0.00 | N/A — no verified directly comparable record |
| reduced_density_q4 | 2088.00 | 5869.00 | 64.423 | 3780.00 | 96.67 | N/A — no verified directly comparable record |
| reduced_density_q123 | 2113.00 | 5779.00 | 63.437 | 3650.00 | 100.00 | N/A — no verified directly comparable record |
| pennylane_execution | 936430.00 | 92760.00 | -909.519 | -852388.00 | 0.00 | N/A — no verified directly comparable record |

## Full timing statistics

| Operation | Implementation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Samples |
|---|---|---:|---:|---:|---:|---:|---:|
| rotation_operator | production | 65939 | 67772.50 | 70087.63 | 105279 | 7816.71 | 30 |
| rotation_operator | independent | 56445 | 58118.00 | 60880.33 | 82845 | 6841.24 | 30 |
| c3x_operator | production | 1693 | 1807.50 | 1858.17 | 2484 | 194.20 | 30 |
| c3x_operator | independent | 1643 | 1823.00 | 1872.30 | 3175 | 272.11 | 30 |
| transition_operator | production | 70817 | 72019.00 | 73000.03 | 90577 | 3457.78 | 30 |
| transition_operator | independent | 61403 | 62684.50 | 63778.37 | 77858 | 3333.42 | 30 |
| state_evolution | production | 72249 | 73982.00 | 75286.20 | 87172 | 3310.76 | 30 |
| state_evolution | independent | 63206 | 64512.50 | 65390.53 | 78048 | 3344.64 | 30 |
| density_matrix | production | 10736 | 11066.50 | 11680.93 | 17056 | 1444.32 | 30 |
| density_matrix | independent | 2714 | 2844.00 | 2917.47 | 3936 | 236.67 | 30 |
| reduced_density_q4 | production | 1973 | 2088.00 | 2494.80 | 13280 | 2009.10 | 30 |
| reduced_density_q4 | independent | 5669 | 5869.00 | 6146.73 | 10156 | 903.71 | 30 |
| reduced_density_q123 | production | 2053 | 2113.00 | 2195.67 | 3084 | 231.80 | 30 |
| reduced_density_q123 | independent | 5649 | 5779.00 | 5844.73 | 6339 | 164.83 | 30 |
| pennylane_execution | production | 900841 | 936430.00 | 943983.97 | 1046662 | 30424.53 | 30 |
| pennylane_execution | independent | 74843 | 92760.00 | 88464.20 | 113471 | 11959.21 | 30 |

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
