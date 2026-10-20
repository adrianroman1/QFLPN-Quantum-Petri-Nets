# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-20T18:33:46.528928+00:00`
- Status: **PASS**
- Qubits: `4`
- Hilbert dimension: `16`
- Basis order: `big-endian`
- Operator order: `U = C3X @ U_rot`
- Warmups per operation: `5`
- Measured repetitions: `30`
- Timer: `time.perf_counter_ns`
- Numerical tolerance: `1.000e-12`
- Total benchmark runtime: **0.156775 seconds**
- Total production execution time: **0.067144820 seconds**
- Total independent execution time: **0.022321834 seconds**
- Total timed execution time (both implementations): **0.089466654 seconds**
- Initial evidence-generation time: **0.003116 seconds**
- Runtime measurement scope: Elapsed wall-clock time from benchmark CLI start, before configuration loading, through the first complete generation of the four evidence files. Final JSON and Markdown persistence of the measured duration is excluded to avoid a self-referential timing measurement.

## Numerical parity

PennyLane / independent NumPy state difference: `0.000000e+00`

## Paired operation measurements

| Operation | Production median (ns) | Independent median (ns) | Production reduction (%) | Paired median difference (ns) | Production wins (%) | World record |
|---|---:|---:|---:|---:|---:|---|
| rotation_operator | 219456.50 | 180508.00 | -21.577 | -29335.00 | 13.33 | N/A — no verified directly comparable record |
| c3x_operator | 2745.00 | 2735.00 | -0.366 | 0.00 | 50.00 | N/A — no verified directly comparable record |
| transition_operator | 239599.00 | 199288.50 | -20.227 | -40250.50 | 10.00 | N/A — no verified directly comparable record |
| state_evolution | 241808.00 | 204713.50 | -18.120 | -32395.50 | 10.00 | N/A — no verified directly comparable record |
| density_matrix | 39885.00 | 8496.00 | -369.456 | -31323.00 | 0.00 | N/A — no verified directly comparable record |
| reduced_density_q4 | 4203.00 | 10910.50 | 61.477 | 6692.50 | 93.33 | N/A — no verified directly comparable record |
| reduced_density_q123 | 6141.00 | 15599.00 | 60.632 | 9733.50 | 100.00 | N/A — no verified directly comparable record |
| pennylane_execution | 1460846.00 | 141800.50 | -930.212 | -1316701.00 | 0.00 | N/A — no verified directly comparable record |

## Full timing statistics

| Operation | Implementation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Samples |
|---|---|---:|---:|---:|---:|---:|---:|
| rotation_operator | production | 106289 | 219456.50 | 198397.37 | 255559 | 43953.65 | 30 |
| rotation_operator | independent | 88005 | 180508.00 | 169766.27 | 241292 | 40732.56 | 30 |
| c3x_operator | production | 2204 | 2745.00 | 2765.27 | 4799 | 583.67 | 30 |
| c3x_operator | independent | 2124 | 2735.00 | 2830.83 | 5711 | 841.22 | 30 |
| transition_operator | production | 118652 | 239599.00 | 232078.67 | 293630 | 51393.84 | 30 |
| transition_operator | independent | 99767 | 199288.50 | 190428.97 | 232796 | 31158.28 | 30 |
| state_evolution | production | 122960 | 241808.00 | 229443.43 | 280175 | 45726.91 | 30 |
| state_evolution | independent | 101340 | 204713.50 | 197762.73 | 246271 | 35694.05 | 30 |
| density_matrix | production | 29165 | 39885.00 | 41332.10 | 67867 | 7714.98 | 30 |
| density_matrix | independent | 6202 | 8496.00 | 9341.23 | 35517 | 4987.13 | 30 |
| reduced_density_q4 | production | 3196 | 4203.00 | 7162.07 | 33734 | 6659.56 | 30 |
| reduced_density_q4 | independent | 9017 | 10910.50 | 14891.63 | 25047 | 5706.07 | 30 |
| reduced_density_q123 | production | 3367 | 6141.00 | 6275.93 | 10369 | 2234.41 | 30 |
| reduced_density_q123 | independent | 8956 | 15599.00 | 15619.10 | 23975 | 5049.72 | 30 |
| pennylane_execution | production | 1385835 | 1460846.00 | 1520705.83 | 1927490 | 140542.08 | 30 |
| pennylane_execution | independent | 122479 | 141800.50 | 143420.37 | 190868 | 19739.12 | 30 |

## Paired comparison interpretation

- Positive median difference means the independent implementation took longer.
- Production win rate is the fraction of paired samples where production was faster.
- Ties are reported separately and are not counted as production wins.
- The median ratio is independent median divided by production median.
- Production reduction is measured relative to the independent median.
- Execution order alternates between paired samples.
- Numerical validation is performed after each timed call.

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
