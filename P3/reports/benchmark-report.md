## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40155072366-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 13
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.061518 | 5.677714 |
| Median (ms) | 1.813997 | 5.907332 |
| Std. dev. (ms) | 0.403192 | 1.081700 |
| Throughput (states/s) | 485079488.521 | 176127219.932 |

- Speedup: **0.363089×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40155072366-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
