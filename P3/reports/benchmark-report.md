## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-41223048026-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 76
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.956265 | 3.621472 |
| Median (ms) | 2.706558 | 3.467970 |
| Std. dev. (ms) | 0.510432 | 0.670840 |
| Throughput (states/s) | 338264634.098 | 276130795.647 |

- Speedup: **0.816316×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `/home/runner/work/QFLPN-Quantum-Petri-Nets/QFLPN-Quantum-Petri-Nets/P3/results/raw/p3-41223048026-1/validation-report.json`
- CSV evidence: `/home/runner/work/QFLPN-Quantum-Petri-Nets/QFLPN-Quantum-Petri-Nets/P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
