## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40212437025-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 24
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.568945 | 8.375837 |
| Median (ms) | 2.204136 | 7.700563 |
| Std. dev. (ms) | 0.598438 | 1.650039 |
| Throughput (states/s) | 389264823.555 | 119391060.224 |

- Speedup: **0.306709×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40212437025-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
