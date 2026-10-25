## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40244220495-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 45
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.925489 | 9.936202 |
| Median (ms) | 3.921222 | 10.994637 |
| Std. dev. (ms) | 1.238396 | 1.859210 |
| Throughput (states/s) | 254745338.854 | 100642074.293 |

- Speedup: **0.395069×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40244220495-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
