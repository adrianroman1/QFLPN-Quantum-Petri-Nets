## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40154561963-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 12
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 1.581831 | 5.439634 |
| Median (ms) | 1.548997 | 5.474215 |
| Std. dev. (ms) | 0.176872 | 1.005250 |
| Throughput (states/s) | 632178945.078 | 183835914.681 |

- Speedup: **0.290797×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40154561963-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
