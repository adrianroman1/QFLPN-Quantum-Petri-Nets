# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-20T18:35:27.521512+00:00`
- Status: **PASS**
- Qubits: `4`
- Hilbert dimension: `16`
- Basis order: `big-endian`
- Operator order: `U = C3X @ U_rot`
- Warmups per operation: `5`
- Measured repetitions: `30`
- Timer: `time.perf_counter_ns`
- Numerical tolerance: `1.000e-12`
- Total benchmark runtime: **0.141668 seconds**
- Total production execution time: **0.056263572 seconds**
- Total independent execution time: **0.016092411 seconds**
- Total timed execution time (both implementations): **0.072355983 seconds**
- Initial evidence-generation time: **0.002765 seconds**
- Runtime measurement scope: Elapsed wall-clock time from benchmark CLI start, before configuration loading, through the first complete generation of the four evidence files. Final JSON and Markdown persistence of the measured duration is excluded to avoid a self-referential timing measurement.

## Numerical parity

PennyLane / independent NumPy state difference: `0.000000e+00`

## Paired operation measurements

| Operation | Production median (ns) | Independent median (ns) | Production reduction (%) | Paired median difference (ns) | Production wins (%) | World record |
|---|---:|---:|---:|---:|---:|---|
| rotation_operator | 152870.50 | 155446.00 | 1.657 | -26319.00 | 20.00 | N/A — no verified directly comparable record |
| c3x_operator | 2845.00 | 2730.00 | -4.212 | 145.00 | 50.00 | N/A — no verified directly comparable record |
| transition_operator | 122233.00 | 104204.50 | -17.301 | -19702.00 | 6.67 | N/A — no verified directly comparable record |
| state_evolution | 124197.00 | 105632.00 | -17.575 | -22276.50 | 10.00 | N/A — no verified directly comparable record |
| density_matrix | 19732.00 | 4593.50 | -329.564 | -15113.00 | 0.00 | N/A — no verified directly comparable record |
| reduced_density_q4 | 3627.00 | 9302.50 | 61.010 | 5791.00 | 100.00 | N/A — no verified directly comparable record |
| reduced_density_q123 | 3702.00 | 9087.00 | 59.260 | 5511.00 | 100.00 | N/A — no verified directly comparable record |
| pennylane_execution | 1391361.50 | 138693.50 | -903.192 | -1253213.50 | 0.00 | N/A — no verified directly comparable record |

## Full timing statistics

| Operation | Implementation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Samples |
|---|---|---:|---:|---:|---:|---:|---:|
| rotation_operator | production | 106278 | 152870.50 | 181007.47 | 314126 | 68731.50 | 30 |
| rotation_operator | independent | 87884 | 155446.00 | 157252.17 | 273119 | 56118.29 | 30 |
| c3x_operator | production | 2224 | 2845.00 | 2794.13 | 4208 | 519.76 | 30 |
| c3x_operator | independent | 2234 | 2730.00 | 3631.43 | 28453 | 4648.74 | 30 |
| transition_operator | production | 115455 | 122233.00 | 124955.63 | 154438 | 9989.68 | 30 |
| transition_operator | independent | 97221 | 104204.50 | 105352.57 | 132337 | 8190.79 | 30 |
| state_evolution | production | 118401 | 124197.00 | 132745.03 | 213288 | 20481.49 | 30 |
| state_evolution | independent | 99205 | 105632.00 | 109153.77 | 145882 | 11647.25 | 30 |
| density_matrix | production | 18455 | 19732.00 | 20616.53 | 28584 | 2445.54 | 30 |
| density_matrix | independent | 4157 | 4593.50 | 4676.00 | 6312 | 425.45 | 30 |
| reduced_density_q4 | production | 3186 | 3627.00 | 3734.53 | 5600 | 540.95 | 30 |
| reduced_density_q4 | independent | 8516 | 9302.50 | 9934.80 | 15509 | 1561.69 | 30 |
| reduced_density_q123 | production | 3366 | 3702.00 | 3797.77 | 5380 | 425.36 | 30 |
| reduced_density_q123 | independent | 8506 | 9087.00 | 10083.23 | 33542 | 4383.47 | 30 |
| pennylane_execution | production | 1353796 | 1391361.50 | 1405801.30 | 1719559 | 65903.77 | 30 |
| pennylane_execution | independent | 119644 | 138693.50 | 136329.73 | 164177 | 12324.33 | 30 |

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
