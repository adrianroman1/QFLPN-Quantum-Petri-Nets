## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40238562735-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 39
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 1.892667 | 6.371438 |
| Median (ms) | 1.649825 | 5.701936 |
| Std. dev. (ms) | 0.375524 | 1.574894 |
| Throughput (states/s) | 528354877.796 | 156950450.241 |

- Speedup: **0.297055×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40238562735-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
