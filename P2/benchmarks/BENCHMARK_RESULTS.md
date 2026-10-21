# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-21T19:59:57.718379+00:00`
- Status: **PASS**
- Qubits: `4`
- Hilbert dimension: `16`
- Basis order: `big-endian`
- Operator order: `U = C3X @ U_rot`
- Warmups per operation: `5`
- Measured repetitions: `30`
- Timer: `time.perf_counter_ns`
- Numerical tolerance: `1.000e-12`
- Total benchmark runtime: **0.133693 seconds**
- Total production execution time: **0.054691339 seconds**
- Total independent execution time: **0.014128413 seconds**
- Total timed execution time (both implementations): **0.068819752 seconds**
- Initial evidence-generation time: **0.003055 seconds**
- Runtime measurement scope: Elapsed wall-clock time from benchmark CLI start, before configuration loading, through the first complete generation of the four evidence files. Final JSON and Markdown persistence of the measured duration is excluded to avoid a self-referential timing measurement.

## Numerical parity

PennyLane / independent NumPy state difference: `0.000000e+00`

## Paired operation measurements

| Operation | Production median (ns) | Independent median (ns) | Production reduction (%) | Paired median difference (ns) | Production wins (%) | World record |
|---|---:|---:|---:|---:|---:|---|
| rotation_operator | 112410.50 | 91901.50 | -22.316 | -21851.50 | 3.33 | N/A — no verified directly comparable record |
| c3x_operator | 2765.00 | 2720.00 | -1.654 | -85.00 | 50.00 | N/A — no verified directly comparable record |
| transition_operator | 119854.00 | 101991.00 | -17.514 | -17798.50 | 10.00 | N/A — no verified directly comparable record |
| state_evolution | 123130.50 | 104991.00 | -17.277 | -16606.50 | 13.33 | N/A — no verified directly comparable record |
| density_matrix | 19526.50 | 4403.00 | -343.482 | -15218.50 | 0.00 | N/A — no verified directly comparable record |
| reduced_density_q4 | 3477.00 | 9442.50 | 63.177 | 6021.50 | 96.67 | N/A — no verified directly comparable record |
| reduced_density_q123 | 3577.00 | 9167.50 | 60.982 | 5546.50 | 100.00 | N/A — no verified directly comparable record |
| pennylane_execution | 1411636.00 | 139145.00 | -914.507 | -1277019.00 | 0.00 | N/A — no verified directly comparable record |

## Full timing statistics

| Operation | Implementation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Samples |
|---|---|---:|---:|---:|---:|---:|---:|
| rotation_operator | production | 103925 | 112410.50 | 120681.17 | 181189 | 18553.46 | 30 |
| rotation_operator | independent | 87364 | 91901.50 | 94651.07 | 138769 | 10660.93 | 30 |
| c3x_operator | production | 2225 | 2765.00 | 2829.83 | 5580 | 676.57 | 30 |
| c3x_operator | independent | 2174 | 2720.00 | 2751.87 | 5180 | 598.13 | 30 |
| transition_operator | production | 114955 | 119854.00 | 124974.50 | 167885 | 14065.23 | 30 |
| transition_operator | independent | 96721 | 101991.00 | 104143.50 | 134562 | 8762.09 | 30 |
| state_evolution | production | 118271 | 123130.50 | 128598.67 | 219170 | 18468.11 | 30 |
| state_evolution | independent | 99516 | 104991.00 | 108521.57 | 140583 | 10485.60 | 30 |
| density_matrix | production | 18435 | 19526.50 | 20485.73 | 27651 | 2392.81 | 30 |
| density_matrix | independent | 3948 | 4403.00 | 4573.03 | 8075 | 768.59 | 30 |
| reduced_density_q4 | production | 3106 | 3477.00 | 4491.47 | 30558 | 4859.76 | 30 |
| reduced_density_q4 | independent | 8496 | 9442.50 | 9891.83 | 14808 | 1413.25 | 30 |
| reduced_density_q123 | production | 3276 | 3577.00 | 3932.07 | 8636 | 1028.44 | 30 |
| reduced_density_q123 | independent | 8786 | 9167.50 | 10100.23 | 29655 | 3728.32 | 30 |
| pennylane_execution | production | 1367098 | 1411636.00 | 1417051.20 | 1571831 | 38659.89 | 30 |
| pennylane_execution | independent | 121187 | 139145.00 | 136314.00 | 169847 | 13825.73 | 30 |

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
