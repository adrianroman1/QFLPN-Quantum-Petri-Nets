## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40237258005-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 37
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 1.899992 | 6.417060 |
| Median (ms) | 1.650953 | 5.977542 |
| Std. dev. (ms) | 0.404463 | 1.048965 |
| Throughput (states/s) | 526318005.549 | 155834613.099 |

- Speedup: **0.296085×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40237258005-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
