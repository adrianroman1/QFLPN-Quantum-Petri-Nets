## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40243657850-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 43
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.752639 | 9.090262 |
| Median (ms) | 2.608464 | 9.493164 |
| Std. dev. (ms) | 0.340314 | 1.786750 |
| Throughput (states/s) | 363287739.511 | 110007826.727 |

- Speedup: **0.302812×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40243657850-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
