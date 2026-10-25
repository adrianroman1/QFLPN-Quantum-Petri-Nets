## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40159467253-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 20
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.151178 | 6.297533 |
| Median (ms) | 1.826232 | 5.926077 |
| Std. dev. (ms) | 0.480400 | 1.448839 |
| Throughput (states/s) | 464861664.606 | 158792349.880 |

- Speedup: **0.341591×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40159467253-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
