# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-21T20:20:51.065705+00:00`
- Status: **PASS**
- Qubits: `4`
- Hilbert dimension: `16`
- Basis order: `big-endian`
- Operator order: `U = C3X @ U_rot`
- Warmups per operation: `5`
- Measured repetitions: `30`
- Timer: `time.perf_counter_ns`
- Numerical tolerance: `1.000e-12`
- Total benchmark runtime: **0.068827 seconds**
- Total production execution time: **0.025261104 seconds**
- Total independent execution time: **0.006110884 seconds**
- Total timed execution time (both implementations): **0.031371988 seconds**
- Initial evidence-generation time: **0.001844 seconds**
- Runtime measurement scope: Elapsed wall-clock time from benchmark CLI start, before configuration loading, through the first complete generation of the four evidence files. Final JSON and Markdown persistence of the measured duration is excluded to avoid a self-referential timing measurement.

## Numerical parity

PennyLane / independent NumPy state difference: `0.000000e+00`

## Paired operation measurements

| Operation | Production median (ns) | Independent median (ns) | Production reduction (%) | Paired median difference (ns) | Production wins (%) | World record |
|---|---:|---:|---:|---:|---:|---|
| rotation_operator | 48042.50 | 41021.50 | -17.115 | -7571.00 | 6.67 | N/A — no verified directly comparable record |
| c3x_operator | 1201.50 | 1226.50 | 2.038 | 30.00 | 53.33 | N/A — no verified directly comparable record |
| transition_operator | 50521.00 | 43045.00 | -17.368 | -7461.00 | 0.00 | N/A — no verified directly comparable record |
| state_evolution | 51328.00 | 43806.00 | -17.171 | -7616.50 | 6.67 | N/A — no verified directly comparable record |
| density_matrix | 7531.50 | 1963.00 | -283.673 | -5574.00 | 0.00 | N/A — no verified directly comparable record |
| reduced_density_q4 | 1412.00 | 3926.00 | 64.035 | 2534.00 | 100.00 | N/A — no verified directly comparable record |
| reduced_density_q123 | 1442.00 | 3991.00 | 63.869 | 2529.50 | 100.00 | N/A — no verified directly comparable record |
| pennylane_execution | 669744.50 | 62654.00 | -968.957 | -614196.50 | 0.00 | N/A — no verified directly comparable record |

## Full timing statistics

| Operation | Implementation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Samples |
|---|---|---:|---:|---:|---:|---:|---:|
| rotation_operator | production | 46951 | 48042.50 | 50089.50 | 81122 | 6273.56 | 30 |
| rotation_operator | independent | 39910 | 41021.50 | 42490.40 | 60371 | 4811.88 | 30 |
| c3x_operator | production | 1131 | 1201.50 | 1243.20 | 1813 | 136.56 | 30 |
| c3x_operator | independent | 1132 | 1226.50 | 1714.23 | 14662 | 2412.10 | 30 |
| transition_operator | production | 49945 | 50521.00 | 51253.90 | 60100 | 2192.20 | 30 |
| transition_operator | independent | 42554 | 43045.00 | 43643.47 | 49435 | 1549.43 | 30 |
| state_evolution | production | 50576 | 51328.00 | 52244.17 | 67161 | 3073.03 | 30 |
| state_evolution | independent | 43105 | 43806.00 | 44822.17 | 59790 | 3406.61 | 30 |
| density_matrix | production | 7291 | 7531.50 | 8473.10 | 16365 | 2244.77 | 30 |
| density_matrix | independent | 1882 | 1963.00 | 2012.53 | 2835 | 173.83 | 30 |
| reduced_density_q4 | production | 1352 | 1412.00 | 1448.80 | 2123 | 135.24 | 30 |
| reduced_density_q4 | independent | 3846 | 3926.00 | 4113.93 | 6270 | 495.41 | 30 |
| reduced_density_q123 | production | 1392 | 1442.00 | 1474.83 | 1963 | 102.99 | 30 |
| reduced_density_q123 | independent | 3866 | 3991.00 | 3999.67 | 4166 | 78.80 | 30 |
| pennylane_execution | production | 630440 | 669744.50 | 675809.30 | 786787 | 30931.26 | 30 |
| pennylane_execution | independent | 49094 | 62654.00 | 60899.73 | 87732 | 10630.86 | 30 |

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
