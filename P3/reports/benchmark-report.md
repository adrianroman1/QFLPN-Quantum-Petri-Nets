## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40152233811-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 10
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.845552 | 9.142722 |
| Median (ms) | 2.605374 | 9.176989 |
| Std. dev. (ms) | 0.614943 | 1.236893 |
| Throughput (states/s) | 351425675.982 | 109376615.527 |

- Speedup: **0.311237×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40152233811-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
