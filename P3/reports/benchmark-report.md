## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40208466006-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 21
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.206926 | 10.346152 |
| Median (ms) | 2.585675 | 10.075697 |
| Std. dev. (ms) | 0.935675 | 1.611967 |
| Throughput (states/s) | 311825093.563 | 96654290.471 |

- Speedup: **0.309963×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40208466006-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
