## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40229435654-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 31
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.962582 | 11.598211 |
| Median (ms) | 2.959157 | 12.395955 |
| Std. dev. (ms) | 0.130527 | 1.880500 |
| Throughput (states/s) | 337543376.855 | 86220195.274 |

- Speedup: **0.255434×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40229435654-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
