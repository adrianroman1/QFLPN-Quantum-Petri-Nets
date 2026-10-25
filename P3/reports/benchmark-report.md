## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40242453791-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 42
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.179297 | 8.352828 |
| Median (ms) | 2.172853 | 8.525221 |
| Std. dev. (ms) | 0.020800 | 1.884007 |
| Throughput (states/s) | 458863506.140 | 119719926.247 |

- Speedup: **0.260905×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40242453791-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
