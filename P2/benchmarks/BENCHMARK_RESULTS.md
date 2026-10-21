# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-21T20:34:55.816487+00:00`
- Status: **PASS**
- Qubits: `4`
- Hilbert dimension: `16`
- Basis order: `big-endian`
- Operator order: `U = C3X @ U_rot`
- Warmups per operation: `5`
- Measured repetitions: `30`
- Timer: `time.perf_counter_ns`
- Numerical tolerance: `1.000e-12`
- Total benchmark runtime: **0.069886 seconds**
- Total production execution time: **0.026291423 seconds**
- Total independent execution time: **0.006388489 seconds**
- Total timed execution time (both implementations): **0.032679912 seconds**
- Initial evidence-generation time: **0.002365 seconds**
- Runtime measurement scope: Elapsed wall-clock time from benchmark CLI start, before configuration loading, through the first complete generation of the four evidence files. Final JSON and Markdown persistence of the measured duration is excluded to avoid a self-referential timing measurement.

## Numerical parity

PennyLane / independent NumPy state difference: `0.000000e+00`

## Paired operation measurements

| Operation | Production median (ns) | Independent median (ns) | Production reduction (%) | Paired median difference (ns) | Production wins (%) | World record |
|---|---:|---:|---:|---:|---:|---|
| rotation_operator | 51303.00 | 43270.00 | -18.565 | -7847.00 | 3.33 | N/A — no verified directly comparable record |
| c3x_operator | 1262.00 | 1312.00 | 3.811 | 14.50 | 53.33 | N/A — no verified directly comparable record |
| transition_operator | 54197.00 | 46185.00 | -17.348 | -7947.50 | 0.00 | N/A — no verified directly comparable record |
| state_evolution | 55539.00 | 47477.00 | -16.981 | -8107.50 | 6.67 | N/A — no verified directly comparable record |
| density_matrix | 8027.00 | 2088.00 | -284.435 | -5954.00 | 0.00 | N/A — no verified directly comparable record |
| reduced_density_q4 | 1562.50 | 4301.50 | 63.675 | 2753.50 | 100.00 | N/A — no verified directly comparable record |
| reduced_density_q123 | 1562.50 | 4266.50 | 63.377 | 2674.00 | 100.00 | N/A — no verified directly comparable record |
| pennylane_execution | 686924.00 | 59935.50 | -1046.105 | -629743.00 | 0.00 | N/A — no verified directly comparable record |

## Full timing statistics

| Operation | Implementation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Samples |
|---|---|---:|---:|---:|---:|---:|---:|
| rotation_operator | production | 50216 | 51303.00 | 52649.60 | 68814 | 4207.91 | 30 |
| rotation_operator | independent | 42464 | 43270.00 | 44053.93 | 55735 | 2478.48 | 30 |
| c3x_operator | production | 1201 | 1262.00 | 1310.97 | 1752 | 124.76 | 30 |
| c3x_operator | independent | 1202 | 1312.00 | 1339.93 | 2243 | 186.40 | 30 |
| transition_operator | production | 53311 | 54197.00 | 55331.10 | 68764 | 3477.21 | 30 |
| transition_operator | independent | 45589 | 46185.00 | 46600.23 | 50937 | 1137.21 | 30 |
| state_evolution | production | 54483 | 55539.00 | 56807.57 | 72940 | 4231.51 | 30 |
| state_evolution | independent | 46961 | 47477.00 | 48902.67 | 66220 | 4622.75 | 30 |
| density_matrix | production | 7802 | 8027.00 | 8568.27 | 13371 | 1227.84 | 30 |
| density_matrix | independent | 2003 | 2088.00 | 2156.37 | 3035 | 202.88 | 30 |
| reduced_density_q4 | production | 1462 | 1562.50 | 1598.53 | 2383 | 168.07 | 30 |
| reduced_density_q4 | independent | 4156 | 4301.50 | 4513.53 | 6049 | 530.36 | 30 |
| reduced_density_q123 | production | 1512 | 1562.50 | 1627.80 | 2503 | 181.14 | 30 |
| reduced_density_q123 | independent | 4107 | 4266.50 | 4287.53 | 4627 | 114.49 | 30 |
| pennylane_execution | production | 659057 | 686924.00 | 698486.93 | 856195 | 37013.35 | 30 |
| pennylane_execution | independent | 51759 | 59935.50 | 61095.43 | 81603 | 8523.55 | 30 |

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
