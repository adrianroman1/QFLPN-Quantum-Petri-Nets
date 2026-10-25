## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40237054822-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 34
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.335232 | 10.051823 |
| Median (ms) | 2.618369 | 10.104101 |
| Std. dev. (ms) | 0.973042 | 2.547351 |
| Throughput (states/s) | 299829244.247 | 99484446.726 |

- Speedup: **0.331804×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40237054822-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
