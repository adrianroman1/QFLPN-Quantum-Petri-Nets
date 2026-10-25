## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40147321406-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 1
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.207917 | 9.440001 |
| Median (ms) | 2.608121 | 9.348352 |
| Std. dev. (ms) | 0.939119 | 1.267890 |
| Throughput (states/s) | 311728812.143 | 105932186.557 |

- Speedup: **0.339822×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40147321406-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
