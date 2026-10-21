# QFLPN P2 — Benchmark Results

- Generated (UTC): `2026-10-21T20:42:00.335126+00:00`
- Status: **PASS**
- Qubits: `4`
- Hilbert dimension: `16`
- Basis order: `big-endian`
- Operator order: `U = C3X @ U_rot`
- Warmups per operation: `5`
- Measured repetitions: `30`
- Timer: `time.perf_counter_ns`
- Numerical tolerance: `1.000e-12`
- Total benchmark runtime: **0.085046 seconds**
- Total production execution time: **0.035675461 seconds**
- Total independent execution time: **0.009182182 seconds**
- Total timed execution time (both implementations): **0.044857643 seconds**
- Initial evidence-generation time: **0.002137 seconds**
- Runtime measurement scope: Elapsed wall-clock time from benchmark CLI start, before configuration loading, through the first complete generation of the four evidence files. Final JSON and Markdown persistence of the measured duration is excluded to avoid a self-referential timing measurement.

## Numerical parity

PennyLane / independent NumPy state difference: `0.000000e+00`

## Paired operation measurements

| Operation | Production median (ns) | Independent median (ns) | Production reduction (%) | Paired median difference (ns) | Production wins (%) | World record |
|---|---:|---:|---:|---:|---:|---|
| rotation_operator | 72702.50 | 61384.50 | -18.438 | -11003.00 | 3.33 | N/A — no verified directly comparable record |
| c3x_operator | 1672.50 | 1681.50 | 0.535 | 13.00 | 50.00 | N/A — no verified directly comparable record |
| transition_operator | 74034.50 | 64546.00 | -14.700 | -9272.50 | 16.67 | N/A — no verified directly comparable record |
| state_evolution | 75494.00 | 66447.00 | -13.615 | -9412.50 | 10.00 | N/A — no verified directly comparable record |
| density_matrix | 10427.50 | 2615.00 | -298.757 | -7691.00 | 0.00 | N/A — no verified directly comparable record |
| reduced_density_q4 | 1795.00 | 5391.00 | 66.704 | 3611.00 | 100.00 | N/A — no verified directly comparable record |
| reduced_density_q123 | 1980.50 | 5607.50 | 64.681 | 3625.50 | 100.00 | N/A — no verified directly comparable record |
| pennylane_execution | 939679.00 | 94447.00 | -894.927 | -861183.00 | 0.00 | N/A — no verified directly comparable record |

## Full timing statistics

| Operation | Implementation | Min (ns) | Median (ns) | Mean (ns) | Max (ns) | Std. dev. (ns) | Samples |
|---|---|---:|---:|---:|---:|---:|---:|
| rotation_operator | production | 68554 | 72702.50 | 77730.57 | 112296 | 11218.81 | 30 |
| rotation_operator | independent | 57307 | 61384.50 | 65607.97 | 99340 | 9356.36 | 30 |
| c3x_operator | production | 1507 | 1672.50 | 1687.47 | 2023 | 122.33 | 30 |
| c3x_operator | independent | 1444 | 1681.50 | 1756.33 | 2922 | 325.65 | 30 |
| transition_operator | production | 71783 | 74034.50 | 74596.93 | 79181 | 2262.12 | 30 |
| transition_operator | independent | 61313 | 64546.00 | 67426.80 | 89063 | 7000.78 | 30 |
| state_evolution | production | 73241 | 75494.00 | 77065.03 | 101395 | 5116.46 | 30 |
| state_evolution | independent | 63172 | 66447.00 | 68779.73 | 89223 | 6310.76 | 30 |
| density_matrix | production | 9719 | 10427.50 | 10909.47 | 15850 | 1405.40 | 30 |
| density_matrix | independent | 2365 | 2615.00 | 2666.60 | 3689 | 246.87 | 30 |
| reduced_density_q4 | production | 1638 | 1795.00 | 1847.33 | 2765 | 208.09 | 30 |
| reduced_density_q4 | independent | 5064 | 5391.00 | 5589.43 | 7601 | 564.75 | 30 |
| reduced_density_q123 | production | 1830 | 1980.50 | 2053.57 | 3385 | 323.77 | 30 |
| reduced_density_q123 | independent | 5243 | 5607.50 | 5729.83 | 7552 | 467.59 | 30 |
| pennylane_execution | production | 901745 | 939679.00 | 943291.67 | 1076168 | 32745.12 | 30 |
| pennylane_execution | independent | 71142 | 94447.00 | 88516.03 | 120381 | 13356.11 | 30 |

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
