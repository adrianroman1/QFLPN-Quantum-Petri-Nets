## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40247643806-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 46
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.134492 | 8.218067 |
| Median (ms) | 3.180914 | 7.479551 |
| Std. dev. (ms) | 0.791105 | 1.610255 |
| Throughput (states/s) | 319031003.305 | 121683120.435 |

- Speedup: **0.381415×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40247643806-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
