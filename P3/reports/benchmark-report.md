## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40225454957-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 28
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.239901 | 10.172160 |
| Median (ms) | 2.610940 | 10.004952 |
| Std. dev. (ms) | 0.986104 | 1.512136 |
| Throughput (states/s) | 308651415.850 | 98307536.469 |

- Speedup: **0.318507×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40225454957-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
