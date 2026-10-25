## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40152141218-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 9
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.965499 | 10.103470 |
| Median (ms) | 2.618529 | 9.833887 |
| Std. dev. (ms) | 0.710505 | 1.897825 |
| Throughput (states/s) | 337211319.712 | 98975895.420 |

- Speedup: **0.293513×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40152141218-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
